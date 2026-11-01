"""Master analysis: codec structure, GOPs, splice points, audio layout.

Key definitions (all indices are 0-based *display* frame indices unless noted):

* **clean cut point k** - the first k frames in decode order are exactly the
  first k frames in display order.  Because an H.264 picture can only
  reference pictures that precede it in decode order, the decode-order prefix
  ending at a clean cut point is self-contained: its frames decode to exactly
  the same pixels whatever follows it.
* **resume point r** - a clean cut point whose decode-order sample r is an IDR
  access unit.  An IDR clears every reference picture, so the decode-order
  suffix starting at r decodes identically regardless of what precedes it.

A copied range [r, k) therefore needs r to be a resume point and k a clean cut
point.  Non-IDR I-frames (open GOP / recovery-point frames) are never used as
resume points because later pictures may still reference pictures before them.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional

from . import h264
from .ffmpeg import ffprobe_json
from .mp4 import (Movie, Track, audio_entry_info, avcc_from_entry, read_movie,
                  visual_entry_dimensions)


class AnalysisError(RuntimeError):
    pass


@dataclass
class VideoAnalysis:
    track: Track
    codec: str
    avcc: Optional[h264.AvcConfig]
    sps: List[h264.SPS]
    pps: List[h264.PPS]
    width: int
    height: int
    pix_fmt: str
    timescale: int
    frame_duration: int
    fps: Fraction
    frame_count: int
    cts0: int
    disp_of_dec: List[int]
    dec_of_disp: List[int]
    is_idr: List[bool]            # decode order
    slice_type: List[Optional[str]]  # decode order
    pps_id: List[Optional[int]]   # decode order
    recovery_point: List[bool]    # decode order
    cut_points: List[int]
    resume_points: List[int]
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    inband_parameter_sets: bool = False
    max_reorder_delay: int = 0    # max(decode_index - display_index) in frames
    open_gop_frames: int = 0

    @property
    def patchable(self) -> bool:
        return not self.blocking_issues

    def active_sps(self) -> h264.SPS:
        # SPS referenced by the PPS of the first frame
        first_pps = self.pps_id[0]
        pps = next((p for p in self.pps if p.pps_id == first_pps), None)
        if pps is not None:
            sps = next((s for s in self.sps if s.sps_id == pps.sps_id), None)
            if sps is not None:
                return sps
        return self.sps[0]

    def active_pps(self) -> h264.PPS:
        first_pps = self.pps_id[0]
        return next((p for p in self.pps if p.pps_id == first_pps), self.pps[0])

    def gop_lengths(self) -> List[int]:
        rp = self.resume_points
        return [rp[i + 1] - rp[i] for i in range(len(rp) - 1)]

    def frame_type_display(self) -> List[str]:
        out = []
        for k in range(self.frame_count):
            d = self.dec_of_disp[k]
            t = self.slice_type[d] or "?"
            if self.is_idr[d]:
                t = "IDR"
            out.append(t)
        return out

    def prev_cut(self, k: int) -> int:
        """Largest clean cut point <= k."""
        import bisect
        i = bisect.bisect_right(self.cut_points, k) - 1
        return self.cut_points[max(i, 0)]

    def next_resume(self, k: int) -> int:
        """Smallest resume point >= k (frame_count if none)."""
        import bisect
        i = bisect.bisect_left(self.resume_points, k)
        if i >= len(self.resume_points):
            return self.frame_count
        return self.resume_points[i]

    def prev_resume(self, k: int) -> int:
        import bisect
        i = bisect.bisect_right(self.resume_points, k) - 1
        return self.resume_points[max(i, 0)]

    def summary(self) -> dict:
        gl = self.gop_lengths()
        sps = self.active_sps()
        types = self.slice_type
        return {
            "codec": self.codec,
            "sample_entry": self.track.sample_entry_type,
            "width": self.width,
            "height": self.height,
            "pix_fmt": self.pix_fmt,
            "fps": f"{self.fps.numerator}/{self.fps.denominator}",
            "fps_float": float(self.fps),
            "timescale": self.timescale,
            "frame_duration": self.frame_duration,
            "frame_count": self.frame_count,
            "duration_s": self.frame_count / float(self.fps),
            "sps": sps.summary(),
            "pps": self.active_pps().summary(),
            "parameter_sets": {"sps_ids": [s.sps_id for s in self.sps], "pps_ids": [p.pps_id for p in self.pps]},
            "idr_count": sum(self.is_idr),
            "resume_points": len(self.resume_points),
            "cut_points": len(self.cut_points),
            "gop_min": min(gl) if gl else self.frame_count,
            "gop_max": max(gl) if gl else self.frame_count,
            "gop_avg": (sum(gl) / len(gl)) if gl else self.frame_count,
            "b_frames": any(t == "B" for t in types),
            "max_reorder_delay": self.max_reorder_delay,
            "open_gop_frames": self.open_gop_frames,
            "inband_parameter_sets": self.inband_parameter_sets,
            "patchable": self.patchable,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
        }


@dataclass
class AudioAnalysis:
    track: Track
    index: int
    info: dict
    codec: str
    sample_rate: int
    channels: int
    packet_count: int
    frame_size: int            # samples per packet (1024 for AAC-LC)
    priming: int               # media_time of the edit list (encoder delay)
    presented_samples: int     # samples presented after edit list
    uniform_packets: bool
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "index": self.index,
            "track_id": self.track.track_id,
            "codec": self.codec,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "packets": self.packet_count,
            "frame_size": self.frame_size,
            "priming_samples": self.priming,
            "presented_samples": self.presented_samples,
            "duration_s": self.presented_samples / self.sample_rate if self.sample_rate else 0,
            "avg_bitrate": self.info.get("avg_bitrate"),
            "splice_capable": not self.blocking_issues,
            "issues": self.blocking_issues,
            "warnings": self.warnings,
        }


@dataclass
class MasterAnalysis:
    path: str
    movie: Movie
    video: VideoAnalysis
    audio: List[AudioAnalysis]
    other_tracks: List[Track]
    probe: dict
    color: dict
    file_size: int

    def summary(self) -> dict:
        return {
            "path": self.path,
            "file_size": self.file_size,
            "container": {
                "major_brand": self.movie.ftyp.payload[:4].decode("latin-1") if self.movie.ftyp else None,
                "faststart": self.movie.moov_before_mdat,
                "fragmented": self.movie.fragmented,
                "movie_timescale": self.movie.timescale,
                "tracks": [t.handler for t in self.movie.tracks],
            },
            "video": self.video.summary(),
            "audio": [a.summary() for a in self.audio],
            "color": self.color,
            "other_tracks": [{"handler": t.handler, "track_id": t.track_id} for t in self.other_tracks],
        }


def _scan_nals(f, offset: int, size: int, length_size: int) -> List[bytes]:
    """Read NAL units of one sample; slice NALs are truncated to their first bytes."""
    nals = []
    pos = 0
    while pos < size:
        f.seek(offset + pos)
        hdr = f.read(length_size)
        if len(hdr) < length_size:
            raise AnalysisError("truncated sample data")
        ln = int.from_bytes(hdr, "big")
        pos += length_size
        if ln == 0 or pos + ln > size:
            raise AnalysisError(f"invalid NAL length {ln} in sample at offset {offset}")
        t_byte = f.read(1)
        t = t_byte[0] & 0x1F
        if t in (h264.NAL_SPS, h264.NAL_PPS, h264.NAL_SEI) and ln <= 1 << 16:
            body = t_byte + f.read(ln - 1)
        else:
            body = t_byte + f.read(min(ln, 32) - 1)
        nals.append(body)
        pos += ln
    return nals


def analyze_video(movie: Movie, track: Track, log=None) -> VideoAnalysis:
    entry = track.stsd_entries[0] if track.stsd_entries else b""
    codec = track.sample_entry_type
    issues: List[str] = []
    warns: List[str] = []
    if codec not in ("avc1", "avc3"):
        raise AnalysisError(f"unsupported video codec '{codec}' (only H.264 'avc1'/'avc3' masters can be patched)")
    if len(track.stsd_entries) > 1:
        warns.append(f"video track has {len(track.stsd_entries)} sample descriptions (previously patched file?)")
    avcc_raw = avcc_from_entry(entry)
    if avcc_raw is None:
        raise AnalysisError("avc1 sample entry has no avcC box")
    avcc = h264.AvcConfig.parse(avcc_raw)
    # collect parameter sets from all sample descriptions
    for extra in track.stsd_entries[1:]:
        raw = avcc_from_entry(extra)
        if raw:
            c = h264.AvcConfig.parse(raw)
            for s in c.sps:
                if s not in avcc.sps:
                    avcc.sps.append(s)
            for p in c.pps:
                if p not in avcc.pps:
                    avcc.pps.append(p)
    n = track.sample_count
    if n == 0:
        raise AnalysisError("video track has no samples")

    # --- timing ------------------------------------------------------------
    durs = set(track.durations[:-1]) if n > 1 else set(track.durations)
    if len(durs) != 1:
        issues.append(f"variable frame rate: {len(durs)} distinct frame durations in stts")
    dur = max(set(track.durations), key=track.durations.count)
    if track.durations[-1] != dur:
        warns.append(f"last frame duration {track.durations[-1]} differs from nominal {dur}")
    order = sorted(range(n), key=lambda i: track.cts(i))
    cts0 = track.cts(order[0])
    for k, d in enumerate(order):
        if track.cts(d) != cts0 + k * dur:
            issues.append(f"composition timestamps are not constant-frame-rate at display frame {k}")
            break
    disp_of_dec = [0] * n
    for k, d in enumerate(order):
        disp_of_dec[d] = k
    fps = Fraction(track.timescale, dur)

    # edit list
    if track.edits:
        normal = [e for e in track.edits if e.media_time != -1]
        empties = [e for e in track.edits if e.media_time == -1]
        if len(normal) != 1:
            issues.append(f"edit list has {len(normal)} non-empty edits (multi-edit timelines are not supported)")
        else:
            e = normal[0]
            if e.rate_int != 1:
                issues.append("edit list uses a non-unity playback rate")
            if e.media_time != cts0:
                issues.append(f"edit list media_time {e.media_time} != first composition time {cts0}: "
                              f"the master trims frames at its start")
            seg_media = e.segment_duration * track.timescale / movie.timescale
            frames_presented = seg_media / dur
            if frames_presented < n - 1.01:
                issues.append(f"edit list presents {frames_presented:.2f} of {n} frames (trimmed tail)")
        if empties:
            warns.append("edit list contains an initial empty edit (delayed start); preserved as-is")

    # --- NAL structure -------------------------------------------------------
    is_idr = [False] * n
    stype: List[Optional[str]] = [None] * n
    ppsid: List[Optional[int]] = [None] * n
    recov = [False] * n
    inband = False
    sps_list = list(avcc.sps)
    pps_list = list(avcc.pps)
    with open(movie.path, "rb") as f:
        for i in range(n):
            nals = _scan_nals(f, track.offsets[i], track.sizes[i], avcc.length_size)
            info = h264.analyze_access_unit(nals)
            is_idr[i] = info.is_idr
            stype[i] = info.slice_type
            ppsid[i] = info.pps_id
            recov[i] = info.has_recovery_point
            if info.inband_sps or info.inband_pps:
                inband = True
                for s in info.inband_sps:
                    if s not in sps_list:
                        sps_list.append(s)
                for p in info.inband_pps:
                    if p not in pps_list:
                        pps_list.append(p)
            if info.slice_type is None:
                issues.append(f"sample {i} contains no slice NAL unit")
                break
            if log and i and i % 5000 == 0:
                log(f"scanned {i}/{n} access units")
    sps = [h264.parse_sps(s) for s in sps_list]
    sps_map = {s.sps_id: s for s in sps}
    pps = []
    for p in pps_list:
        tmp = h264.parse_pps(p)
        chroma = sps_map[tmp.sps_id].chroma_format_idc if tmp.sps_id in sps_map else 1
        pps.append(h264.parse_pps(p, chroma))

    # Parameter-set id conflicts (same id, different content) make splicing ambiguous.
    seen_s: Dict[int, bytes] = {}
    for s in sps:
        if s.sps_id in seen_s and seen_s[s.sps_id] != s.raw:
            issues.append(f"SPS id {s.sps_id} is redefined with different content inside the stream")
        seen_s[s.sps_id] = s.raw
    seen_p: Dict[int, bytes] = {}
    for p in pps:
        if p.pps_id in seen_p and seen_p[p.pps_id] != p.raw:
            issues.append(f"PPS id {p.pps_id} is redefined with different content inside the stream")
        seen_p[p.pps_id] = p.raw

    first_sps = sps[0]
    for s in sps:
        if not s.frame_mbs_only:
            issues.append("interlaced (field/MBAFF) coding is not supported for patching")
            break
    for p in pps:
        if p.num_slice_groups > 1:
            issues.append("FMO slice groups are not supported")
            break
    if not is_idr[0]:
        issues.append("first frame is not an IDR picture")

    # --- splice points -----------------------------------------------------
    cut_points = [0]
    max_disp = -1
    max_delay = 0
    for j in range(n):
        dj = disp_of_dec[j]
        if dj > max_disp:
            max_disp = dj
        if max_disp == j:
            cut_points.append(j + 1)
        if j - dj > max_delay:
            max_delay = j - dj
    cut_set = set(cut_points)
    resume_points = [j for j in range(n) if is_idr[j] and j in cut_set]
    if not resume_points or resume_points[0] != 0:
        issues.append("stream does not start at a resume point")
    open_gop = sum(1 for j in range(n) if track.is_sync(j) and not is_idr[j])
    if open_gop:
        warns.append(f"{open_gop} sync samples are non-IDR I-frames (open GOP / recovery point); "
                     f"they are not used as splice points")
    non_sync_idr = sum(1 for j in range(n) if is_idr[j] and not track.is_sync(j))
    if non_sync_idr:
        warns.append(f"{non_sync_idr} IDR frames are not flagged as sync samples in stss")

    w, h = first_sps.width, first_sps.height
    ew, eh = visual_entry_dimensions(entry)
    if (ew, eh) != (w, h):
        warns.append(f"sample entry dimensions {ew}x{eh} differ from SPS {w}x{h}")
    if any((s.width, s.height) != (w, h) for s in sps):
        issues.append("resolution changes inside the stream")

    return VideoAnalysis(
        track=track, codec="h264", avcc=avcc, sps=sps, pps=pps, width=w, height=h,
        pix_fmt=first_sps.pix_fmt, timescale=track.timescale, frame_duration=dur, fps=fps,
        frame_count=n, cts0=cts0, disp_of_dec=disp_of_dec, dec_of_disp=order,
        is_idr=is_idr, slice_type=stype, pps_id=ppsid, recovery_point=recov,
        cut_points=cut_points, resume_points=resume_points, blocking_issues=issues,
        warnings=warns, inband_parameter_sets=inband, max_reorder_delay=max_delay,
        open_gop_frames=open_gop)


def analyze_audio(movie: Movie, track: Track, index: int) -> AudioAnalysis:
    entry = track.stsd_entries[0]
    info = audio_entry_info(entry)
    issues: List[str] = []
    warns: List[str] = []
    codec = info.get("entry_type", "?")
    rate = info.get("sample_rate") or info.get("rate") or track.timescale
    channels = info.get("channels", 0)
    frame_size = 1024
    if codec == "mp4a":
        ot = info.get("aac_object_type")
        if info.get("object_type_indication") not in (0x40, 0x66, 0x67, 0x68):
            issues.append("mp4a track is not AAC")
            codec = "mp4a(non-aac)"
        else:
            codec = "aac"
            if ot != 2:
                issues.append(f"AAC object type {ot} (only AAC-LC supports packet splicing)")
            frame_size = info.get("frame_length", 1024)
            if info.get("channel_config") == 0:
                issues.append("AAC channel configuration 0 (PCE) is not supported for splicing")
    else:
        issues.append(f"audio codec '{codec}' cannot be spliced (copy or full re-encode only)")
    n = track.sample_count
    durs = track.durations
    uniform = len(set(durs[:-1])) <= 1 and (not durs or durs[0] == frame_size)
    if not uniform:
        issues.append("audio packets do not all carry one frame of samples")
    if track.timescale != rate:
        warns.append(f"audio media timescale {track.timescale} != sample rate {rate}")
        issues.append("audio timescale differs from sample rate")
    priming = 0
    presented = sum(durs)
    if track.edits:
        normal = [e for e in track.edits if e.media_time != -1]
        if len(normal) == 1:
            priming = normal[0].media_time
            presented = normal[0].segment_duration * track.timescale // movie.timescale
        else:
            issues.append("audio edit list is not a single edit")
    return AudioAnalysis(track=track, index=index, info=info, codec=codec, sample_rate=rate,
                         channels=channels, packet_count=n, frame_size=frame_size, priming=priming,
                         presented_samples=presented, uniform_packets=uniform,
                         blocking_issues=issues, warnings=warns)


COLOR_KEYS = ("color_range", "color_space", "color_transfer", "color_primaries", "chroma_location",
              "field_order", "sample_aspect_ratio")


def analyze_master(path: str, log=None, run_ffprobe: bool = True) -> MasterAnalysis:
    if not os.path.isfile(path):
        raise AnalysisError(f"master file not found: {path}")
    movie = read_movie(path)
    if movie.fragmented:
        raise AnalysisError("fragmented MP4 masters are not supported (export a regular MP4)")
    vids = movie.track_by_handler("vide")
    if not vids:
        raise AnalysisError("master has no video track")
    if len(vids) > 1:
        raise AnalysisError("master has more than one video track")
    video = analyze_video(movie, vids[0], log=log)
    audios = [analyze_audio(movie, t, i) for i, t in enumerate(movie.track_by_handler("soun"))]
    others = [t for t in movie.tracks if t.handler not in ("vide", "soun")]
    probe = {}
    color = {}
    if run_ffprobe:
        probe = ffprobe_json(path, ["-show_streams", "-show_format"])
        for s in probe.get("streams", []):
            if s.get("codec_type") == "video":
                color = {k: s.get(k) for k in COLOR_KEYS if s.get(k) is not None}
                color["pix_fmt"] = s.get("pix_fmt")
                color["profile"] = s.get("profile")
                break
    sps = video.active_sps()
    if sps.vui is not None:
        color["vui_full_range"] = sps.vui.full_range
        color["vui_primaries"] = sps.vui.colour_primaries
        color["vui_transfer"] = sps.vui.transfer_characteristics
        color["vui_matrix"] = sps.vui.matrix_coefficients
    return MasterAnalysis(path=os.path.abspath(path), movie=movie, video=video, audio=audios,
                          other_tracks=others, probe=probe, color=color, file_size=movie.file_size)


def file_sha256(path: str, progress=None, cancel_check=None) -> str:
    h = hashlib.sha256()
    size = os.path.getsize(path)
    done = 0
    with open(path, "rb") as f:
        while True:
            if cancel_check:
                cancel_check()
            buf = f.read(16 * 1024 * 1024)
            if not buf:
                break
            h.update(buf)
            done += len(buf)
            if progress:
                progress(done / max(1, size))
    return h.hexdigest()


def peak_bitrate_kbps(video: VideoAnalysis) -> int:
    """Maximum video bitrate over any 1-second window (decode order), kbit/s."""
    t = video.track
    win = max(1, int(round(float(video.fps))))
    sizes = t.sizes
    acc = sum(sizes[:win])
    peak = acc
    for i in range(win, len(sizes)):
        acc += sizes[i] - sizes[i - win]
        peak = max(peak, acc)
    secs = win / float(video.fps)
    return int(peak * 8 / secs / 1000)


def gop_map(video: VideoAnalysis, max_points: int = 20000) -> dict:
    """Compact structure for UI visualisation."""
    return {
        "frame_count": video.frame_count,
        "resume_points": video.resume_points[:max_points],
        "idr_display": sorted(video.disp_of_dec[j] for j in range(video.frame_count) if video.is_idr[j])[:max_points],
        "cut_points_sample": video.cut_points[:: max(1, len(video.cut_points) // max_points)],
    }


def dumps(obj) -> str:
    return json.dumps(obj, indent=2, default=str)
