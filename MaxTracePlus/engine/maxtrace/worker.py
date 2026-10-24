"""Out-of-process job runner.

The Fusion launcher writes ``job.json`` into a fresh job directory and starts
this worker in the background. The worker reports progress in
``status.lua``/``status.json`` (atomic replace) and finishes with
``result.lua``/``result.json``. Lua reads the ``.lua`` variants (plain table
literals) so no JSON parser is needed inside Fusion. A ``cancel`` file in the
job directory aborts the job at the next checkpoint.

Jobs: ``analyze`` (detection + preview), ``build`` (detection + highlight
output), ``verify`` (measure frames rendered by Fusion), ``clean`` (cache).
"""

from __future__ import annotations

import hashlib
import json
import logging
import logging.handlers
import os
import shutil
import sys
import time
import traceback
import uuid
from typing import Any

import numpy as np

from . import __version__
from . import detect as det
from . import geometry as geo
from .easing import Curve, duration_to_frames, frame_progress
from .fusion_setting import Calibration, NativeStyle, native_setting, raster_setting
from .imageio import ImageLoadError, file_digest, hex_to_rgb, load_rgb, rgb_to_hex, rgb_to_lab
from .luaser import to_lua
from .render import SequenceSpec, StrokeStyle, render_preview, render_sequence

log = logging.getLogger("maxtrace")


class JobError(RuntimeError):
    def __init__(self, message: str, code: str = "error"):
        super().__init__(message)
        self.code = code


