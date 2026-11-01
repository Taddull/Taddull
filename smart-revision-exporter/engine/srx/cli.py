"""Command line interface (also the process boundary used by the macOS app).

    python3 -m srx doctor
    python3 -m srx probe master.mp4
    python3 -m srx plan master.mp4 --rev 1800:1950
    python3 -m srx export master.mp4 -o master_rev2.mp4 --rev 1800:1950 --source resolve
    python3 -m srx export --request request.json --json
    python3 -m srx prepare-master -o rr_master.mp4 --source resolve --gop-seconds 1
    python3 -m srx full-export -o full.mp4 --source resolve --reference master.mp4 [--resolve-preset NAME]
    python3 -m srx resolve status|ranges|alignment
    python3 -m srx jobs list|recover
    python3 -m srx project status|approve FILE
    python3 -m srx frame master.mp4 --index 1234 -o frame.png
    python3 -m srx filmstrip master.mp4 -o strip.png

With --json every event is a JSON object on its own line (stdout).
Exit codes: 0 success, 1 failure, 2 usage error, 3 verification failed, 130 cancelled.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import signal
import subprocess
import sys
from fractions import Fraction
from typing import List, Optional

from . import BUILD_KIND, __version__, jsonutil
from .events import Emitter
from .ffmpeg import CancelToken, Cancelled, ToolError, encoders, ffmpeg, version_info
from .jobs import ProjectStore, app_support_dir, list_jobs, recover_jobs
from .media import AnalysisError, analyze_master, file_sha256, gop_map
from .plan import PlanError, Revision
from .render import FileRenderSource, ManualRender, SyntheticRenderSource
from .synthetic import SynthTimeline
from .timecode import frames_to_tc, parse_rate, tc_to_frames


def _parse_rev(spec: str) -> Revision:
    """'START:END[,flag...]' frames (end exclusive). Flags: video, audio, hb=N, ha=N, delta=N, label=TEXT."""
    parts = [p.strip() for p in spec.split(",")]
    rng = parts[0].replace("-", ":") if parts[0].count(":") == 1 or "-" in parts[0] else parts[0]
    a, b = rng.split(":")
    r = Revision(int(a), int(b))
    flags = parts[1:]
    if "video" in flags and "audio" not in flags:
        r.audio = False
    if "audio" in flags and "video" not in flags:
        r.video = False
    for f in flags:
        if "=" in f:
            k, v = f.split("=", 1)
            if k == "hb":
                r.handles_before = int(v)
            elif k == "ha":
                r.handles_after = int(v)
            elif k == "delta":
                r.delta = int(v)
            elif k == "label":
                r.label = v
    return r


def _make_source(cfg: dict, job=None):
    t = cfg.get("type", "resolve")
    if t == "synthetic":
        tl = SynthTimeline.from_dict(cfg["timeline"]) if "timeline" in cfg else SynthTimeline.load(cfg["path"])
        return SyntheticRenderSource(tl), tl.start_frame, tl.rate, tl.length
    if t == "files":
        fps = parse_rate(cfg["fps"])
        rs = [ManualRender(r["path"], int(r["timeline_start"])) for r in cfg["renders"]]
        src = FileRenderSource(rs, fps)
        length = cfg.get("frames")
        return src, int(cfg.get("timeline_offset", 0)), fps, length
    if t == "resolve":
        from .resolve_bridge import ResolveRenderSource, ResolveSession
        src = ResolveRenderSource(ResolveSession().connect(), job=job)
        info = src.info
        return src, info.start_frame, src.rate, info.end_frame - info.start_frame
    raise SystemExit(f"unknown source type {t}")


def _source_from_args(args) -> dict:
    s = getattr(args, "source", None) or "resolve"
    if s.startswith("synthetic:"):
        return {"type": "synthetic", "path": s.split(":", 1)[1]}
    if s == "files":
        renders = []
        for r in args.render or []:
            path, _, frame = r.rpartition("@")
            renders.append({"path": path, "timeline_start": int(frame)})
        return {"type": "files", "renders": renders, "fps": args.fps or "", "timeline_offset": args.timeline_offset or 0}
    return {"type": "resolve"}


def _emitter(args) -> Emitter:
    return Emitter(json_mode=getattr(args, "json", False), quiet=getattr(args, "quiet", False))


def _install_signals(cancel: CancelToken):
    def handler(signum, frame):
        cancel.cancel("cancelled by user" if signum == signal.SIGINT else f"terminated (signal {signum})")
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def _print(args, obj) -> None:
    if getattr(args, "json", False):
        sys.stdout.write(jsonutil.dumps({"type": "result", **obj}) + "\n")
    else:
        print(jsonutil.dumps(obj, indent=2))


# ---------------------------------------------------------------------------
def cmd_doctor(args) -> int:
    from .numeric import HAVE_NUMPY
    from .resolve_bridge import locate_scripting
    vi = version_info()
    enc = encoders()
    checks = []

    def add(name, ok, detail, required=True):
        checks.append({"name": name, "ok": bool(ok), "detail": detail, "required": required})

    add("python", sys.version_info >= (3, 9), sys.version.split()[0])
    add("numpy", HAVE_NUMPY, "fast numeric verification" if HAVE_NUMPY else
        "not installed - verification falls back to slower pure-Python PSNR", required=False)
    add("ffmpeg", "path" in vi.get("ffmpeg", {}), json.dumps(vi.get("ffmpeg")))
    add("ffprobe", "path" in vi.get("ffprobe", {}), json.dumps(vi.get("ffprobe")))
    add("libx264", enc.get("libx264"), "required for patch segments")
    add("aac encoder", enc.get("aac") or enc.get("aac_at"),
        "aac_at (AudioToolbox)" if enc.get("aac_at") else "FFmpeg native aac")
    add("prores", enc.get("prores_ks"), "intermediate for synthetic/self tests", required=False)
    add("videotoolbox", enc.get("h264_videotoolbox"), "not used for patch segments (see technical report)",
        required=False)
    loc = locate_scripting()
    add("resolve scripting module", loc["module_present"], loc["module_dir"], required=False)
    add("resolve fusionscript library", loc["lib_present"], loc["lib"], required=False)
    home = app_support_dir()
    os.makedirs(home, exist_ok=True)
    import shutil
    free = shutil.disk_usage(home).free
    add("work disk space", free > 5e9, f"{free / 1e9:.1f} GB free in {home}")
    rs = None
    if not args.no_resolve:
        from .resolve_bridge import status
        rs = status(timeout=2.0)
        add("resolve connection", rs.get("connected"), rs.get("error") or
            f"{rs.get('version')} - {rs.get('timeline', {}).get('project')} / {rs.get('timeline', {}).get('timeline')}",
            required=False)
    ok = all(c["ok"] for c in checks if c["required"])
    _print(args, {"engine_version": __version__, "build": BUILD_KIND, "platform": platform.platform(),
                  "machine": platform.machine(), "ok": ok, "checks": checks, "resolve": rs, "home": home})
    return 0 if ok else 1


def cmd_probe(args) -> int:
    m = analyze_master(args.master)
    out = m.summary()
    if args.gop_map:
        out["gop_map"] = gop_map(m.video)
        out["frame_types"] = "".join({"IDR": "K", "I": "I", "P": "P", "B": "B"}.get(t, "?")
                                     for t in m.video.frame_type_display())
    if args.fingerprint:
        out["sha256"] = file_sha256(args.master)
    _print(args, {"probe": out})
    return 0


def _revisions_from_request(req: dict, offset: int) -> List[Revision]:
    revs = []
    units = req.get("revision_units", "master")
    for r in req.get("revisions", []):
        rv = Revision.from_dict(r)
        if units == "timeline":
            rv.start -= offset
            rv.end -= offset
        revs.append(rv)
    return revs


def _opts_from_request(req: dict, offset: int):
    from .exporter import ExportOptions
    from .verify import Thresholds
    th = Thresholds(**req.get("thresholds", {}))
    return ExportOptions(mode=req.get("mode", "verified"), strict=bool(req.get("strict", False)),
                         timeline_offset=offset, audio_strategy=req.get("audio", "auto"),
                         quality=req.get("quality", "high"), preset=req.get("preset", "slow"),
                         threads=int(req.get("threads", 0)), guard_frames=int(req.get("guard_frames", 6)),
                         keep_temp=bool(req.get("keep_temp", False)), faststart=req.get("faststart"),
                         aac_encoder=req.get("aac_encoder"), job_root=req.get("job_root"),
                         cache_dir=req.get("cache_dir"), project_root=req.get("project_root"), thresholds=th)


def _request_from_args(args) -> dict:
    if getattr(args, "request", None):
        with open(args.request) as f:
            return json.load(f)
    req = {"master": getattr(args, "master", None), "output": getattr(args, "output", None),
           "mode": "fast" if getattr(args, "fast", False) else "verified", "strict": getattr(args, "strict", False),
           "audio": getattr(args, "audio", "auto"), "quality": getattr(args, "quality", "high"),
           "preset": getattr(args, "preset", "slow"), "threads": getattr(args, "threads", 0),
           "guard_frames": getattr(args, "guard", 6), "keep_temp": getattr(args, "keep_temp", False),
           "revisions": [r.__dict__ for r in (_parse_rev(s) for s in (getattr(args, "rev", None) or []))],
           "source": _source_from_args(args)}
    if getattr(args, "timeline_offset", None) is not None:
        req["timeline_offset"] = args.timeline_offset
    if getattr(args, "master_offset", None):
        req["master_offset"] = args.master_offset
    return req


def cmd_plan(args) -> int:
    from .exporter import Exporter
    req = _request_from_args(args)
    offset = int(req.get("timeline_offset") or 0) + int(req.get("master_offset", 0))
    opts = _opts_from_request(req, offset)
    revs = _revisions_from_request(req, offset)
    res = Exporter(_emitter(args)).plan_only(req["master"], revs, opts)
    _print(args, res)
    return 0


def cmd_export(args) -> int:
    from .exporter import ExportError, Exporter
    em = _emitter(args)
    cancel = CancelToken()
    _install_signals(cancel)
    req = _request_from_args(args)
    if not req.get("master") or not req.get("output"):
        em.error("master and output are required", "usage")
        return 2
    em.start_stats()
    try:
        source, tl_start, rate, _ = _make_source(req.get("source", {"type": "resolve"}))
        offset = req.get("timeline_offset")
        offset = int(tl_start if offset is None else offset) + int(req.get("master_offset", 0))
        if hasattr(source, "check_timeline"):
            m = analyze_master(req["master"], run_ffprobe=False)
            problems = source.check_timeline(m.video.fps, m.video.width, m.video.height)
            if problems:
                em.error("timeline does not match master: " + "; ".join(problems), "timeline_mismatch")
                return 1
        opts = _opts_from_request(req, offset)
        revs = _revisions_from_request(req, offset)
        Exporter(em, cancel).smart_export(req["master"], req["output"], revs, source, opts)
        return 0
    except Cancelled:
        return 130
    except ExportError as e:
        return 3 if e.code == "verification_failed" else 1
    except Exception as e:  # already reported for export errors
        if not isinstance(e, (PlanError,)):
            em.error(str(e), getattr(e, "code", "error"))
        return 1
    finally:
        em.close()


def cmd_full(args, kind: str) -> int:
    from .exporter import ExportError, Exporter
    em = _emitter(args)
    cancel = CancelToken()
    _install_signals(cancel)
    em.start_stats()
    req = _request_from_args(args) if args.request else {
        "output": args.output, "source": _source_from_args(args), "reference": args.reference,
        "preset": args.preset, "gop": args.gop, "gop_seconds": getattr(args, "gop_seconds", None),
        "all_intra": getattr(args, "all_intra", False), "crf": args.crf, "resolve_preset": getattr(args, "resolve_preset", None)}
    try:
        source, tl_start, rate, length = _make_source(req["source"])
        if req.get("frames"):
            length = int(req["frames"])
        if length is None:
            em.error("timeline length unknown; pass --frames", "usage")
            return 2
        opts = _opts_from_request(req, tl_start)
        gop = req.get("gop")
        if req.get("all_intra"):
            gop = 1
        elif req.get("gop_seconds"):
            gop = max(1, int(round(float(req["gop_seconds"]) * float(rate))))
        ex = Exporter(em, cancel)
        if kind == "full-export" and req.get("resolve_preset") and req["source"].get("type") == "resolve":
            return _resolve_preset_export(ex, em, source, req, cancel)
        ex.encode_full(source, req["output"], tl_start, int(length), rate, kind, opts,
                       reference=req.get("reference"), gop=gop, crf=float(req.get("crf") or 16.0))
        return 0
    except Cancelled:
        return 130
    except ExportError as e:
        return 3 if e.code == "verification_failed" else 1
    except Exception as e:
        em.error(str(e), getattr(e, "code", "error"))
        return 1
    finally:
        em.close()


def _resolve_preset_export(ex, em, source, req, cancel) -> int:
    """Safe Full Export rendered entirely by Resolve with the user's delivery preset."""
    from .exporter import _check_output_path
    from .jobs import Job, commit_output, partial_path_for
    out = req["output"]
    _check_output_path(out, req.get("reference"))
    job = Job("full-export-resolve", {"output": out, "preset": req["resolve_preset"]}, req.get("job_root"))
    em.attach_log(job.log_path)
    em.stage("render", f"Resolve renders the full timeline with preset '{req['resolve_preset']}'")
    path = source.session.render_with_preset(req["resolve_preset"], job.tmp_dir, "srx_full",
                                             progress=lambda f: em.progress("render", f), cancel=cancel,
                                             log=em.log, on_job=job.add_resolve_job)
    em.stage("verify", "Verifying full export")
    outm = analyze_master(path)
    checks = [{"name": "parse", "status": "pass", "detail": "output parsed"}]
    if req.get("reference"):
        ref = analyze_master(req["reference"])
        rv, ov = ref.video, outm.video
        for name, a, b in (("frame_rate", rv.fps, ov.fps), ("dimensions", (rv.width, rv.height), (ov.width, ov.height)),
                           ("pix_fmt", rv.pix_fmt, ov.pix_fmt), ("color", {k: ref.color.get(k) for k in ("color_primaries", "color_transfer", "color_space", "color_range")},
                                                                {k: outm.color.get(k) for k in ("color_primaries", "color_transfer", "color_space", "color_range")})):
            checks.append({"name": name, "status": "pass" if a == b else "fail", "detail": f"reference {a}, export {b}"})
    status = "passed" if all(c["status"] == "pass" for c in checks) else "failed"
    final = out
    if status == "passed":
        partial = partial_path_for(out, job.id)
        import shutil
        shutil.move(path, partial)
        commit_output(partial, out)
    job.finish("succeeded" if status == "passed" else "failed")
    em.result({"status": "succeeded" if status == "passed" else "failed", "verification": status,
               "output": os.path.abspath(final), "checks": checks, "job": job.id})
    return 0 if status == "passed" else 3


