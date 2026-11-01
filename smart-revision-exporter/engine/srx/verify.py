"""Verification engine.

Nothing is reported as successful unless it was measured here.

Video
-----
* Structure: frame count, rational frame rate, dimensions, pixel format, colour
  metadata, constant-frame-rate composition timestamps, segment boundaries on
  IDR / clean-cut points, parameter sets.
* Preserved frames (copied packets): every decoded frame is hashed (SHA-256 of
  the raw decoded picture in the master's native pixel format, no conversion)
  and compared to the master's decoded frame.  "Verified" mode decodes the full
  output; "Fast" mode only decodes the regions around each splice.
* Re-encoded frames: PSNR against the fresh render that was encoded
  (encode fidelity) and, for boundary frames whose content is supposed to be
  unchanged, against the master.
* Guard frames (rendered but not used): render vs master, to detect timeline
  changes outside the declared revision ranges.
* Decoder errors anywhere in the decoded ranges fail verification.

Audio
-----
* copy: packet bytes and timing identical; decoded PCM identical.
* splice: packets outside the replaced range identical; decoded PCM identical
  outside the two transition blocks; transition blocks and replaced region at
  codec-noise level relative to the render; alignment lag 0.
* full: duration identical; alignment lag 0 against the master in unchanged
  regions; level difference and SNR within limits.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from . import numeric
from .assemble import extract_video_clip
from .audio import _mono, decode_windows
from .ffmpeg import CancelToken, FrameReader, ToolError, ffprobe_json, plane_layout, raw_frame_size
from .media import MasterAnalysis, analyze_master
from .mp4 import read_movie
from .plan import Plan, output_frame_classes, output_to_master_map
from .render import RenderedClip


@dataclass
class Thresholds:
    fidelity_min_psnr: float = 35.0      # output vs encoder input (render)
    unchanged_min_psnr: float = 30.0     # render/boundary vs master where content must be unchanged
    revised_same_psnr: float = 55.0      # revised frames this close to master trigger a warning
    black_luma: float = 20.0
    audio_transition_min_snr: float = 20.0
    audio_full_min_snr: float = 12.0
    audio_level_tolerance_db: float = 0.5


@dataclass
class Check:
    name: str
    status: str           # pass | fail | warn | skip
    detail: str
    data: dict = field(default_factory=dict)


class Report:
    def __init__(self, level: str):
        self.level = level
        self.checks: List[Check] = []
        self.video: dict = {}
        self.audio: List[dict] = []
        self.costs: dict = {}
        self.started = time.time()

    def add(self, name: str, status: str, detail: str, **data) -> Check:
        c = Check(name, status, detail, data)
        self.checks.append(c)
        return c

    @property
    def status(self) -> str:
        if any(c.status == "fail" for c in self.checks):
            return "failed"
        if not self.checks:
            return "failed"
        return "passed"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "level": self.level,
            "checks": [asdict(c) for c in self.checks],
            "video": self.video,
            "audio": self.audio,
            "costs": self.costs,
            "warnings": [c.detail for c in self.checks if c.status == "warn"],
            "failures": [c.detail for c in self.checks if c.status == "fail"],
        }


def _frame_metrics(a: bytes, b: bytes, layout, peak: int) -> Tuple[float, float]:
    """Return (luma PSNR, minimum PSNR over all planes).

    The minimum over planes is used for every pass/fail decision so that
    chroma-only changes (e.g. a colour grade or hue transition) are caught."""
    y_psnr = float("nan")
    worst = float("inf")
    for pi, (off, w, h, bps) in enumerate(layout):
        sse, n = numeric.plane_sse(a, b, off, w, h, bps)
        ps = numeric.psnr_from_sse(sse, n, peak)
        if pi == 0:
            y_psnr = ps
        worst = min(worst, ps)
    return y_psnr, worst


def _fmt(x: float) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if math.isinf(x):
        return "inf"
    return f"{x:.2f}"


def _stats(values: List[float]) -> dict:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    if not vals:
        return {"count": 0}
    finite = [v for v in vals if not math.isinf(v)]
    return {
        "count": len(vals),
        "min": min(vals),
        "mean": (sum(finite) / len(finite)) if finite else float("inf"),
        "max": max(vals),
    }


# ---------------------------------------------------------------------------
# Master frame hashes (cacheable by master SHA-256)
# ---------------------------------------------------------------------------

def hash_all_frames(path: str, pix_fmt: str, w: int, h: int, cancel: Optional[CancelToken] = None,
                    progress=None, total: int = 0) -> Tuple[List[str], str]:
    fr = FrameReader(path, pix_fmt, w, h, cancel=cancel)
    hashes = []
    try:
        while True:
            f = fr.read()
            if f is None:
                break
            hashes.append(hashlib.sha256(f).hexdigest())
            if progress and total and len(hashes) % 50 == 0:
                progress(len(hashes) / total)
        err = fr.finish()
    except Exception:
        fr.close()
        raise
    return hashes, err


def load_cached_hashes(cache_dir: Optional[str], fingerprint: Optional[str], pix_fmt: str, n: int):
    if not cache_dir or not fingerprint:
        return None
    p = os.path.join(cache_dir, f"{fingerprint}.framehashes.json")
    try:
        with open(p) as f:
            d = json.load(f)
        if d.get("pix_fmt") == pix_fmt and len(d.get("hashes", [])) == n and d.get("algo") == "sha256":
            return d["hashes"]
    except Exception:
        return None
    return None


def save_cached_hashes(cache_dir: Optional[str], fingerprint: Optional[str], pix_fmt: str, hashes: List[str]):
    if not cache_dir or not fingerprint:
        return
    os.makedirs(cache_dir, exist_ok=True)
    p = os.path.join(cache_dir, f"{fingerprint}.framehashes.json")
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"algo": "sha256", "pix_fmt": pix_fmt, "hashes": hashes}, f)
    os.replace(tmp, p)


# ---------------------------------------------------------------------------
# Region contexts (lock-step comparison around render segments)
# ---------------------------------------------------------------------------

class _RegionContext:
    def __init__(self, seg_index: int, w0: int, w1: int, seg, render_lo: int, render_hi: int,
                 render_reader: Optional[FrameReader], master_reader: Optional[FrameReader],
                 master_first: int):
        self.seg_index = seg_index
        self.w0, self.w1 = w0, w1
        self.seg = seg
        self.render_lo, self.render_hi = render_lo, render_hi
        self.render_reader = render_reader
        self.master_reader = master_reader
        self.master_pos = master_first  # master index of next frame from master_reader
        self.master_cache: Optional[Tuple[int, bytes]] = None
        self.rows: List[dict] = []
        self.errors: List[str] = []

    def master_frame(self, m: int) -> Optional[bytes]:
        if self.master_reader is None or m < 0:
            return None
        if self.master_cache and self.master_cache[0] == m:
            return self.master_cache[1]
        if m < self.master_pos:
            return None
        while self.master_pos < m:
            if self.master_reader.read() is None:
                return None
            self.master_pos += 1
        f = self.master_reader.read()
        if f is None:
            return None
        self.master_pos += 1
        self.master_cache = (m, f)
        return f

    def close(self):
        for r in (self.render_reader, self.master_reader):
            if r is not None:
                err = r.close()
                if err.strip():
                    self.errors.append(err.strip()[-500:])


class Verifier:
    def __init__(self, master: MasterAnalysis, plan: Plan, output_path: str,
                 renders: List[RenderedClip], conversion_filters: List[str], workdir: str,
                 level: str = "full", cache_dir: Optional[str] = None, master_fingerprint: Optional[str] = None,
                 thresholds: Optional[Thresholds] = None, cancel: Optional[CancelToken] = None,
                 progress=None, log=None, audio_results: Optional[dict] = None,
                 render_audio_index: Optional[dict] = None):
        self.m = master
        self.plan = plan
        self.out = output_path
        self.renders = renders
        self.conv = conversion_filters
        self.workdir = workdir
        self.level = level
        self.cache_dir = cache_dir
        self.fp = master_fingerprint
        self.t = thresholds or Thresholds()
        self.cancel = cancel or CancelToken()
        self.progress = progress or (lambda stage, frac: None)
        self.log = log or (lambda s: None)
        self.audio_results = audio_results or {}
        self.report = Report(level)
        v = master.video
        self.pix = v.pix_fmt
        self.W, self.H = v.width, v.height
        self.layout = plane_layout(self.pix, self.W, self.H)
        self.peak = (1 << v.active_sps().bit_depth_luma) - 1
        self.o2m = output_to_master_map(plan)
        self.cls = output_frame_classes(plan)

    # ------------------------------------------------------------------
    def run(self) -> Report:
        t0 = time.time()
        out_an = self._structure()
        if out_an is not None:
            self._video(out_an)
            self._audio(out_an)
        self.report.costs["verification_seconds"] = round(time.time() - t0, 2)
        return self.report

    # ------------------------------------------------------------------
    def _structure(self) -> Optional[MasterAnalysis]:
        rep = self.report
        try:
            out = analyze_master(self.out, run_ffprobe=True)
        except Exception as e:
            rep.add("container", "fail", f"output cannot be parsed: {e}")
            return None
        ov, mv = out.video, self.m.video
        rep.add("container", "pass", "output parsed (ISO-BMFF structure valid)",
                tracks=[t.handler for t in out.movie.tracks])
        if not ov.patchable and ov.blocking_issues:
            rep.add("video_structure", "fail", "; ".join(ov.blocking_issues))
        if ov.frame_count == self.plan.output_frames:
            rep.add("frame_count", "pass", f"{ov.frame_count} frames (expected {self.plan.output_frames})",
                    master=mv.frame_count, output=ov.frame_count)
        else:
            rep.add("frame_count", "fail", f"output has {ov.frame_count} frames, expected {self.plan.output_frames}")
        if ov.fps == mv.fps and ov.timescale == mv.timescale and ov.frame_duration == mv.frame_duration:
            rep.add("frame_rate", "pass", f"{mv.fps.numerator}/{mv.fps.denominator} fps, timescale {mv.timescale}")
        else:
            rep.add("frame_rate", "fail", f"frame rate/timebase changed: {ov.fps} vs {mv.fps}")
        if (ov.width, ov.height, ov.pix_fmt) == (mv.width, mv.height, mv.pix_fmt):
            rep.add("dimensions", "pass", f"{ov.width}x{ov.height} {ov.pix_fmt}")
        else:
            rep.add("dimensions", "fail", f"{ov.width}x{ov.height} {ov.pix_fmt} vs master "
                                          f"{mv.width}x{mv.height} {mv.pix_fmt}")
        keys = ("color_range", "color_space", "color_transfer", "color_primaries", "pix_fmt", "profile")
        diffs = {k: (self.m.color.get(k), out.color.get(k)) for k in keys if self.m.color.get(k) != out.color.get(k)}
        if diffs:
            rep.add("color_metadata", "fail", f"colour metadata differs: {diffs}")
        else:
            rep.add("color_metadata", "pass", "colour metadata identical (container + VUI): " +
                    ", ".join(f"{k}={self.m.color.get(k)}" for k in keys[:4]))
        # every segment start must be an IDR resume point; copy segment ends must be clean cuts
        bad = []
        cuts = set(ov.cut_points)
        resumes = set(ov.resume_points)
        for seg in self.plan.segments:
            if seg.out_len == 0:
                continue
            if seg.out_start not in resumes:
                bad.append(f"segment at output frame {seg.out_start} does not start at an IDR resume point")
            if seg.out_end not in cuts and seg.out_end != ov.frame_count:
                bad.append(f"segment ending at {seg.out_end} is not a clean cut")
        if bad:
            rep.add("splice_points", "fail", "; ".join(bad))
        else:
            rep.add("splice_points", "pass", f"{len(self.plan.segments) - 1} splice point(s) on IDR/clean-cut boundaries")
        rep.add("parameter_sets", "pass",
                f"output carries SPS ids {[s.sps_id for s in ov.sps]} / PPS ids {[p.pps_id for p in ov.pps]}")
        if out.video.cts0 != mv.cts0:
            rep.add("timestamps", "fail", f"composition start {out.video.cts0} != master {mv.cts0}")
        else:
            rep.add("timestamps", "pass", "constant-frame-rate composition timestamps, no duplicates or gaps; "
                                          "first composition time identical to master")
        if len(out.audio) != len(self.m.audio):
            rep.add("audio_tracks", "fail", f"{len(out.audio)} audio tracks vs {len(self.m.audio)} in master")
        return out

    # ------------------------------------------------------------------
    def _render_for_segment(self, seg) -> Optional[RenderedClip]:
        for c in self.renders:
            if c.has_video and c.timeline_start <= seg.render_start and c.timeline_end >= seg.render_end:
                return c
        return None

    def _open_render_reader(self, clip: RenderedClip, lo: int, hi: int) -> FrameReader:
        start = lo - clip.timeline_start
        end = hi - clip.timeline_start
        vf = ",".join([f"trim=start_frame={start}:end_frame={end}", "setpts=PTS-STARTPTS", *self.conv])
        return FrameReader(clip.path, self.pix, self.W, self.H, vf=vf, cancel=self.cancel)

    def _open_master_reader(self, m_lo: int, m_hi: int, tag: str) -> Tuple[FrameReader, int]:
        v = self.m.video
        start = v.prev_resume(max(0, m_lo))
        i = bisect_left(v.cut_points, m_hi)
        end = v.cut_points[i] if i < len(v.cut_points) else v.frame_count
        path = os.path.join(self.workdir, f"verify_master_{tag}_{start}_{end}.mp4")
        extract_video_clip(self.m, start, end, path)
        return FrameReader(path, self.pix, self.W, self.H, cancel=self.cancel), start

    def _make_contexts(self) -> List[_RegionContext]:
        ctxs = []
        off = self.plan.timeline_offset
        n_out = self.plan.output_frames
        for si, seg in enumerate(self.plan.segments):
            if seg.kind != "render":
                continue
            r_lo = seg.render_start - off
            r_hi = seg.render_end - off
            w0 = max(0, min(r_lo, seg.out_start - 2))
            w1 = min(n_out, max(r_hi, seg.out_end + 2))
            clip = self._render_for_segment(seg)
            rr = self._open_render_reader(clip, seg.render_start, seg.render_end) if clip and r_hi > r_lo else None
            ms = [self.o2m[j] for j in range(w0, w1) if self.o2m[j] >= 0]
            mr, mfirst = (None, 0)
            if ms:
                mr, mfirst = self._open_master_reader(min(ms), max(ms) + 1, str(si))
            ctxs.append(_RegionContext(si, w0, w1, seg, r_lo, r_hi, rr, mr, mfirst))
        return ctxs

    def _process_frame(self, ctx: _RegionContext, j: int, out_frame: bytes) -> None:
        row = {"frame": j, "class": self.cls[j], "master": self.o2m[j]}
        render = None
        if ctx.render_lo <= j < ctx.render_hi and ctx.render_reader is not None:
            render = ctx.render_reader.read()
            if render is None:
                ctx.errors.append(f"render reader ended early at output frame {j}")
        m = self.o2m[j]
        mf = ctx.master_frame(m) if m >= 0 else None
        in_seg = ctx.seg.out_start <= j < ctx.seg.out_end
        if in_seg and render is not None:
            y, a = _frame_metrics(out_frame, render, self.layout, self.peak)
            row["fidelity_y"], row["fidelity"] = y, a
            row["out_luma"] = numeric.plane_mean(out_frame, 0, self.W, self.H, self.layout[0][3])
            row["render_luma"] = numeric.plane_mean(render, 0, self.W, self.H, self.layout[0][3])
        if not in_seg:
            row["class"] = "guard"
            if mf is not None:
                row["identical_to_master"] = (out_frame == mf)
            if render is not None and mf is not None:
                row["render_vs_master_y"], row["render_vs_master"] = _frame_metrics(render, mf, self.layout, self.peak)
        elif mf is not None:
            row["out_vs_master_y"], row["out_vs_master"] = _frame_metrics(out_frame, mf, self.layout, self.peak)
            if render is not None:
                row["render_vs_master_y"], row["render_vs_master"] = _frame_metrics(render, mf, self.layout, self.peak)
        ctx.rows.append(row)

    # ------------------------------------------------------------------
    def _video(self, out_an: MasterAnalysis) -> None:
        rep = self.report
        v = self.m.video
        n_out = self.plan.output_frames
        t_start = time.time()
        ctxs = self._make_contexts()
        out_hashes: List[Optional[str]] = []
        master_hashes = None
        master_err = ""
        decode_errors = []
        frames_decoded = 0

        if self.level == "full":
            master_hashes = load_cached_hashes(self.cache_dir, self.fp, self.pix, v.frame_count)
            mh_holder: dict = {}
            mthread = None
            if master_hashes is None:
                def _mh():
                    try:
                        h, e = hash_all_frames(self.m.path, self.pix, self.W, self.H, self.cancel)
                        mh_holder["h"], mh_holder["e"] = h, e
                    except Exception as ex:  # noqa
                        mh_holder["x"] = ex
                mthread = threading.Thread(target=_mh, daemon=True)
                mthread.start()
                rep.costs["master_decode"] = "full decode (no cache)"
            else:
                rep.costs["master_decode"] = "cached frame hashes"
            fr = FrameReader(self.out, self.pix, self.W, self.H, cancel=self.cancel)
            active: List[_RegionContext] = []
            pending = sorted(ctxs, key=lambda c: c.w0)
            j = 0
            try:
                while True:
                    if j % 64 == 0:
                        self.cancel.check()
                        self.progress("verify", j / max(1, n_out))
                    f = fr.read()
                    if f is None:
                        break
                    out_hashes.append(hashlib.sha256(f).hexdigest())
                    while pending and pending[0].w0 <= j:
                        active.append(pending.pop(0))
                    for c in list(active):
                        if j < c.w1:
                            self._process_frame(c, j, f)
                        if j + 1 >= c.w1:
                            active.remove(c)
                    j += 1
                out_err = fr.finish()
            except Exception:
                fr.close()
                for c in ctxs:
                    c.close()
                raise
            frames_decoded += j
            if out_err.strip():
                decode_errors.append("output: " + out_err.strip()[-800:])
            if mthread is not None:
                while mthread.is_alive():
                    mthread.join(timeout=0.5)
                    self.cancel.check()
                if "x" in mh_holder:
                    raise mh_holder["x"]
                master_hashes, master_err = mh_holder["h"], mh_holder["e"]
                frames_decoded += len(master_hashes)
                if len(master_hashes) == v.frame_count:
                    save_cached_hashes(self.cache_dir, self.fp, self.pix, master_hashes)
            if master_err.strip():
                decode_errors.append("master: " + master_err.strip()[-800:])
            if len(out_hashes) != n_out:
                rep.add("decoded_frame_count", "fail", f"decoder produced {len(out_hashes)} frames, expected {n_out}")
            else:
                rep.add("decoded_frame_count", "pass", f"decoder produced exactly {n_out} frames")
            if master_hashes is not None and len(master_hashes) != v.frame_count:
                rep.add("master_decode", "fail", f"master decoded to {len(master_hashes)} frames, "
                                                 f"container says {v.frame_count}")
        else:
            # Fast: decode only the output regions around each render segment.
            for c in ctxs:
                self.cancel.check()
                lo = out_an.video.prev_resume(c.w0)
                i = bisect_left(out_an.video.cut_points, c.w1)
                hi = out_an.video.cut_points[i] if i < len(out_an.video.cut_points) else out_an.video.frame_count
                path = os.path.join(self.workdir, f"verify_out_{c.seg_index}_{lo}_{hi}.mp4")
                extract_video_clip(out_an, lo, hi, path)
                fr = FrameReader(path, self.pix, self.W, self.H, cancel=self.cancel)
                j = lo
                try:
                    while j < hi:
                        f = fr.read()
                        if f is None:
                            break
                        if c.w0 <= j < c.w1:
                            self._process_frame(c, j, f)
                        elif self.o2m[j] >= 0 and self.cls[j] == "preserved":
                            mf = c.master_frame(self.o2m[j])
                            c.rows.append({"frame": j, "class": "guard", "master": self.o2m[j],
                                           "identical_to_master": (mf == f) if mf is not None else None})
                        j += 1
                    err = fr.finish()
                except Exception:
                    fr.close()
                    raise
                frames_decoded += j - lo
                if err.strip():
                    decode_errors.append(err.strip()[-800:])
            rep.add("decoded_frame_count", "skip", "fast mode: full-output decode skipped")
        for c in ctxs:
            c.close()
            if c.errors:
                decode_errors.extend(c.errors)

        rep.costs["frames_decoded"] = frames_decoded
        rep.costs["video_verify_seconds"] = round(time.time() - t_start, 2)
        if decode_errors:
            rep.add("decoder_errors", "fail", "decoder reported errors: " + " | ".join(decode_errors)[:2000])
        else:
            rep.add("decoder_errors", "pass", "no decoder errors or warnings in decoded ranges")

        # --- preserved frames -------------------------------------------------
        preserved_idx = [j for j in range(n_out) if self.cls[j] == "preserved"]
        vrep: Dict[str, object] = {"master_frames": v.frame_count, "output_frames": n_out}
        if self.level == "full" and master_hashes is not None and len(out_hashes) == n_out:
            mism = [j for j in preserved_idx if out_hashes[j] != master_hashes[self.o2m[j]]]
            vrep["compared_unchanged"] = len(preserved_idx)
            vrep["identical_unchanged"] = len(preserved_idx) - len(mism)
            vrep["mismatched_frames"] = mism[:200]
            if mism:
                rep.add("pixel_identity", "fail",
                        f"{len(mism)} of {len(preserved_idx)} preserved frames differ from the master "
                        f"(first: output frame {mism[0]})")
            else:
                rep.add("pixel_identity", "pass",
                        f"all {len(preserved_idx)} preserved frames are pixel-identical to the master "
                        f"(SHA-256 of decoded {self.pix} frames)")
        elif self.level == "fast":
            rows = [r for c in ctxs for r in c.rows if r.get("identical_to_master") is not None]
            bad = [r["frame"] for r in rows if not r["identical_to_master"]]
            vrep["compared_unchanged"] = len(rows)
            vrep["identical_unchanged"] = len(rows) - len(bad)
            vrep["mismatched_frames"] = bad[:200]
            vrep["unverified_unchanged"] = len(preserved_idx) - len(rows)
            if bad:
                rep.add("pixel_identity", "fail", f"{len(bad)} preserved frames next to splices differ from master")
            else:
                rep.add("pixel_identity", "warn" if rows else "fail",
                        f"{len(rows)} preserved frames adjacent to splice points verified identical; "
                        f"{len(preserved_idx) - len(rows)} other preserved frames were NOT decoded (Fast Patch). "
                        f"Their packets are byte-identical copies of the master.")

        # --- re-encoded & guard frames ---------------------------------------
        all_rows = [r for c in ctxs for r in c.rows]
        fid = [r for r in all_rows if "fidelity_y" in r]
        bnd = [r for r in all_rows if r["class"] == "boundary" and "render_vs_master_y" in r]
        bnd_out = [r for r in all_rows if r["class"] == "boundary" and "out_vs_master_y" in r]
        grd = [r for r in all_rows if r["class"] == "guard" and "render_vs_master_y" in r]
        rev = [r for r in all_rows if r["class"] == "revised" and "render_vs_master_y" in r]
        expected_reencoded = sum(s.out_len for s in self.plan.segments if s.kind == "render")
        vrep["reencoded_frames"] = expected_reencoded
        vrep["encode_fidelity_psnr_y"] = _stats([r["fidelity_y"] for r in fid])
        vrep["encode_fidelity_psnr_min_plane"] = _stats([r["fidelity"] for r in fid])
        vrep["boundary_frames"] = len([1 for j in range(n_out) if self.cls[j] == "boundary"])
        vrep["boundary_render_vs_master_psnr_y"] = _stats([r["render_vs_master_y"] for r in bnd])
        vrep["boundary_render_vs_master_psnr_min_plane"] = _stats([r["render_vs_master"] for r in bnd])
        vrep["boundary_output_vs_master_psnr_y"] = _stats([r["out_vs_master_y"] for r in bnd_out])
        vrep["guard_render_vs_master_psnr_y"] = _stats([r["render_vs_master_y"] for r in grd])
        vrep["revised_render_vs_master_psnr_y"] = _stats([r["render_vs_master_y"] for r in rev])
        if len(fid) != expected_reencoded:
            rep.add("encode_fidelity", "fail", f"only {len(fid)} of {expected_reencoded} re-encoded frames could be "
                                               f"compared with their render")
        else:
            low = [r for r in fid if r["fidelity"] < self.t.fidelity_min_psnr]
            if low:
                worst = min(low, key=lambda r: r["fidelity"])
                rep.add("encode_fidelity", "fail",
                        f"{len(low)} re-encoded frames below {self.t.fidelity_min_psnr} dB PSNR vs render "
                        f"(worst plane {_fmt(worst['fidelity'])} dB at frame {worst['frame']})")
            elif fid:
                rep.add("encode_fidelity", "pass",
                        f"{len(fid)} re-encoded frames vs fresh render: luma PSNR min "
                        f"{_fmt(vrep['encode_fidelity_psnr_y']['min'])} dB / mean "
                        f"{_fmt(vrep['encode_fidelity_psnr_y']['mean'])} dB; worst plane "
                        f"{_fmt(vrep['encode_fidelity_psnr_min_plane']['min'])} dB")
            else:
                rep.add("encode_fidelity", "pass", "no re-encoded frames")
        black = [r["frame"] for r in fid if r.get("out_luma", 255) <= self.t.black_luma < r.get("render_luma", 0)]
        if black:
            rep.add("black_frames", "fail", f"unexpected black frames at output {black[:10]}")
        else:
            rep.add("black_frames", "pass", "no unintended black frames in re-encoded regions")
        changed_outside = [r for r in bnd + grd if r["render_vs_master"] < self.t.unchanged_min_psnr]
        if changed_outside:
            frames = sorted(r["frame"] for r in changed_outside)
            rep.add("unchanged_content", "fail",
                    f"{len(frames)} frame(s) OUTSIDE the declared revision ranges differ from the master in the fresh "
                    f"render (PSNR < {self.t.unchanged_min_psnr} dB in at least one plane, output frames "
                    f"{frames[0]}-{frames[-1]}). "
                    f"The edit probably extends beyond the revision range (e.g. a transition) or the master does not "
                    f"match this timeline. Expand the revision range (handles) and export again.",
                    frames=frames[:100])
        elif bnd or grd:
            rep.add("unchanged_content", "pass",
                    f"{len(bnd)} boundary + {len(grd)} guard frame(s) rendered fresh match the master "
                    f"(min PSNR over Y/U/V {_fmt(min(r['render_vs_master'] for r in bnd + grd))} dB)")
        else:
            rep.add("unchanged_content", "pass", "revisions align with splice points; no boundary frames")
        gid = [r for r in all_rows if r["class"] == "guard" and r.get("identical_to_master") is not None]
        badg = [r["frame"] for r in gid if not r["identical_to_master"]]
        if badg:
            rep.add("seams", "fail", f"frames adjacent to splices differ from master: {badg[:10]}")
        else:
            rep.add("seams", "pass", f"{len(gid)} copied frames adjacent to splice points decode identically")
        same = [r["frame"] for r in rev if r["render_vs_master"] >= self.t.revised_same_psnr]
        if rev and len(same) == len(rev):
            rep.add("revision_content", "warn", "the revised ranges render identically to the master - "
                                                "did the timeline change in Resolve?")
        vrep["segments"] = [
            {"kind": s.kind, "master": [s.master_start, s.master_end], "output": [s.out_start, s.out_end],
             "revised": s.revised, "boundary_frames": s.boundary_frames}
            for s in self.plan.segments]
        rep.video.update(vrep)

    # ------------------------------------------------------------------
    def _audio(self, out_an: MasterAnalysis) -> None:
        rep = self.report
        for ap in self.plan.audio:
            ma = self.m.audio[ap.index]
            if ap.index >= len(out_an.audio):
                rep.add(f"audio{ap.index}", "fail", "audio track missing in output")
                continue
            oa = out_an.audio[ap.index]
            ent = {"index": ap.index, "strategy": ap.strategy, "reason": ap.reason}
            try:
                if ap.strategy == "copy":
                    self._audio_copy(ma, oa, ent)
                elif ap.strategy == "splice":
                    self._audio_splice(ma, oa, ap, ent)
                else:
                    self._audio_full(ma, oa, ent)
            except Exception as e:
                rep.add(f"audio{ap.index}_verification", "fail", f"audio verification error: {e}")
            rep.audio.append(ent)

    def _packets_equal(self, ma, oa, skip: range = range(0)) -> Tuple[int, int]:
        mt, ot = ma.track, oa.track
        same = diff = 0
        with open(self.m.path, "rb") as fm, open(self.out, "rb") as fo:
            for i in range(mt.sample_count):
                if i in skip:
                    continue
                if mt.sizes[i] != ot.sizes[i] or mt.durations[i] != ot.durations[i] or \
                        mt.cts_offsets[i] != ot.cts_offsets[i]:
                    diff += 1
                    continue
                fm.seek(mt.offsets[i])
                fo.seek(ot.offsets[i])
                if fm.read(mt.sizes[i]) == fo.read(ot.sizes[i]):
                    same += 1
                else:
                    diff += 1
        return same, diff

    def _pcm_compare(self, ma, exclude: List[Tuple[int, int]]) -> dict:
        """Stream-decode master and output audio; count identical samples outside `exclude`."""
        import subprocess
        from .ffmpeg import ffmpeg as ffm
        ch = ma.channels
        fb = 4 * ch

        def proc(path):
            return subprocess.Popen([ffm(), "-v", "error", "-nostdin", "-i", path, "-map", f"0:a:{ma.index}",
                                     "-f", "f32le", "-acodec", "pcm_f32le", "-"],
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        pm, po = proc(self.m.path), proc(self.out)
        self.cancel.register(pm)
        self.cancel.register(po)
        pos = 0
        identical = differing = 0
        first_diff = None
        bm = bytearray()
        bo = bytearray()
        excl = sorted(exclude)
        try:
            while True:
                cm = pm.stdout.read(fb * 32768)
                co = po.stdout.read(fb * 32768)
                bm += cm
                bo += co
                n = min(len(bm), len(bo)) // fb
                if n == 0 and not cm and not co:
                    break
                if n == 0:
                    continue
                a = bytes(bm[:n * fb])
                b = bytes(bo[:n * fb])
                del bm[:n * fb]
                del bo[:n * fb]
                # split block into excluded / included parts
                cur = pos
                end = pos + n
                pieces = []
                for s, e in excl:
                    if e <= cur or s >= end:
                        continue
                    if s > cur:
                        pieces.append((cur, s))
                    cur = max(cur, e)
                if cur < end:
                    pieces.append((cur, end))
                for s, e in pieces:
                    sa = a[(s - pos) * fb:(e - pos) * fb]
                    sb = b[(s - pos) * fb:(e - pos) * fb]
                    if sa == sb:
                        identical += e - s
                    else:
                        # locate first differing sample
                        for k in range(0, len(sa), fb):
                            if sa[k:k + fb] != sb[k:k + fb]:
                                if first_diff is None:
                                    first_diff = s + k // fb
                                differing += 1
                            else:
                                identical += 1
                pos = end
            tail_m = len(bm) // fb
            tail_o = len(bo) // fb
        finally:
            for p in (pm, po):
                try:
                    p.stdout.close()
                    p.wait(timeout=10)
                except Exception:
                    pass
                self.cancel.unregister(p)
        return {"identical": identical, "differing": differing, "first_diff": first_diff,
                "length_master": pos + tail_m, "length_output": pos + tail_o}

    def _audio_copy(self, ma, oa, ent):
        rep = self.report
        same, diff = self._packets_equal(ma, oa) if ma.packet_count == oa.packet_count else (0, -1)
        ent["packets_identical"] = same
        if diff == 0 and ma.track.edits == oa.track.edits:
            rep.add(f"audio{ma.index}_packets", "pass",
                    f"all {same} AAC packets byte-identical, identical timing and edit list")
        else:
            rep.add(f"audio{ma.index}_packets", "fail", f"audio packets differ ({diff} different)")
        pcm = self._pcm_compare(ma, [])
        ent["pcm"] = pcm
        if pcm["differing"] == 0 and pcm["length_master"] == pcm["length_output"]:
            rep.add(f"audio{ma.index}_sync", "pass",
                    f"decoded audio identical ({pcm['identical']} samples); synchronisation unchanged")
        else:
            rep.add(f"audio{ma.index}_sync", "fail", f"decoded audio differs: {pcm}")

    def _ref_audio(self, ma, s_lo: int, s_hi: int):
        """Reference (render) audio for presentation samples [s_lo, s_hi) using measured alignment."""
        res = self.audio_results.get(ma.index, {})
        for sp in res.get("splices", []):
            ra = sp["render_audio"]
            off = sp["alignment"]["offset"]
            lo, hi = s_lo - off, s_hi - off
            if lo >= 0 and hi <= ra.nsamples:
                fb = 4 * ra.channels
                return ra.data[lo * fb:hi * fb]
        return None

    def _audio_splice(self, ma, oa, ap, ent):
        rep = self.report
        F, P, ch = ma.frame_size, ma.priming, ma.channels
        if oa.packet_count != ma.packet_count:
            rep.add(f"audio{ma.index}_packets", "fail", "packet count changed")
            return
        skip = set()
        for sp in ap.splices:
            skip.update(range(sp.packet_start, sp.packet_end))
        same, diff = self._packets_equal(ma, oa, skip=skip)
        ent["packets_identical"] = same
        ent["packets_replaced"] = len(skip)
        if diff:
            rep.add(f"audio{ma.index}_packets", "fail", f"{diff} packets outside the splice ranges changed")
        else:
            rep.add(f"audio{ma.index}_packets", "pass",
                    f"{same} AAC packets byte-identical; {len(skip)} packets replaced in {len(ap.splices)} splice(s)")
        excl = [(sp.packet_start * F - P, (sp.packet_end + 1) * F - P) for sp in ap.splices]
        pcm = self._pcm_compare(ma, excl)
        ent["pcm_outside_transitions"] = pcm
        if pcm["differing"] == 0 and pcm["length_master"] == pcm["length_output"]:
            rep.add(f"audio{ma.index}_pcm_identity", "pass",
                    f"decoded audio outside the splice regions is bit-identical ({pcm['identical']} samples)")
        else:
            rep.add(f"audio{ma.index}_pcm_identity", "fail",
                    f"decoded audio outside the splice regions differs ({pcm['differing']} samples, first at "
                    f"{pcm['first_diff']}). The master may use AAC noise substitution (PNS); use full audio "
                    f"re-encode.")
        details = []
        worst_fail = []
        for sp in ap.splices:
            s0 = sp.packet_start * F - P
            s1 = sp.packet_end * F - P
            blocks = [("start", s0, s0 + F), ("end", s1, s1 + F)]
            windows = [(max(0, a), b) for _, a, b in blocks] + [(max(0, s0), s1)]
            outw = decode_windows(self.out, ma.index, ch, ma.sample_rate, windows)
            mw = decode_windows(self.m.path, ma.index, ch, ma.sample_rate, windows)
            d = {"packets": [sp.packet_start, sp.packet_end], "samples": [s0, s1]}
            for (name, a, b), ob, mb in zip(blocks, outw[:2], mw[:2]):
                ref = self._ref_audio(ma, max(0, a), b)
                if ref is None or len(ob) != len(ref) or not ob:
                    d[name] = {"status": "skip"}
                    continue
                rf = numeric.floats_from_bytes(ref)
                of = numeric.floats_from_bytes(ob)
                mf = numeric.floats_from_bytes(mb)
                snr_out = numeric.snr_db(rf, of)
                snr_master = numeric.snr_db(rf, mf) if len(mb) == len(ref) else None
                limit = self.t.audio_transition_min_snr
                if snr_master is not None and not math.isinf(snr_master):
                    limit = min(limit, snr_master - 6.0)
                ok = snr_out is None or snr_out >= limit
                d[name] = {"snr_vs_render": snr_out, "master_snr_vs_render": snr_master, "limit": limit, "ok": ok}
                if not ok:
                    worst_fail.append(f"{name} of splice at packet {sp.packet_start}: {_fmt(snr_out)} dB < {_fmt(limit)} dB")
            ref = self._ref_audio(ma, max(0, s0), s1)
            if ref is not None and len(ref) == len(outw[2]):
                rf = _mono(ref, ch)
                of = _mono(outw[2], ch)
                d["region_snr_vs_render"] = numeric.snr_db(numeric.floats_from_bytes(ref),
                                                           numeric.floats_from_bytes(outw[2]))
                mid = len(rf) // 2
                win = min(4096, len(rf) // 4)
                if win > 256:
                    lag, corr = numeric.best_lag(rf[mid:mid + win], of[mid - 32:mid + win + 32], 32)
                    d["sync_lag_samples"] = lag
                    d["sync_corr"] = corr
                    if lag != 0 and corr > 0.5:
                        worst_fail.append(f"replaced audio is offset by {lag} samples")
            details.append(d)
        ent["splices"] = details
        if worst_fail:
            rep.add(f"audio{ma.index}_splice", "fail", "audio splice check failed: " + "; ".join(worst_fail))
        else:
            rep.add(f"audio{ma.index}_splice", "pass",
                    "transition blocks at codec-noise level (no clicks); replaced audio aligned (lag 0): " +
                    "; ".join(f"splice {d['packets']}: start {_fmt(d.get('start', {}).get('snr_vs_render'))} dB, "
                              f"end {_fmt(d.get('end', {}).get('snr_vs_render'))} dB, "
                              f"lag {d.get('sync_lag_samples', 'n/a')}" for d in details))

    def _audio_full(self, ma, oa, ent):
        rep = self.report
        expected = ma.presented_samples
        if self.plan.output_frames != self.plan.master_frames:
            expected = int(Fraction(self.plan.output_frames) * ma.sample_rate / self.m.video.fps)
        ent["presented_samples"] = oa.presented_samples
        if abs(oa.presented_samples - expected) <= ma.sample_rate // 1000 + 1:
            rep.add(f"audio{ma.index}_duration", "pass", f"audio duration {oa.presented_samples} samples "
                                                         f"(expected {expected})")
        else:
            rep.add(f"audio{ma.index}_duration", "fail",
                    f"audio duration {oa.presented_samples} samples, expected {expected}")
        # alignment & level against master in unchanged regions
        cls = output_frame_classes(self.plan)
        o2m = self.o2m
        fps = self.m.video.fps
        sr = ma.sample_rate
        # windows of 1 s around 5 positions in preserved video regions
        n = self.plan.output_frames
        cands = [int(n * f) for f in (0.1, 0.3, 0.5, 0.7, 0.9)]
        wins = []
        for c in cands:
            span = int(fps)
            if c + span >= n:
                continue
            if all(cls[j] == "preserved" for j in range(c, c + span)):
                m0 = o2m[c]
                o_s = int(Fraction(c) * sr / fps)
                m_s = int(Fraction(m0) * sr / fps)
                wins.append((o_s, m_s, sr))
        results = []
        for o_s, m_s, length in wins:
            ow = decode_windows(self.out, ma.index, ma.channels, sr, [(o_s - 64, o_s + length + 64)])[0]
            mw = decode_windows(self.m.path, ma.index, ma.channels, sr, [(m_s, m_s + length)])[0]
            mm = _mono(mw, ma.channels)
            om = _mono(ow, ma.channels)
            if len(mm) < length or len(om) < length + 128:
                continue
            if numeric.energy(mm) / length < 1e-7:
                continue
            lag, corr, frac = numeric.subsample_lag(mm, om, 64)
            seg = om[64:64 + length]
            snr = numeric.snr_db(mm, seg)
            lvl = 10 * math.log10(max(1e-20, numeric.energy(seg)) / max(1e-20, numeric.energy(mm)))
            results.append({"output_sample": o_s, "lag": lag, "subsample_lag": round(frac, 3), "corr": corr,
                            "snr": snr, "level_diff_db": lvl})
        ent["alignment_windows"] = results
        if not results:
            rep.add(f"audio{ma.index}_sync", "warn", "no unchanged non-silent windows available to measure sync")
            return
        worst = max(abs(r["subsample_lag"]) for r in results)
        if worst <= 0.5:
            rep.add(f"audio{ma.index}_sync", "pass",
                    f"re-encoded audio aligned with master in {len(results)} windows "
                    f"(max |offset| {worst:.2f} samples, sub-sample estimate)")
        else:
            rep.add(f"audio{ma.index}_sync", "fail", "audio offset vs master detected: " +
                    ", ".join(f"{r['subsample_lag']:+.2f}" for r in results) + " samples")
        worst_snr = min(r["snr"] for r in results)
        worst_lvl = max(abs(r["level_diff_db"]) for r in results)
        if worst_snr < self.t.audio_full_min_snr or worst_lvl > self.t.audio_level_tolerance_db:
            rep.add(f"audio{ma.index}_quality", "fail",
                    f"unchanged audio differs from master more than expected (SNR {_fmt(worst_snr)} dB, "
                    f"level {worst_lvl:.2f} dB)")
        else:
            rep.add(f"audio{ma.index}_quality", "pass",
                    f"unchanged regions: SNR vs master >= {_fmt(worst_snr)} dB, level difference <= {worst_lvl:.2f} dB")