class Cancelled(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Status / IO helpers
# --------------------------------------------------------------------------


def _atomic_write(path: str, text: str) -> None:
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _jsonable(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, np.ndarray):
        return _jsonable(v.tolist())
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


class Job:
    def __init__(self, job_dir: str):
        self.dir = job_dir
        self.started = time.time()
        self._last_status = 0.0

    def cancelled(self) -> bool:
        return os.path.exists(os.path.join(self.dir, "cancel"))

    def check(self) -> None:
        if self.cancelled():
            raise Cancelled()

    def status(self, stage: str, progress: float, message: str, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_status < 0.08:
            return
        self._last_status = now
        data = {
            "stage": stage,
            "progress": round(float(max(0.0, min(1.0, progress))), 4),
            "message": message,
            "time": now,
            "pid": os.getpid(),
        }
        _atomic_write(os.path.join(self.dir, "status.json"), json.dumps(data))
        _atomic_write(os.path.join(self.dir, "status.lua"), to_lua(data))

    def finish(self, result: dict[str, Any]) -> None:
        result = _jsonable(result)
        result.setdefault("elapsed", round(time.time() - self.started, 3))
        _atomic_write(os.path.join(self.dir, "result.json"), json.dumps(result, indent=1))
        _atomic_write(os.path.join(self.dir, "result.lua"), to_lua(result))


def setup_logging(log_dir: str | None, verbose: bool = False) -> None:
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    if log.handlers:
        return
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        h = logging.handlers.RotatingFileHandler(os.path.join(log_dir, "worker.log"), maxBytes=2_000_000, backupCount=3)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(process)d] %(message)s"))
        log.addHandler(h)
    else:
        log.addHandler(logging.StreamHandler(sys.stderr))


# --------------------------------------------------------------------------
# Analysis (cached)
# --------------------------------------------------------------------------


def _analysis_cache_path(cache_dir: str, digest: str, params: det.DetectParams) -> str:
    key = json.dumps({"img": digest, "p": params.cache_key(), "v": __version__}, sort_keys=True)
    h = hashlib.sha1(key.encode()).hexdigest()[:24]
    return os.path.join(cache_dir, "analysis", h + ".json")


def _line_from_dict(d: dict[str, Any]) -> det.TracedLine:
    return det.TracedLine(
        id=int(d["id"]),
        kind=d["kind"],
        color_rgb=tuple(d["color_rgb"]),
        dense=np.asarray(d["dense"], float),
        path=np.asarray(d["path"], float),
        thickness=float(d["thickness"]),
        coverage=float(d["coverage"]),
        span=float(d["span"]),
        max_gap=float(d["max_gap"]),
        ambiguity=float(d["ambiguity"]),
        residual=float(d["residual"]),
        confidence=float(d["confidence"]),
        score=float(d["score"]),
        method=d["method"],
        ambiguous_ranges=[tuple(r) for r in d.get("ambiguous_ranges", [])],
        parts=d.get("parts", []),
        notes=d.get("notes", []),
    )


def _line_to_dict(t: det.TracedLine) -> dict[str, Any]:
    return {
        "id": t.id,
        "kind": t.kind,
        "color_rgb": list(t.color_rgb),
        "dense": t.dense[:: max(1, len(t.dense) // 6000)].tolist(),
        "path": t.path.tolist(),
        "thickness": t.thickness,
        "coverage": t.coverage,
        "span": t.span,
        "max_gap": t.max_gap,
        "ambiguity": t.ambiguity,
        "residual": t.residual,
        "confidence": t.confidence,
        "score": t.score,
        "method": t.method,
        "ambiguous_ranges": [list(r) for r in t.ambiguous_ranges],
        "parts": t.parts,
        "notes": t.notes,
    }


def run_analysis(job: Job, spec: dict[str, Any], cache_dir: str | None) -> tuple[det.Analysis, np.ndarray, bool]:
    image = spec.get("image")
    if not image:
        raise JobError("No source image was provided.", "no_image")
    params = det.DetectParams.from_dict(spec.get("detect"))
    job.status("load", 0.03, "Reading source frame", force=True)
    if not os.path.isfile(image):
        raise JobError("The source image is missing: {}".format(os.path.basename(image)), "image_load")
    try:
        digest = file_digest(image)
        rgb = load_rgb(image)
    except ImageLoadError as e:
        raise JobError(str(e), "image_load") from e
    job.check()
    # Selection does not change detection: cache without it.
    sel_free = det.DetectParams.from_dict({**(spec.get("detect") or {}), "candidate": None, "candidate_hex": None})
    cpath = _analysis_cache_path(cache_dir, digest, sel_free) if cache_dir else None
    analysis = None
    from_cache = False
    if cpath and os.path.isfile(cpath):
        try:
            with open(cpath, "r", encoding="utf-8") as f:
                d = json.load(f)
            analysis = det.Analysis(
                width=d["width"],
                height=d["height"],
                background_rgb=tuple(d["background_rgb"]),
                region_px=tuple(d["region_px"]),
                region_source=d["region_source"],
                lines=[_line_from_dict(x) for x in d["lines"]],
                selected=d["selected"],
                warnings=list(d["warnings"]),
            )
            if analysis.width != rgb.shape[1] or analysis.height != rgb.shape[0]:
                analysis = None
            else:
                from_cache = True
        except Exception:  # corrupt cache: recompute
            log.warning("ignoring unreadable analysis cache %s", cpath)
            analysis = None
    if analysis is None:
        job.status("detect", 0.08, "Detecting graph line", force=True)
        t0 = time.time()
        try:
            analysis = det.analyze(rgb, sel_free)
        except det.DetectionError as e:
            raise JobError(str(e), e.code) from e
        log.info("analysis %s: %d candidates in %.2fs", os.path.basename(image), len(analysis.lines), time.time() - t0)
        if cpath:
            os.makedirs(os.path.dirname(cpath), exist_ok=True)
            payload = {
                "width": analysis.width,
                "height": analysis.height,
                "background_rgb": list(analysis.background_rgb),
                "region_px": list(analysis.region_px),
                "region_source": analysis.region_source,
                "lines": [_line_to_dict(t) for t in analysis.lines],
                "selected": analysis.selected,
                "warnings": analysis.warnings,
            }
            _atomic_write(cpath, json.dumps(payload))
    job.check()
    # Apply the candidate selection.
    analysis.warnings = [w for w in analysis.warnings if "previously chosen" not in w]
    if params.candidate is not None or params.candidate_hex:
        chosen = None
        if params.candidate_hex:
            want = np.asarray(hex_to_rgb(params.candidate_hex))
            best = min(analysis.lines, key=lambda t: float(np.linalg.norm(np.asarray(t.color_rgb) - want)) + (0 if t.id == params.candidate else 0.03))
            if float(np.linalg.norm(np.asarray(best.color_rgb) - want)) < 0.15:
                chosen = best.id
        elif params.candidate is not None and any(t.id == params.candidate for t in analysis.lines):
            chosen = params.candidate
        if chosen is None:
            analysis.warnings.append("The previously chosen line was not found again; using the best match.")
        else:
            analysis.selected = chosen
    return analysis, rgb, from_cache


# --------------------------------------------------------------------------
# Style / timing
# --------------------------------------------------------------------------

DEFAULT_STYLE = {
    "color": "#FF2020",
    "thickness": 7.0,  # px at the output resolution, 1080p reference
    "opacity": 1.0,
    "softness": 0.1,
    "halo": 0.0,
    "glow": 0.0,
}


def thickness_in_source(style: dict[str, Any], img_w: int, img_h: int, out_w: int | None, out_h: int | None) -> float:
    """Convert the UI thickness (pixels at the output frame) to source pixels.

    The UI value is defined at 1080p and scales with the output height so a
    preset keeps its visual weight at 1440p/2160p. The source image is shown
    fitted into the output frame (Resolve's default scaling), so the stroke
    drawn at source resolution is divided by that fit scale.
    """
    t = float(style.get("thickness", DEFAULT_STYLE["thickness"]))
    if not (0.5 <= t <= 120):
        raise JobError("Thickness must be between 0.5 and 120 px.", "bad_style")
    ow = int(out_w or img_w)
    oh = int(out_h or img_h)
    out_px = t * (min(ow / 1920.0, oh / 1080.0))
    fit = min(ow / float(img_w), oh / float(img_h))
    return max(0.5, out_px / max(fit, 1e-6))


def color_similarity_warnings(analysis: det.Analysis, line: det.TracedLine, highlight_rgb: tuple[float, float, float]) -> list[dict[str, str]]:
    warns = []
    hl = rgb_to_lab(np.asarray(highlight_rgb, np.float32).reshape(1, 1, 3)).reshape(3)

    def de(rgb) -> float:
        lab = rgb_to_lab(np.asarray(rgb, np.float32).reshape(1, 1, 3)).reshape(3)
        return float(np.linalg.norm(lab - hl))

    if line.kind == "joined" and line.parts:
        for part in line.parts:
            if de(hex_to_rgb(part["color"])) < 22:
                warns.append(
                    {
                        "code": "already_highlighted",
                        "message": "{:.0f}-{:.0f}% of this line is already drawn in {}. A {} highlight there will barely be visible; use a contrasting colour or an unhighlighted source.".format(
                            part["from"] * 100, part["to"] * 100, part["color"], rgb_to_hex(highlight_rgb)
                        ),
                    }
                )
    elif de(line.color_rgb) < 22:
        warns.append(
            {
                "code": "same_color",
                "message": "The traced line is already {}; a {} highlight on top of it will be hard to see. Pick a contrasting colour (e.g. Marker Yellow) or add Soft/Glow.".format(
                    rgb_to_hex(line.color_rgb), rgb_to_hex(highlight_rgb)
                ),
            }
        )
    return warns


# --------------------------------------------------------------------------
# Job handlers
# --------------------------------------------------------------------------


def _preview(job: Job, analysis: det.Analysis, rgb: np.ndarray, trim: tuple[float, float], hl_rgb, spec: dict[str, Any]) -> dict[str, Any] | None:
    out = spec.get("preview_path") or os.path.join(job.dir, "preview.png")
    try:
        return render_preview(
            rgb,
            analysis.lines,
            analysis.selected,
            out,
            trim=trim,
            region=tuple(analysis.region_px),
            highlight_rgb=hl_rgb,
            max_width=int(spec.get("preview_width", 440)),
        )
    except Exception:  # preview is cosmetic
        log.exception("preview failed")
        return None


def handle_analyze(job: Job, spec: dict[str, Any]) -> dict[str, Any]:
    analysis, rgb, cached = run_analysis(job, spec, spec.get("cache_dir"))
    style = {**DEFAULT_STYLE, **(spec.get("style") or {})}
    hl_rgb = hex_to_rgb(style["color"])
    rng = spec.get("range") or {}
    trim = (float(rng.get("start", 0.0)), float(rng.get("end", 1.0)))
    job.status("preview", 0.9, "Preparing preview", force=True)
    prev = _preview(job, analysis, rgb, trim, hl_rgb, spec)
    line = analysis.selected_line()
    return {
        "ok": True,
        "job": "analyze",
        "analysis": analysis.to_dict(),
        "cached": cached,
        "preview": prev,
        "selected": line.summary(analysis.width, analysis.height),
        "warnings": [{"code": "detect", "message": w} for w in analysis.warnings]
        + color_similarity_warnings(analysis, line, hl_rgb),
    }


def handle_build(job: Job, spec: dict[str, Any]) -> dict[str, Any]:
    analysis, rgb, cached = run_analysis(job, spec, spec.get("cache_dir"))
    line = analysis.selected_line()
    W, H = analysis.width, analysis.height
    if line.confidence < float(spec.get("min_confidence", 0.35)) and not spec.get("force"):
        raise JobError(
            "Detection confidence is too low ({:.0%}). Check the preview, pick the line colour, or restrict the region; then try again.".format(
                line.confidence
            ),
            "low_confidence",
        )
    style = {**DEFAULT_STYLE, **(spec.get("style") or {})}
    try:
        hl_rgb = hex_to_rgb(style["color"])
    except ValueError as e:
        raise JobError(str(e), "bad_style") from e
    out = spec.get("output") or {}
    comp_w, comp_h = out.get("comp_width"), out.get("comp_height")
    thick = thickness_in_source(style, W, H, comp_w, comp_h)

    rng = spec.get("range") or {}
    r0, r1 = float(rng.get("start", 0.0)), float(rng.get("end", 1.0))
    if not (0.0 <= r0 < r1 <= 1.0) or r1 - r0 < 0.005:
        raise JobError("Trace range must satisfy 0% <= start < end <= 100%.", "bad_range")
    path = geo.trim_fraction(line.path, r0, r1)
    if geo.total_length(path) < 2.0:
        raise JobError("The selected trace range is too short.", "bad_range")
    # An imported image (or original media file) can differ in size from the
    # node it is drawn over: fit it (uniform scale, centred) to that node.
    tw, th = out.get("target_width"), out.get("target_height")
    fit_note = None
    if tw and th and (int(tw), int(th)) != (W, H):
        tw, th = int(tw), int(th)
        sc = min(tw / float(W), th / float(H))
        ox, oy = (tw - W * sc) / 2.0, (th - H * sc) / 2.0
        path = path * sc + np.array([ox, oy])
        if abs(tw / float(th) - W / float(H)) > 0.01:
            fit_note = "The image aspect ratio differs from the node ({}x{} vs {}x{}); the trace was fitted to the node.".format(W, H, tw, th)
        W, H = tw, th
        thick = thickness_in_source(style, W, H, comp_w, comp_h)

    timing = spec.get("timing") or {}
    fps = float(timing.get("fps") or 0)
    if not (1.0 <= fps <= 240.0):
        raise JobError("Unsupported or unknown frame rate ({}).".format(timing.get("fps")), "bad_fps")
    duration = float(timing.get("duration", 2.5))
    if not (0.1 <= duration <= 60.0):
        raise JobError("Duration must be between 0.1 and 60 seconds.", "bad_timing")
    frames = duration_to_frames(duration, fps)
    try:
        curve = Curve.from_settings(timing.get("motion", "linear"), timing.get("custom"))
    except ValueError as e:
        raise JobError(str(e), "bad_timing") from e
    anim_start = int(timing.get("start_frame", 0))
    comp_start = int(timing.get("comp_start", anim_start))
    comp_end = int(timing.get("comp_end", anim_start + frames))
    if comp_end < comp_start:
        raise JobError("Invalid composition frame range.", "bad_timing")

    mode = out.get("mode", "native")
    gen_id = out.get("gen_id") or uuid.uuid4().hex[:12]
    warnings = [{"code": "detect", "message": w} for w in analysis.warnings]
    warnings += color_similarity_warnings(analysis, line, hl_rgb)
    if thick < line.thickness * 1.1:
        warnings.append(
            {
                "code": "thin",
                "message": "The highlight ({:.1f}px) is not thicker than the source line ({:.1f}px); increase Thickness to cover it.".format(
                    thick, line.thickness
                ),
            }
        )
    if anim_start + frames > comp_end:
        warnings.append(
            {
                "code": "beyond_range",
                "message": "The animation ends after the composition's last frame ({}); the full line will not be reached on screen.".format(comp_end),
            }
        )

    if fit_note:
        warnings.append({"code": "fit", "message": fit_note})
    job.status("path", 0.5, "Generating path", force=True)
    preview = _preview(job, analysis, rgb, (r0, r1), hl_rgb, spec)
    mid_frame = anim_start + max(1, frames // 2)
    mid_progress = float(frame_progress(curve, anim_start, frames, np.array([mid_frame]))[0])
    result: dict[str, Any] = {
        "ok": True,
        "job": "build",
        "gen_id": gen_id,
        "mode": mode,
        "width": W,
        "height": H,
        "analysis": analysis.to_dict(),
        "selected": line.summary(W, H),
        "cached": cached,
        "preview": preview,
        "thickness_px": thick,
        "color": rgb_to_hex(hl_rgb),
        "anim_start": anim_start,
        "anim_frames": frames,
        "anim_end": anim_start + frames,
        "mid_frame": mid_frame,
        "mid_progress": mid_progress,
        "range": [r0, r1],
        "path_px": path.tolist(),
        "warnings": warnings,
    }

    setting_path = os.path.join(job.dir, "highlight.setting")
    if mode == "native":
        cal = Calibration.from_dict(spec.get("calibration"))
        L = geo.total_length(path)
        dense_path = geo.resample_preserving_vertices(path, max(3.0, L / 400.0))
        nstyle = NativeStyle(
            color=hl_rgb,
            thickness_px=thick,
            opacity=float(style.get("opacity", 1.0)),
            softness=float(style.get("softness", 0.0)),
            halo=float(style.get("halo", 0.0)),
            glow=float(style.get("glow", 0.0)),
        )
        st = native_setting(gen_id, dense_path, W, H, nstyle, anim_start, frames, curve, cal)
        _atomic_write(setting_path, st["text"])
        result.update(
            {
                "setting": setting_path,
                "tools": st["tools"],
                "layer_tool": st["layer_tool"],
                "merge_tool": st["merge_tool"],
                "calibration": cal.to_dict(),
                "native_points": len(dense_path),
                "path_sent_px": dense_path.tolist(),
                "editable": True,
            }
        )
    elif mode == "raster":
        render_root = out.get("render_dir")
        if not render_root:
            raise JobError("No render directory configured.", "config")
        rstyle = StrokeStyle(
            color=hl_rgb,
            thickness=thick,
            opacity=float(style.get("opacity", 1.0)),
            softness=float(style.get("softness", 0.0)),
            halo=float(style.get("halo", 0.0)),
            glow=float(style.get("glow", 0.0)),
        )
        key = hashlib.sha1(
            json.dumps(
                {
                    "p": np.round(path, 3).tolist(),
                    "s": [rstyle.color, rstyle.thickness, rstyle.opacity, rstyle.softness, rstyle.halo, rstyle.glow],
                    "t": [comp_start, comp_end, anim_start, frames, curve.x1, curve.y1, curve.x2, curve.y2, curve.linear],
                    "wh": [W, H],
                    "v": __version__,
                }
            ).encode()
        ).hexdigest()[:16]
        seq_dir = os.path.join(render_root, key)
        manifest = os.path.join(seq_dir, "manifest.json")
        info = None
        if os.path.isfile(manifest):
            try:
                with open(manifest) as f:
                    info = json.load(f)
                if not os.path.isfile(info["first_file"]) or info.get("frames") != comp_end - comp_start + 1:
                    info = None
            except Exception:
                info = None
        if info is None:
            _check_disk(render_root, W, H, comp_end - comp_start + 1, frames)
            tmp_dir = seq_dir + ".partial"
            if os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

            def prog(p: float, msg: str) -> None:
                job.status("render", 0.55 + 0.4 * p, msg)

            try:
                info = render_sequence(
                    path,
                    W,
                    H,
                    rstyle,
                    SequenceSpec(comp_start, comp_end, anim_start, frames, curve),
                    tmp_dir,
                    progress_cb=prog,
                    cancel_cb=job.cancelled,
                )
            except InterruptedError as e:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise Cancelled() from e
            except Exception:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise
            if os.path.isdir(seq_dir):
                shutil.rmtree(seq_dir, ignore_errors=True)
            os.replace(tmp_dir, seq_dir)
            info["first_file"] = os.path.join(seq_dir, os.path.basename(info["first_file"]))
            info["pattern"] = os.path.join(seq_dir, os.path.basename(info["pattern"]))
            with open(manifest, "w") as f:
                json.dump({**info, "path_px": path.tolist(), "created": time.time()}, f)
        st = raster_setting(gen_id, info["first_file"], info["frames"], comp_start, anim_start)
        _atomic_write(setting_path, st["text"])
        result.update(
            {
                "setting": setting_path,
                "tools": st["tools"],
                "layer_tool": st["layer_tool"],
                "merge_tool": st["merge_tool"],
                "sequence": {
                    "dir": seq_dir,
                    "first_file": info["first_file"],
                    "frames": info["frames"],
                    "global_start": comp_start,
                },
                "path_sent_px": path.tolist(),
                "editable": False,
            }
        )
    else:
        raise JobError(f"Unknown output mode '{mode}'.", "config")
    job.status("done", 1.0, "Output ready", force=True)
    return result


def _check_disk(root: str, w: int, h: int, total: int, unique: int) -> None:
    os.makedirs(root, exist_ok=True)
    need = int(unique * w * h * 0.6) + 50_000_000  # generous PNG estimate
    free = shutil.disk_usage(root).free
    if free < need:
        raise JobError(
            "Not enough disk space for the rendered highlight ({:.0f} MB needed, {:.0f} MB free).".format(need / 1e6, free / 1e6),
            "disk_full",
        )


def handle_verify(job: Job, spec: dict[str, Any]) -> dict[str, Any]:
    from .verify import VerifyInput, verify

    v = spec.get("verify") or {}
    frames = {k: p for k, p in (v.get("frames") or {}).items() if p}
    if "end" not in frames:
        raise JobError("No rendered frames to verify.", "verify")
    inp = VerifyInput(
        frames=frames,
        expected_px=np.asarray(v["path_px"], float),
        width=int(v["width"]),
        height=int(v["height"]),
        thickness_px=float(v["thickness_px"]),
        color=hex_to_rgb(v.get("color", "#FF2020")),
        mid_progress=float(v.get("mid_progress", 0.5)),
        calibration=Calibration.from_dict(v.get("calibration")),
        mode=v.get("mode", "native"),
    )
    job.status("verify", 0.3, "Checking rendered result", force=True)
    res = verify(inp)
    res["job"] = "verify"
    res.setdefault("ok", False)
    return res


def handle_clean(job: Job, spec: dict[str, Any]) -> dict[str, Any]:
    root = spec.get("cache_dir")
    if not root or not os.path.isdir(root):
        return {"ok": True, "job": "clean", "removed_bytes": 0}
    keep = {os.path.realpath(p) for p in (spec.get("keep") or [])}
    removed = 0
    root_real = os.path.realpath(root)
    for sub in ("analysis", "grabs", "previews"):
        d = os.path.join(root_real, sub)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            p = os.path.join(d, name)
            if os.path.realpath(p) in keep:
                continue
            removed += _remove(p, root_real)
    jobs = os.path.join(root_real, "jobs")
    if os.path.isdir(jobs):
        for name in os.listdir(jobs):
            p = os.path.join(jobs, name)
            if os.path.realpath(p) == os.path.realpath(job.dir):
                continue
            removed += _remove(p, root_real)
    renders = spec.get("render_dir")
    if renders and os.path.isdir(renders) and spec.get("clean_renders"):
        rr = os.path.realpath(renders)
        for name in os.listdir(rr):
            p = os.path.join(rr, name)
            if os.path.realpath(p) in keep:
                continue
            removed += _remove(p, rr)
    return {"ok": True, "job": "clean", "removed_bytes": removed}


def _remove(path: str, must_be_under: str) -> int:
    real = os.path.realpath(path)
    if not real.startswith(must_be_under + os.sep):
        return 0  # never delete outside the MaxTrace+ directories
    size = 0
    if os.path.isdir(real) and not os.path.islink(real):
        for dp, _, files in os.walk(real):
            for fn in files:
                try:
                    size += os.path.getsize(os.path.join(dp, fn))
                except OSError:
                    pass
        shutil.rmtree(real, ignore_errors=True)
    else:
        try:
            size = os.path.getsize(real)
            os.remove(real)
        except OSError:
            pass
    return size


HANDLERS = {"analyze": handle_analyze, "build": handle_build, "verify": handle_verify, "clean": handle_clean}


def run_job(job_dir: str) -> int:
    job = Job(job_dir)
    spec_path = os.path.join(job_dir, "job.json")
    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
    except Exception as e:  # noqa: BLE001
        job.finish({"ok": False, "code": "bad_job", "message": f"Unreadable job file: {e}"})
        return 2
    setup_logging(spec.get("log_dir"), bool(spec.get("diagnostics")))
    kind = spec.get("job")
    log.info("job %s (%s) started", os.path.basename(job_dir), kind)
    try:
        handler = HANDLERS.get(kind)
        if handler is None:
            raise JobError(f"Unknown job type '{kind}'.", "bad_job")
        job.status("start", 0.01, "Starting", force=True)
        result = handler(job, spec)
        job.finish(result)
        log.info("job %s finished ok in %.2fs", os.path.basename(job_dir), time.time() - job.started)
        return 0
    except Cancelled:
        job.finish({"ok": False, "code": "cancelled", "message": "Cancelled."})
        log.info("job %s cancelled", os.path.basename(job_dir))
        return 3
    except JobError as e:
        job.finish({"ok": False, "code": e.code, "message": str(e)})
        log.warning("job %s failed: %s (%s)", os.path.basename(job_dir), e, e.code)
        return 1
    except Exception as e:  # noqa: BLE001 - must never leave the launcher hanging
        tb = traceback.format_exc()
        log.error("job %s crashed: %s\n%s", os.path.basename(job_dir), e, tb)
        job.finish({"ok": False, "code": "internal", "message": "Internal error: {}".format(e), "traceback": tb})
        return 4


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: maxtrace_worker.py <job_dir> | --selftest")
        return 0
    if argv[0] == "--selftest":
        import cv2  # noqa: F401

        print(json.dumps({"ok": True, "version": __version__, "numpy": np.__version__, "opencv": cv2.__version__}))
        return 0
    return run_job(os.path.abspath(argv[0]))