def cmd_resolve(args) -> int:
    from .resolve_bridge import ResolveSession, revision_ranges_from_resolve, status
    if args.action == "status":
        _print(args, {"resolve": status(timeout=args.timeout)})
        return 0
    s = ResolveSession().connect(args.timeout)
    info = s.timeline_info()
    if args.action == "ranges":
        ranges = revision_ranges_from_resolve(info, args.marker_color)
        rate = parse_rate(info.fps)
        for r in ranges:
            r["start_tc"] = frames_to_tc(r["start"], rate, info.drop_frame)
            r["end_tc_inclusive"] = frames_to_tc(r["end"] - 1, rate, info.drop_frame)
            r["master_start"] = r["start"] - info.start_frame
            r["master_end"] = r["end"] - info.start_frame
        edges = s.edit_points_near([r["start"] for r in ranges] + [r["end"] for r in ranges]) if ranges else []
        _print(args, {"timeline": info.to_dict(), "ranges": ranges, "nearby_edit_points": edges})
        return 0
    if args.action == "alignment":
        return _check_alignment(args, s, info)
    return 2


def _check_alignment(args, session, info) -> int:
    """Render a short probe range and find which master frame offset matches it.

    This verifies the master <-> timeline relationship (wrong master, timeline
    moved, different start offset) before any patch is attempted.
    """
    import hashlib
    from .assemble import extract_video_clip
    from .encoder import input_conversion_filter, derive_settings
    from .ffmpeg import FrameReader
    from .numeric import plane_sse, psnr_from_sse
    from .plan import RenderRequest
    from .resolve_bridge import ResolveRenderSource
    from .jobs import Job
    m = analyze_master(args.master)
    v = m.video
    src = ResolveRenderSource(session)
    probs = src.check_timeline(v.fps, v.width, v.height)
    n = v.frame_count
    center = args.frame if args.frame is not None else n // 2
    span = 8
    lo = max(0, center - span)
    hi = min(n, center + span)
    job = Job("alignment", {"master": args.master})
    req = RenderRequest(info.start_frame + lo, info.start_frame + hi, True, False, "alignment")
    clip = src.render(req, job.tmp_dir)
    s = derive_settings(v, [], [])
    conv = input_conversion_filter(clip.pix_fmt, clip.color_range, s, v)
    rf = FrameReader(clip.path, v.pix_fmt, v.width, v.height, vf=",".join(["setpts=PTS-STARTPTS", *conv]))
    rframes = []
    while True:
        f = rf.read()
        if f is None:
            break
        rframes.append(f)
    rf.finish()
    a = v.prev_resume(max(0, lo - 3))
    import bisect
    i = bisect.bisect_left(v.cut_points, min(n, hi + 3))
    b = v.cut_points[i] if i < len(v.cut_points) else n
    clipm = job.tmp("master_probe.mp4")
    extract_video_clip(m, a, b, clipm)
    mr = FrameReader(clipm, v.pix_fmt, v.width, v.height)
    mframes = []
    while True:
        f = mr.read()
        if f is None:
            break
        mframes.append(f)
    mr.finish()
    w, h = v.width, v.height
    peak = (1 << v.active_sps().bit_depth_luma) - 1
    scores = {}
    for shift in range(-3, 4):
        vals = []
        for k, rfm in enumerate(rframes):
            mi = lo + k + shift - a
            if 0 <= mi < len(mframes):
                sse, cnt = plane_sse(rfm, mframes[mi], 0, w, h, 1 if v.active_sps().bit_depth_luma == 8 else 2)
                vals.append(psnr_from_sse(sse, cnt, peak))
        if vals:
            scores[shift] = sum(vals) / len(vals)
    best = max(scores, key=lambda k: scores[k]) if scores else None
    ok = best == 0 and scores.get(0, 0) >= 30.0 and not probs
    job.finish("succeeded")
    _print(args, {"aligned": ok, "best_offset": best, "psnr_by_offset": scores, "problems": probs,
                  "probe_frames": [lo, hi], "timeline_start_frame": info.start_frame})
    return 0 if ok else 1


