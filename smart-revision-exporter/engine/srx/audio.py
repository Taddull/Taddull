"""Audio engine: copy, AAC packet splice, or full-track re-encode.

AAC-LC is an MDCT codec with 50% window overlap: decoded block i is the
overlap-add of packet i-1 and packet i.  Independently encoded AAC segments can
therefore not simply be concatenated.  The splice strategy used here:

1. Choose a replacement packet range [p, q) on the master's own AAC frame grid,
   at least two frames (2048 samples) outside the revised audio on both sides,
   so every transition block lies in audio that is unchanged on the timeline.
2. Encode the timeline audio starting W packets *before* p (warm-up) with an
   input offset chosen so the new encoder's frame grid coincides exactly with
   the master's grid, taking the master's priming (edit-list media_time) and
   the encoder's own delay into account.
3. Replace exactly the packets [p, q); every other packet stays byte-identical,
   so audio timing, sample count and edit list are unchanged.
4. Verification decodes the result and checks (a) bit-identical PCM outside the
   transition blocks, (b) alignment (cross-correlation lag 0) and (c) the error
   at both transition blocks is at codec-noise level (no click).

When the duration changes, the codec is not AAC-LC, or the user selects it, the
whole audio track is re-encoded from a full Resolve audio render (audio-only,
which is fast) with the master's codec parameters.
"""

from __future__ import annotations

import math
import os
import subprocess
from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from typing import List, Optional, Tuple

from . import numeric
from .ffmpeg import CancelToken, ToolError, encoders, ffmpeg, run
from .media import AudioAnalysis
from .mp4 import EditEntry, OutSample, OutTrack, Track, audio_entry_info, read_movie


class AudioError(RuntimeError):
    pass


def choose_encoder(preferred: Optional[str] = None) -> str:
    enc = encoders()
    if preferred:
        if not enc.get(preferred):
            raise AudioError(f"audio encoder '{preferred}' is not available in this FFmpeg build")
        return preferred
    if enc.get("aac_at"):
        return "aac_at"  # Apple AudioToolbox AAC (macOS)
    if enc.get("aac"):
        return "aac"
    raise AudioError("no AAC encoder available in FFmpeg")


def _encode_args(encoder: str, bitrate: int, channels: int, sample_rate: int) -> List[str]:
    args = ["-c:a", encoder, "-b:a", str(bitrate), "-ar", str(sample_rate), "-ac", str(channels)]
    if encoder == "aac":
        # PNS (noise substitution) makes decoder output depend on a running
        # random-number state; it would break bit-identical decoding of every
        # later packet after a splice (now and in future revision cycles).
        args += ["-profile:a", "aac_low", "-aac_pns", "0"]
    return args


@lru_cache(maxsize=16)
def encoder_delay(encoder: str, sample_rate: int, channels: int, bitrate: int, workdir: str) -> int:
    """Measure the encoder's priming delay (edit-list media_time it writes)."""
    path = os.path.join(workdir, f"delay_probe_{encoder}_{sample_rate}_{channels}.m4a")
    cmd = [ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i",
           f"anullsrc=r={sample_rate}:cl={'mono' if channels == 1 else 'stereo' if channels == 2 else str(channels) + 'c'}",
           "-t", "1", *_encode_args(encoder, bitrate, channels, sample_rate), path]
    run(cmd)
    mv = read_movie(path)
    t = mv.track_by_handler("soun")[0]
    if not t.edits:
        return 0
    normal = [e for e in t.edits if e.media_time != -1]
    return normal[0].media_time if normal else 0


@dataclass
class RenderAudio:
    """PCM from a render, as interleaved float32 bytes."""
    path: str
    stream_index: int
    channels: int
    sample_rate: int
    timeline_first_frame: int          # absolute timeline frame of render frame 0
    data: bytes = b""

    @property
    def nsamples(self) -> int:
        return len(self.data) // (4 * self.channels)