def cmd_jobs(args) -> int:
    if args.action == "list":
        _print(args, {"jobs": list_jobs()})
    else:
        rec = recover_jobs()
        if rec and not args.no_resolve:
            try:
                from .resolve_bridge import ResolveSession
                s = ResolveSession().connect(2.0)
                for r in rec:
                    r["resolve_jobs_deleted"] = s.cleanup_jobs(r.get("resolve_render_jobs", []))
            except Exception as e:
                for r in rec:
                    r["resolve_cleanup"] = f"not possible: {e}"
        _print(args, {"recovered": rec})
    return 0


def cmd_project(args) -> int:
    store = ProjectStore()
    fp = file_sha256(args.file)
    if args.action == "status":
        _print(args, {"fingerprint": fp, "project": store.find(fp)})
    else:
        _print(args, {"project": store.approve(fp)})
    return 0


def cmd_frame(args) -> int:
    m = analyze_master(args.input, run_ffprobe=False) if args.exact else None
    fps = m.video.fps if m else Fraction(json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "json",
         args.input], capture_output=True, text=True).stdout)["streams"][0]["r_frame_rate"])
    t = max(0.0, (args.index - 0.5) / float(fps))
    vf = f"scale=-2:{args.height}" if args.height else "null"
    r = subprocess.run([ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.6f}", "-i", args.input, "-frames:v", "1",
                        "-vf", vf, args.output], capture_output=True, text=True)
    if r.returncode != 0:
        _print(args, {"error": r.stderr[-500:]})
        return 1
    _print(args, {"frame": args.index, "output": args.output})
    return 0


def cmd_filmstrip(args) -> int:
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", args.input],
                           capture_output=True, text=True)
    dur = float(json.loads(probe.stdout)["format"]["duration"])
    rate = max(args.tiles / max(dur, 0.01), 1e-3)
    r = subprocess.run([ffmpeg(), "-v", "error", "-y", "-skip_frame", "nokey", "-i", args.input, "-an",
                        "-vf", f"fps={rate:.6f},scale=-2:{args.height},tile={args.tiles}x1", "-frames:v", "1",
                        args.output], capture_output=True, text=True)
    if r.returncode != 0:
        _print(args, {"error": r.stderr[-500:]})
        return 1
    _print(args, {"output": args.output, "tiles": args.tiles})
    return 0


def cmd_synth(args) -> int:
    tl = SynthTimeline.load(args.spec)
    tl.render_master(args.output, gop=args.gop, bframes=args.bframes, profile=args.profile, crf=args.crf,
                     open_gop=args.open_gop)
    _print(args, {"output": args.output})
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="srx", description="Smart Revision Exporter engine " + __version__)
    p.add_argument("--version", action="version", version=f"srx {__version__} ({BUILD_KIND})")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--json", action="store_true", help="JSON-lines output")
        sp.add_argument("--quiet", action="store_true")

    d = sub.add_parser("doctor", help="check dependencies and Resolve connection")
    common(d)
    d.add_argument("--no-resolve", action="store_true")
    d.set_defaults(func=cmd_doctor)

    pr = sub.add_parser("probe", help="analyse a master file")
    common(pr)
    pr.add_argument("master")
    pr.add_argument("--gop-map", action="store_true")
    pr.add_argument("--fingerprint", action="store_true")
    pr.set_defaults(func=cmd_probe)

    def export_args(sp, needs_master=True):
        common(sp)
        if needs_master:
            sp.add_argument("master", nargs="?")
        sp.add_argument("-o", "--output")
        sp.add_argument("--request", help="JSON request file (used by the app)")
        sp.add_argument("--rev", action="append", help="START:END[,video|audio,hb=N,ha=N,delta=N,label=X] "
                                                         "master frames, END exclusive")
        sp.add_argument("--fast", action="store_true", help="Fast Patch (verify splice neighbourhoods only)")
        sp.add_argument("--strict", action="store_true", help="refuse to re-encode any unchanged frame")
        sp.add_argument("--audio", default="auto", choices=["auto", "copy", "splice", "full"])
        sp.add_argument("--quality", default="high", choices=["transparent", "high", "balanced", "match"])
        sp.add_argument("--preset", default="slow")
        sp.add_argument("--threads", type=int, default=0)
        sp.add_argument("--guard", type=int, default=6)
        sp.add_argument("--keep-temp", action="store_true")
        sp.add_argument("--source", default="resolve", help="resolve | synthetic:SPEC.json | files")
        sp.add_argument("--render", action="append", help="files source: PATH@TIMELINE_START_FRAME")
        sp.add_argument("--fps", help="files source: frame rate (e.g. 30000/1001)")
        sp.add_argument("--timeline-offset", type=int, default=None,
                        help="absolute timeline frame of master frame 0 (default: timeline start)")
        sp.add_argument("--master-offset", type=int, default=0,
                        help="master starts this many frames after the timeline start")

    pl = sub.add_parser("plan", help="show what would be rendered/copied")
    export_args(pl)
    pl.set_defaults(func=cmd_plan)

    ex = sub.add_parser("export", help="Smart Export (Fast/Verified Patch)")
    export_args(ex)
    ex.set_defaults(func=cmd_export)

    for name, help_ in (("prepare-master", "render a Revision-Ready Master"), ("full-export", "Safe Full Export")):
        sp = sub.add_parser(name, help=help_)
        export_args(sp, needs_master=False)
        sp.add_argument("--reference", help="existing master to match (codec parameters, colour)")
        sp.add_argument("--gop", type=int)
        sp.add_argument("--gop-seconds", type=float)
        sp.add_argument("--all-intra", action="store_true")
        sp.add_argument("--crf", type=float, default=16.0)
        sp.add_argument("--frames", type=int)
        sp.add_argument("--resolve-preset", help="full-export: render with this Resolve preset")
        sp.set_defaults(func=(lambda a, k=name: cmd_full(a, "revision-ready" if k == "prepare-master" else k)))

    rs = sub.add_parser("resolve", help="DaVinci Resolve helpers")
    common(rs)
    rs.add_argument("action", choices=["status", "ranges", "alignment"])
    rs.add_argument("master", nargs="?")
    rs.add_argument("--marker-color")
    rs.add_argument("--frame", type=int)
    rs.add_argument("--timeout", type=float, default=3.0)
    rs.set_defaults(func=cmd_resolve)

    jb = sub.add_parser("jobs", help="list or recover interrupted jobs")
    common(jb)
    jb.add_argument("action", choices=["list", "recover"])
    jb.add_argument("--no-resolve", action="store_true")
    jb.set_defaults(func=cmd_jobs)

    pj = sub.add_parser("project", help="revision history")
    common(pj)
    pj.add_argument("action", choices=["status", "approve"])
    pj.add_argument("file")
    pj.set_defaults(func=cmd_project)

    fr = sub.add_parser("frame", help="extract one frame as an image")
    common(fr)
    fr.add_argument("input")
    fr.add_argument("--index", type=int, required=True)
    fr.add_argument("-o", "--output", required=True)
    fr.add_argument("--height", type=int, default=0)
    fr.add_argument("--exact", action="store_true")
    fr.set_defaults(func=cmd_frame)

    fs = sub.add_parser("filmstrip", help="keyframe filmstrip image for the timeline")
    common(fs)
    fs.add_argument("input")
    fs.add_argument("-o", "--output", required=True)
    fs.add_argument("--tiles", type=int, default=48)
    fs.add_argument("--height", type=int, default=54)
    fs.set_defaults(func=cmd_filmstrip)

    sy = sub.add_parser("synth", help="render a synthetic test master")
    common(sy)
    sy.add_argument("spec")
    sy.add_argument("-o", "--output", required=True)
    sy.add_argument("--gop", type=int, default=250)
    sy.add_argument("--bframes", type=int, default=3)
    sy.add_argument("--profile", default="high")
    sy.add_argument("--crf", type=int, default=20)
    sy.add_argument("--open-gop", action="store_true")
    sy.set_defaults(func=cmd_synth)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    try:
        return args.func(args)
    except (AnalysisError, PlanError, ToolError, ValueError, FileNotFoundError) as e:
        if getattr(args, "json", False):
            sys.stdout.write(json.dumps({"type": "error", "message": str(e), "code": type(e).__name__}) + "\n")
        else:
            sys.stderr.write(f"error: {e}\n")
        return 1
    except Exception as e:
        code = getattr(e, "code", type(e).__name__)
        if getattr(args, "json", False):
            sys.stdout.write(json.dumps({"type": "error", "message": str(e), "code": code}) + "\n")
        else:
            sys.stderr.write(f"error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