def load_render_audio(path: str, stream_index: int, channels: int, sample_rate: int,
                      first_frame: int) -> RenderAudio:
    cmd = [ffmpeg(), "-v", "error", "-nostdin", "-i", path, "-map", f"0:a:{stream_index}",
           "-f", "f32le", "-acodec", "pcm_f32le", "-ar", str(sample_rate), "-ac", str(channels), "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise AudioError(f"cannot read audio stream {stream_index} from render: {r.stderr.decode()[-500:]}")
    return RenderAudio(path, stream_index, channels, sample_rate, first_frame, r.stdout)


def decode_windows(path: str, stream_index: int, channels: int, sample_rate: int,
                   windows: List[Tuple[int, int]], cancel: Optional[CancelToken] = None) -> List[bytes]:
    """Decode an audio track (edit list applied) and return the requested
    presentation-sample windows as interleaved float32 bytes."""
    if not windows:
        return []
    need_end = max(e for _, e in windows)
    cmd = [ffmpeg(), "-v", "error", "-nostdin", "-i", path, "-map", f"0:a:{stream_index}",
           "-f", "f32le", "-acodec", "pcm_f32le", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    if cancel:
        cancel.register(p)
    frame_bytes = 4 * channels
    buf = bytearray()
    pos = 0
    out = [bytearray() for _ in windows]
    try:
        while pos < need_end:
            chunk = p.stdout.read(frame_bytes * 65536)
            if not chunk:
                break
            buf += chunk
            nfull = len(buf) // frame_bytes
            block = bytes(buf[:nfull * frame_bytes])
            del buf[:nfull * frame_bytes]
            b0, b1 = pos, pos + nfull
            for wi, (s, e) in enumerate(windows):
                lo, hi = max(s, b0), min(e, b1)
                if lo < hi:
                    out[wi] += block[(lo - b0) * frame_bytes:(hi - b0) * frame_bytes]
            pos = b1
    finally:
        try:
            p.stdout.close()
            p.terminate()
            p.wait(timeout=10)
        except Exception:
            pass
        if cancel:
            cancel.unregister(p)
    return [bytes(o) for o in out]


def _mono(data: bytes, channels: int):
    return numeric.mixdown(numeric.floats_from_bytes(data), channels)


def measure_alignment(master_path: str, master_stream: int, ra: RenderAudio, nominal_offset: int,
                      windows: List[Tuple[int, int]], maxlag: int = 48) -> dict:
    """Measure where render sample 0 lies on the master's presentation timeline.

    `windows` are presentation-sample ranges known to be unchanged on the timeline.
    Returns {"offset": int, "measured": bool, "corr": float, "lags": [...]}.
    """
    results = []
    ch = ra.channels
    mwin = decode_windows(master_path, master_stream, ch, ra.sample_rate,
                          [(s, e) for s, e in windows])
    for (s, e), md in zip(windows, mwin):
        m = _mono(md, ch)
        if len(m) < 256 or numeric.energy(m) / max(1, len(m)) < 1e-7:
            continue
        lo = s - nominal_offset - maxlag
        hi = e - nominal_offset + maxlag
        if lo < 0 or hi > ra.nsamples:
            continue
        seg = _mono(ra.data[lo * 4 * ch:hi * 4 * ch], ch)
        lag, corr = numeric.best_lag(m, seg, maxlag)
        # render index (s - nominal + lag) matches master index s => offset = nominal - lag
        results.append((nominal_offset - lag, corr))
    if not results:
        return {"offset": nominal_offset, "measured": False, "corr": None, "lags": []}
    offsets = [r[0] for r in results]
    best = max(set(offsets), key=offsets.count)
    corr = max(r[1] for r in results if r[0] == best)
    return {"offset": best, "measured": True, "corr": corr, "lags": [o - nominal_offset for o in offsets],
            "consistent": len(set(offsets)) == 1}


@dataclass
class SpliceResult:
    packet_start: int
    packet_end: int
    encoded_path: str
    new_packets: List[Tuple[int, int, int]]   # (offset, size, duration) in encoded file
    alignment: dict
    encoder: str
    encoder_delay: int
    input_start_sample: int
    warmup_packets: int


def asc_compatible(master: AudioAnalysis, entry: bytes) -> Tuple[bool, str]:
    info = audio_entry_info(entry)
    m = master.info
    for key in ("aac_object_type", "sample_rate", "channel_config", "frame_length"):
        if info.get(key) != m.get(key):
            return False, f"{key}: master {m.get(key)} vs patch {info.get(key)}"
    return True, "ok"


def splice_track(master_path: str, a: AudioAnalysis, packet_start: int, packet_end: int,
                 ra: RenderAudio, timeline_offset: int, fps: Fraction, unchanged_windows: List[Tuple[int, int]],
                 workdir: str, encoder: str, bitrate: int, cancel: Optional[CancelToken] = None,
                 log=None) -> SpliceResult:
    F = a.frame_size
    P = a.priming
    sr = a.sample_rate
    ch = a.channels
    D = encoder_delay(encoder, sr, ch, bitrate, workdir)
    W = -(-D // F) + 2
    # nominal presentation sample of render sample 0
    rel_frame = ra.timeline_first_frame - timeline_offset
    exact = Fraction(rel_frame) * sr / fps
    nominal = math.floor(exact)
    align = measure_alignment(master_path, a.index, ra, nominal, unchanged_windows)
    if not align["measured"]:
        if exact.denominator != 1:
            raise AudioError("cannot measure render audio alignment (silence around the splice) and the "
                             "frame boundary is not on an integer sample; use full audio re-encode")
        if log:
            log("audio alignment not measurable (silence); using exact nominal offset")
    elif not align.get("consistent", True):
        raise AudioError(f"render audio alignment is inconsistent across guard windows: {align['lags']}")
    off = align["offset"]
    S0 = (packet_start - W) * F - P + D
    n_packets = packet_end - (packet_start - W) + W
    S1 = S0 + n_packets * F
    # build encoder input (presentation samples [S0, S1)) from render samples
    frame_bytes = 4 * ch
    lo = S0 - off
    hi = S1 - off
    pre = post = 0
    if lo < 0:
        # Legal only when the render starts at the very beginning of the timeline:
        # audio before presentation sample 0 is encoder priming (silence).
        if ra.timeline_first_frame != timeline_offset:
            raise AudioError("render does not cover the audio warm-up region")
        pre = -lo
        lo = 0
    if hi > ra.nsamples:
        post = hi - ra.nsamples
        if S1 - post < a.presented_samples - F:
            raise AudioError("render does not cover the audio tail region")
        hi = ra.nsamples
    pcm = b"\x00" * (pre * frame_bytes) + ra.data[lo * frame_bytes:hi * frame_bytes] + b"\x00" * (post * frame_bytes)
    raw_path = os.path.join(workdir, f"audio{a.index}_splice_{packet_start}.f32")
    with open(raw_path, "wb") as f:
        f.write(pcm)
    enc_path = os.path.join(workdir, f"audio{a.index}_splice_{packet_start}.m4a")
    run([ffmpeg(), "-v", "error", "-y", "-nostdin", "-f", "f32le", "-ar", str(sr), "-ac", str(ch), "-i", raw_path,
         *_encode_args(encoder, bitrate, ch, sr), enc_path], cancel=cancel, log=log)
    mv = read_movie(enc_path)
    t = mv.track_by_handler("soun")[0]
    ok, why = asc_compatible(a, t.stsd_entries[0])
    if not ok:
        raise AudioError(f"re-encoded AAC is not compatible with the master ({why})")
    measured_d = 0
    if t.edits:
        normal = [e for e in t.edits if e.media_time != -1]
        measured_d = normal[0].media_time if normal else 0
    if measured_d != D:
        raise AudioError(f"encoder delay changed between probe ({D}) and encode ({measured_d})")
    need = W + (packet_end - packet_start)
    if t.sample_count < need:
        raise AudioError(f"splice encode produced {t.sample_count} packets, need {need}")
    if any(t.durations[i] != F for i in range(W, need)):
        raise AudioError("splice encode packets are not uniform frames")
    new = [(t.offsets[i], t.sizes[i], t.durations[i]) for i in range(W, need)]
    return SpliceResult(packet_start, packet_end, enc_path, new, align, encoder, D, S0, W)


def build_spliced_track(a: AudioAnalysis, splices: List[SpliceResult], src_master: int,
                        src_index_of: dict) -> OutTrack:
    t = a.track
    samples: List[OutSample] = []
    replaced = {}
    for sp in splices:
        for i, (off, size, dur) in enumerate(sp.new_packets):
            replaced[sp.packet_start + i] = (src_index_of[sp.encoded_path], off, size, dur)
    for i in range(t.sample_count):
        if i in replaced:
            src, off, size, dur = replaced[i]
            samples.append(OutSample(src, off, size, t.durations[i], t.cts_offsets[i], t.is_sync(i),
                                     t.desc_index[i]))
        else:
            samples.append(OutSample(src_master, t.offsets[i], t.sizes[i], t.durations[i], t.cts_offsets[i],
                                     t.is_sync(i), t.desc_index[i]))
    return OutTrack(template=t, samples=samples, stsd_entries=t.stsd_entries, edits=t.edits,
                    stbl_extra=[b.raw for b in t.stbl_other if b.type not in ("sdtp", "cslg")])


def copy_track(t: Track, src: int) -> OutTrack:
    samples = [OutSample(src, t.offsets[i], t.sizes[i], t.durations[i], t.cts_offsets[i], t.is_sync(i),
                         t.desc_index[i]) for i in range(t.sample_count)]
    return OutTrack(template=t, samples=samples, stsd_entries=t.stsd_entries, edits=t.edits,
                    stbl_extra=[b.raw for b in t.stbl_other if b.type not in ("sdtp", "cslg")])


@dataclass
class FullAudioResult:
    encoded_path: str
    encoder: str
    encoder_delay: int
    presented_samples: int


def encode_full_track(a: AudioAnalysis, render_path: str, render_stream: int, workdir: str, encoder: str,
                      bitrate: int, expected_samples: int, cancel=None, log=None, progress=None) -> FullAudioResult:
    out = os.path.join(workdir, f"audio{a.index}_full.m4a")
    run([ffmpeg(), "-v", "error", "-y", "-nostdin", "-i", render_path, "-map", f"0:a:{render_stream}", "-vn",
         *_encode_args(encoder, bitrate, a.channels, a.sample_rate), out], cancel=cancel, log=log)
    mv = read_movie(out)
    t = mv.track_by_handler("soun")[0]
    ok, why = asc_compatible(a, t.stsd_entries[0])
    if not ok:
        # Full re-encode does not require bit-level ASC identity, only same layout.
        info = audio_entry_info(t.stsd_entries[0])
        if info.get("sample_rate") != a.sample_rate or info.get("channel_config") != a.info.get("channel_config"):
            raise AudioError(f"re-encoded audio layout differs from master ({why})")
    D = 0
    if t.edits:
        normal = [e for e in t.edits if e.media_time != -1]
        D = normal[0].media_time if normal else 0
    total = sum(t.durations)
    if total - D < expected_samples:
        raise AudioError(f"rendered audio is too short: {total - D} samples, expected {expected_samples}")
    return FullAudioResult(out, encoder, D, expected_samples)


def build_full_track(a: AudioAnalysis, res: FullAudioResult, src: int, movie_timescale: int) -> OutTrack:
    mv = read_movie(res.encoded_path)
    t = mv.track_by_handler("soun")[0]
    samples = [OutSample(src, t.offsets[i], t.sizes[i], t.durations[i], t.cts_offsets[i], True, 1)
               for i in range(t.sample_count)]
    seg = res.presented_samples * movie_timescale // a.sample_rate
    edits = [EditEntry(seg, res.encoder_delay, 1, 0)]
    if a.track.edits:
        empties = [e for e in a.track.edits if e.media_time == -1]
        edits = empties + edits
    return OutTrack(template=a.track, samples=samples, stsd_entries=[t.stsd_entries[0]], edits=edits,
                    stbl_extra=[b.raw for b in t.stbl_other if b.type in ("sgpd", "sbgp")],
                    timescale=t.timescale, mdhd_raw=t.mdhd.raw)


def master_bitrate(a: AudioAnalysis) -> int:
    br = a.info.get("avg_bitrate") or 0
    if not br:
        total = sum(a.track.sizes)
        dur = max(1, sum(a.track.durations)) / a.sample_rate
        br = int(total * 8 / dur)
    # round to a sensible encoder setting
    return int(round(br / 1000.0)) * 1000
