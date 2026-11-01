"""Export orchestration for the four modes.

* Fast Patch            - selective patch, verification of splice neighbourhoods
* Verified Patch        - selective patch, full-decode per-frame verification
* Revision-Ready Master - one-time full render encoded with short closed GOPs
                          (or all-intra) so future patches touch fewer frames
* Safe Full Export      - verified full render (fallback when patching cannot
                          satisfy the requirements)

The original master is opened read-only and never modified.  Outputs are
written to a hidden partial file next to the destination and moved into place
only after verification passes; existing files are never overwritten.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import time
import traceback
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional

from . import __version__, jsonutil
from .assemble import AssembleError, assemble_video, write_output
from .audio import (AudioError, build_full_track, build_spliced_track, choose_encoder, copy_track,
                    encode_full_track, load_render_audio, master_bitrate, splice_track)
from .encoder import (EncodeError, cfr_output_args, derive_settings, encode_segment, input_conversion_filter,
                      retime_filters, validate_patch, x264_param_string)
from .events import Emitter
from .ffmpeg import CancelToken, Cancelled, FrameReader, ToolError, ffmpeg, passthrough_args, run
from .jobs import Job, ProjectStore, app_support_dir, check_disk_space, commit_output, partial_path_for
from .media import AnalysisError, MasterAnalysis, analyze_master, file_sha256
from .mp4 import Mp4Error
from .plan import Plan, PlanError, RenderRequest, Revision, build_plan
from .render import RenderedClip, RenderError, RenderSource
from .report import write_markdown_report
from .verify import Thresholds, Verifier


class ExportError(RuntimeError):
    def __init__(self, message: str, code: str = "export_failed", details: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass
class ExportOptions:
    mode: str = "verified"            # fast | verified
    strict: bool = False
    timeline_offset: int = 0
    audio_strategy: str = "auto"
    quality: str = "high"
    preset: str = "slow"
    threads: int = 0
    guard_frames: int = 6
    keep_temp: bool = False
    faststart: Optional[bool] = None
    aac_encoder: Optional[str] = None
    job_root: Optional[str] = None
    cache_dir: Optional[str] = None
    project_root: Optional[str] = None
    thresholds: Thresholds = field(default_factory=Thresholds)


def _check_output_path(output: str, master: Optional[str] = None) -> None:
    out = os.path.abspath(output)
    if os.path.exists(out):
        raise ExportError(f"output already exists: {out}. Choose a new file name "
                          f"(existing files are never overwritten).", "output_exists")
    if master and os.path.exists(master) and os.path.realpath(master) == os.path.realpath(out):
        raise ExportError("output path is the master file", "output_is_master")
    d = os.path.dirname(out) or "."
    if not os.path.isdir(d):
        raise ExportError(f"output folder does not exist: {d}", "output_dir_missing")
    if not os.access(d, os.W_OK):
        raise ExportError(f"output folder is not writable: {d}", "output_dir_readonly")
    if os.path.splitext(out)[1].lower() not in (".mp4", ".m4v", ".mov"):
        raise ExportError("output must be an .mp4/.m4v/.mov file", "bad_extension")


def _used_parameter_ids(master: MasterAnalysis, plan: Plan):
    v = master.video
    used_pps = set()
    for seg in plan.segments:
        if seg.kind == "copy":
            for j in range(seg.master_start, seg.master_end):
                used_pps.add(v.pps_id[j])
    pmap = {p.pps_id: p for p in v.pps}
    used_sps = {pmap[p].sps_id for p in used_pps if p in pmap}
    return sorted(used_sps), sorted(used_pps)


def _local_bitrate_kbps(master: MasterAnalysis, seg) -> int:
    v = master.video
    t = v.track
    total = sum(t.sizes[j] for j in range(seg.master_start, seg.master_end))
    secs = (seg.master_end - seg.master_start) / float(v.fps)
    return int(total * 8 / max(secs, 1e-6) / 1000)


def _clip_for(renders: List[RenderedClip], lo: int, hi: int, video: bool) -> Optional[RenderedClip]:
    for c in renders:
        if c.timeline_start <= lo and c.timeline_end >= hi and (c.has_video or not video):
            return c
    return None


class Exporter:
    def __init__(self, emitter: Emitter, cancel: Optional[CancelToken] = None):
        self.em = emitter
        self.cancel = cancel or CancelToken()
        self.em.cancel = self.cancel

    # ------------------------------------------------------------------
    def smart_export(self, master_path: str, output_path: str, revisions: List[Revision],
                     source: RenderSource, opts: ExportOptions) -> dict:
        em = self.em
        _check_output_path(output_path, master_path)
        job = Job("smart-export", {"master": os.path.abspath(master_path), "output": os.path.abspath(output_path),
                                   "revisions": [asdict(r) for r in revisions], "mode": opts.mode,
                                   "strict": opts.strict, "source": source.describe()}, opts.job_root)
        em.attach_log(job.log_path)
        em.emit("job", id=job.id, dir=job.dir, version=__version__)
        partial = partial_path_for(output_path, job.id)
        t_all = time.time()
        timings: Dict[str, float] = {}
        try:
            # ---------------- analysis -------------------------------------------
            em.stage("analyze", "Inspecting master")
            t0 = time.time()
            master = analyze_master(master_path, log=em.log)
            em.emit("master", summary=master.summary())
            src_rate = getattr(source, "rate", None)
            if src_rate is not None and src_rate != master.video.fps:
                raise ExportError(f"timeline frame rate {src_rate} differs from the master's "
                                  f"{master.video.fps}: the timeline was changed or this is the wrong master",
                                  "frame_rate_mismatch")
            for w in master.video.warnings:
                em.warn(w)
            em.stage("fingerprint", "Fingerprinting master (SHA-256)")
            fp = file_sha256(master_path, progress=lambda f: em.progress("fingerprint", f),
                             cancel_check=self.cancel.check)
            timings["analyze"] = time.time() - t0
            job.step("analyzed", fingerprint=fp, frames=master.video.frame_count)
            store = ProjectStore(opts.project_root)
            project = store.ensure(master_path, fp)

            # ---------------- plan ------------------------------------------------
            em.stage("plan", "Planning revision patch")
            plan = build_plan(master, revisions, mode=opts.mode, strict=opts.strict,
                              timeline_offset=opts.timeline_offset, audio_strategy=opts.audio_strategy,
                              guard_frames=opts.guard_frames)
            em.emit("plan", plan=plan.to_dict())
            for w in plan.warnings:
                em.warn(w)
            with open(os.path.join(job.dir, "plan.json"), "w") as f:
                jsonutil.dump(plan.to_dict(), f, indent=2)
            v = master.video
            px = v.width * v.height
            need = master.file_size * 1.2 + sum(r.frames for r in plan.renders) * px * 0.8 + 50e6
            msg = check_disk_space(partial, int(master.file_size * 1.2)) or check_disk_space(job.dir, int(need))
            if msg:
                raise ExportError(msg, "disk_space")

            # ---------------- render ----------------------------------------------
            em.stage("render", f"Rendering {plan.stats['rendered_video_frames']} frames in "
                               f"{len(plan.renders)} job(s) via {source.name}")
            t0 = time.time()
            renders: List[RenderedClip] = []
            render_dir = job.tmp("renders")
            os.makedirs(render_dir, exist_ok=True)
            for ri, req in enumerate(plan.renders):
                self.cancel.check()

                def _rp(f, ri=ri):
                    em.progress("render", (ri + f) / len(plan.renders),
                                f"render {ri + 1}/{len(plan.renders)}")
                clip = source.render(req, render_dir, cancel=self.cancel, progress=_rp, log=em.log)
                renders.append(clip)
                job.step("rendered", request=asdict(req), clip=clip.to_dict())
            em.progress("render", 1.0)
            timings["render"] = time.time() - t0

            # ---------------- encode video segments --------------------------------
            em.stage("encode", "Encoding revised segments (libx264, matched to master)")
            t0 = time.time()
            used_sps, used_pps = _used_parameter_ids(master, plan)
            patches = {}
            patch_sources = {}
            sources = [master.path]
            conv_filters: List[str] = []
            settings = None
            rsegs = [(i, s) for i, s in enumerate(plan.segments) if s.kind == "render" and s.out_len > 0]
            for n_done, (si, seg) in enumerate(rsegs):
                self.cancel.check()
                clip = _clip_for(renders, seg.timeline_start, seg.timeline_end, True)
                if clip is None:
                    raise ExportError("internal error: no render covers segment", "internal")
                if (clip.width, clip.height) != (v.width, v.height):
                    raise ExportError(f"render is {clip.width}x{clip.height} but master is {v.width}x{v.height}: "
                                      f"timeline resolution or render settings changed", "resolution_mismatch")
                settings = derive_settings(v, used_sps, used_pps, quality=opts.quality, preset=opts.preset,
                                           threads=opts.threads, local_bitrate_kbps=_local_bitrate_kbps(master, seg))
                if n_done == 0:
                    for note in settings.notes:
                        em.warn(note)
                conv_filters = input_conversion_filter(clip.pix_fmt, clip.color_range, settings, v)
                out = job.tmp(f"patch_{si}.mp4")
                patch = None
                for attempt in range(2):
                    encode_segment(clip.path, clip.timeline_start, seg.timeline_start, seg.timeline_end, settings,
                                   v, out, job.tmp_dir, clip.pix_fmt, clip.color_range, cancel=self.cancel,
                                   log=em.log,
                                   progress=lambda f, n=n_done: em.progress("encode", (n + f) / len(rsegs)))
                    patch = validate_patch(out, v, seg.out_len, settings.sps_id, settings.x264_params)
                    shift = v.cts0 // v.frame_duration
                    if patch.max_delay > shift and attempt == 0:
                        em.warn("patch B-frame delay exceeds master composition offset; re-encoding without B-frames")
                        settings.x264_params["bframes"] = "0"
                        settings.x264_params.pop("b-pyramid", None)
                        os.unlink(out)
                        continue
                    break
                bad = [c for c in patch.compatibility if not c["ok"] and c["severity"] == "error"]
                warn = [c for c in patch.compatibility if not c["ok"] and c["severity"] != "error"]
                for c in warn:
                    em.warn(f"patch stream differs from master in {c['field']}: {c['master']} vs {c['patch']}")
                if bad:
                    raise ExportError("patch bitstream is not compatible with the master: " +
                                      "; ".join(f"{c['field']} master={c['master']} patch={c['patch']}" for c in bad),
                                      "incompatible_patch", {"compatibility": patch.compatibility})
                patches[si] = patch
                patch_sources[si] = len(sources)
                sources.append(out)
                job.step("encoded", segment=si, frames=patch.frame_count, sps_id=settings.sps_id)
            em.progress("encode", 1.0)
            timings["encode"] = time.time() - t0

            # ---------------- audio -------------------------------------------------
            em.stage("audio", "Processing audio")
            t0 = time.time()
            audio_tracks = {}
            audio_results: Dict[int, dict] = {}
            enc_name = None
            for ap in plan.audio:
                self.cancel.check()
                a = master.audio[ap.index]
                if ap.strategy == "copy":
                    audio_tracks[ap.index] = copy_track(a.track, 0)
                    continue
                enc_name = enc_name or choose_encoder(opts.aac_encoder)
                br = master_bitrate(a)
                if ap.strategy == "splice":
                    results = []
                    loaded = {}
                    sres = []
                    for sp in ap.splices:
                        F, P = a.frame_size, a.priming
                        lo_f = opts.timeline_offset + max(0, math.floor(Fraction(max(0, sp.packet_start * F - P - 6 * F)) * v.fps / a.sample_rate))
                        hi_f = opts.timeline_offset + min(plan.output_frames, math.ceil(Fraction(sp.packet_end * F - P + 6 * F) * v.fps / a.sample_rate))
                        clip = _clip_for(renders, lo_f, hi_f, False)
                        if clip is None:
                            raise ExportError("internal error: no render covers audio splice", "internal")
                        if ap.index >= len(clip.audio_streams):
                            raise ExportError(f"render has no audio stream {ap.index}", "render_audio_missing")
                        ast = clip.audio_streams[ap.index]
                        if ast["channels"] != a.channels:
                            raise ExportError(f"render audio has {ast['channels']} channels, master has {a.channels}",
                                              "audio_layout_mismatch")
                        if clip.path not in loaded:
                            loaded[clip.path] = load_render_audio(clip.path, ap.index, a.channels, a.sample_rate,
                                                                  clip.timeline_start)
                        ra = loaded[clip.path]
                        F = a.frame_size
                        wins = [(max(0, sp.sample_start - 6 * F), max(0, sp.sample_start - F)),
                                (sp.sample_end + F, min(a.presented_samples, sp.sample_end + 6 * F))]
                        wins = [w for w in wins if w[1] - w[0] >= 1024]
                        res = splice_track(master.path, a, sp.packet_start, sp.packet_end, ra, opts.timeline_offset,
                                           v.fps, wins, job.tmp_dir, enc_name, br, cancel=self.cancel, log=em.log)
                        if res.alignment.get("measured"):
                            em.log(f"audio splice {sp.packet_start}-{sp.packet_end}: render offset "
                                   f"{res.alignment['offset']} samples (lag {res.alignment['lags']})")
                        results.append(res)
                        sres.append({"render_audio": ra, "alignment": res.alignment,
                                     "packets": [sp.packet_start, sp.packet_end]})
                        if res.encoded_path not in sources:
                            sources.append(res.encoded_path)
                    idx = {p: i for i, p in enumerate(sources)}
                    audio_tracks[ap.index] = build_spliced_track(a, results, 0, idx)
                    audio_results[ap.index] = {"splices": sres, "encoder": enc_name}
                else:
                    off = opts.timeline_offset
                    clip = _clip_for(renders, off, off + plan.output_frames, False)
                    if clip is None:
                        raise ExportError("internal error: no full audio render", "internal")
                    if ap.index >= len(clip.audio_streams):
                        raise ExportError(f"render has no audio stream {ap.index}", "render_audio_missing")
                    expected = a.presented_samples
                    if plan.output_frames != plan.master_frames:
                        expected = int(Fraction(plan.output_frames) * a.sample_rate / v.fps)
                    res = encode_full_track(a, clip.path, ap.index, job.tmp_dir, enc_name, br, expected,
                                            cancel=self.cancel, log=em.log)
                    sources.append(res.encoded_path)
                    audio_tracks[ap.index] = build_full_track(a, res, len(sources) - 1, master.movie.timescale)
                    audio_results[ap.index] = {"encoder": enc_name, "delay": res.encoder_delay}
                job.step("audio", track=ap.index, strategy=ap.strategy)
            timings["audio"] = time.time() - t0

            # ---------------- assemble ----------------------------------------------
            em.stage("assemble", "Writing patched file (stream copy of unchanged packets)")
            t0 = time.time()
            va = assemble_video(master, plan, patches, patch_sources, 0)
            others = {t.track_id: copy_track(t, 0) for t in master.other_tracks}
            job.set(partial_output=partial)
            write_output(master, va.track, audio_tracks, others, sources, partial, faststart=opts.faststart,
                         progress=lambda f: em.progress("assemble", f), cancel_check=self.cancel.check)
            timings["assemble"] = time.time() - t0
            job.step("assembled", partial=partial, parameter_sets=va.parameter_sets)

            # ---------------- verify -------------------------------------------------
            level = "full" if opts.mode == "verified" else "fast"
            em.stage("verify", "Verifying output (" + ("full decode, every frame" if level == "full"
                                                       else "splice neighbourhoods only") + ")")
            t0 = time.time()
            cache_dir = opts.cache_dir or os.path.join(app_support_dir(), "cache")
            ver = Verifier(master, plan, partial, renders, conv_filters, job.tmp_dir, level=level,
                           cache_dir=cache_dir, master_fingerprint=fp, thresholds=opts.thresholds,
                           cancel=self.cancel, progress=lambda st, f: em.progress("verify", f), log=em.log,
                           audio_results=audio_results)
            report = ver.run()
            timings["verify"] = time.time() - t0
            rep = report.to_dict()
            rep["timings_s"] = {k: round(x, 2) for k, x in timings.items()}
            rep["plan_stats"] = plan.stats
            rep["encoding"] = {"video": settings.to_dict() if settings else None,
                               "x264_params": x264_param_string(settings.x264_params) if settings else None,
                               "audio_encoder": enc_name,
                               "parameter_sets": va.parameter_sets,
                               "patch_compatibility": {str(k): p.compatibility for k, p in patches.items()}}
            rep["master"] = master.summary()
            rep["master_fingerprint"] = fp
            rep["engine_version"] = __version__
            rep["mode"] = opts.mode
            report_json = os.path.join(job.dir, "report.json")
            if report.status != "passed":
                failed_copy = os.path.join(job.dir, "FAILED-" + os.path.basename(output_path))
                shutil.move(partial, failed_copy)
                rep["failed_output_kept_at"] = failed_copy
                with open(report_json, "w") as f:
                    jsonutil.dump(rep, f, indent=2)
                write_markdown_report(rep, os.path.join(job.dir, "report.md"))
                raise ExportError("verification failed: " + "; ".join(rep["failures"])[:1500], "verification_failed",
                                  {"report": report_json})
            commit_output(partial, output_path)
            em.stage("finalize", "Fingerprinting output")
            out_fp = file_sha256(output_path, progress=lambda f: em.progress("finalize", f))
            rep["output"] = {"path": os.path.abspath(output_path), "sha256": out_fp,
                             "size": os.path.getsize(output_path)}
            rep["total_seconds"] = round(time.time() - t_all, 2)
            with open(report_json, "w") as f:
                jsonutil.dump(rep, f, indent=2)
            write_markdown_report(rep, os.path.join(job.dir, "report.md"))
            store.record_cycle(project, master_path, fp, output_path, out_fp, [asdict(r) for r in revisions],
                               report_json, report.status, opts.mode)
            job.finish("succeeded", keep_temp=opts.keep_temp, final_output=os.path.abspath(output_path))
            result = {"status": "succeeded", "verification": report.status, "output": os.path.abspath(output_path),
                      "report": report_json, "report_md": os.path.join(job.dir, "report.md"), "job": job.id,
                      "summary": _summary(rep)}
            em.result(result)
            return result
        except Cancelled as e:
            self._abort(job, partial, source)
            job.finish("cancelled", keep_temp=False)
            em.error(f"cancelled: {e}", "cancelled")
            raise
        except ExportError as e:
            self._abort(job, partial, source)
            job.finish("failed", keep_temp=opts.keep_temp, error=str(e), code=e.code)
            em.error(str(e), e.code, **e.details)
            raise
        except (PlanError, EncodeError, AudioError, RenderError, ToolError, Mp4Error, AnalysisError,
                AssembleError) as e:
            self._abort(job, partial, source)
            code = {PlanError: "plan_error", EncodeError: "encode_error", AudioError: "audio_error",
                    RenderError: "render_error", ToolError: "tool_error", Mp4Error: "corrupt_media",
                    AnalysisError: "analysis_error", AssembleError: "assemble_error"}.get(type(e), "error")
            job.finish("failed", keep_temp=opts.keep_temp, error=str(e), code=code)
            em.error(str(e), code)
            raise ExportError(str(e), code) from e
        except Exception as e:
            self._abort(job, partial, source)
            job.finish("failed", keep_temp=True, error=str(e), traceback=traceback.format_exc())
            em.error(f"unexpected error: {e}", "internal", traceback=traceback.format_exc())
            raise

    def _abort(self, job: Job, partial: str, source: RenderSource) -> None:
        try:
            if os.path.exists(partial):
                os.unlink(partial)
        except OSError:
            pass
        try:
            source.cleanup()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def plan_only(self, master_path: str, revisions: List[Revision], opts: ExportOptions) -> dict:
        master = analyze_master(master_path)
        plan = build_plan(master, revisions, mode=opts.mode, strict=opts.strict,
                          timeline_offset=opts.timeline_offset, audio_strategy=opts.audio_strategy,
                          guard_frames=opts.guard_frames)
        return {"plan": plan.to_dict(), "master": master.summary()}

    # ------------------------------------------------------------------
    def encode_full(self, source: RenderSource, output_path: str, timeline_start: int, frames: int, fps: Fraction,
                    kind: str, opts: ExportOptions, reference: Optional[str] = None, gop: Optional[int] = None,
                    crf: float = 16.0, audio_bitrate: Optional[int] = None) -> dict:
        """Full render + encode.  kind = 'revision-ready' | 'full-export'."""
        em = self.em
        _check_output_path(output_path, reference)
        job = Job(kind, {"output": os.path.abspath(output_path), "frames": frames, "gop": gop,
                         "reference": reference, "source": source.describe()}, opts.job_root)
        em.attach_log(job.log_path)
        em.emit("job", id=job.id, dir=job.dir, version=__version__)
        partial = partial_path_for(output_path, job.id)
        try:
            ref = analyze_master(reference) if reference else None
            em.stage("render", f"Rendering full timeline ({frames} frames)")
            req = RenderRequest(timeline_start, timeline_start + frames, True, True, kind)
            clip = source.render(req, job.tmp_dir, cancel=self.cancel,
                                 progress=lambda f: em.progress("render", f), log=em.log)
            self.cancel.check()
            # x264 parameters
            if ref is not None:
                s = derive_settings(ref.video, [], [], quality="high", preset=opts.preset, threads=opts.threads)
                params = dict(s.x264_params)
                color_args = s.color_args
                profile, level = s.profile, s.level
                pix_fmt = s.pix_fmt
                conv = input_conversion_filter(clip.pix_fmt, clip.color_range, s, ref.video)
            else:
                params = {"colorprim": "bt709", "transfer": "bt709", "colormatrix": "bt709", "range": "tv"}
                color_args = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                              "-color_range", "tv"]
                profile, level, pix_fmt = "high", None, "yuv420p"
                conv = ["format=yuv420p"]
            params.pop("sps-id", None)
            params.pop("repeat-headers", None)
            params.pop("vbv-maxrate", None)
            params.pop("vbv-bufsize", None)
            if kind == "revision-ready":
                g = gop or int(round(float(fps)))
                params.update({"keyint": str(g), "min-keyint": str(g), "scenecut": "0", "open-gop": "0"})
                if g == 1:
                    params.update({"bframes": "0"})
                    params.pop("b-pyramid", None)
                else:
                    params.setdefault("bframes", "3")
                    params.setdefault("b-pyramid", "normal")
            else:
                g = gop or (int(params.get("keyint", 0)) or int(round(float(fps))) * 10)
                params.update({"keyint": str(g), "open-gop": "0"})
            em.stage("encode", "Encoding H.264 " + ("revision-ready master" if kind == "revision-ready" else "delivery"))
            vtmp = job.tmp("video.mp4")
            cmd = [ffmpeg(), "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", clip.path, "-map", "0:v:0",
                   "-an", "-vf", ",".join(retime_filters(f"{fps.numerator}/{fps.denominator}") + conv),
                   *cfr_output_args(f"{fps.numerator}/{fps.denominator}"),
                   "-c:v", "libx264", "-preset", opts.preset, "-crf", str(crf), "-profile:v", profile]
            if level:
                cmd += ["-level", level]
            cmd += [*color_args, "-x264-params", x264_param_string(params), "-progress", "pipe:1", vtmp]

            def _p(d):
                try:
                    em.progress("encode", int(d.get("frame", 0)) / max(1, frames))
                except ValueError:
                    pass
            run(cmd, cancel=self.cancel, log=em.log, progress=_p)
            # audio
            sources = [vtmp]
            from .mp4 import read_movie, OutTrack
            vmov = read_movie(vtmp)
            tracks = [copy_track(vmov.track_by_handler("vide")[0], 0)]
            if clip.has_audio and clip.audio_streams:
                enc = choose_encoder(opts.aac_encoder)
                br = audio_bitrate or (master_bitrate(ref.audio[0]) if ref and ref.audio else 192000)
                atmp = job.tmp("audio.m4a")
                run([ffmpeg(), "-v", "error", "-y", "-nostdin", "-i", clip.path, "-map", "0:a:0", "-vn",
                     "-c:a", enc, "-b:a", str(br), atmp], cancel=self.cancel, log=em.log)
                sources.append(atmp)
                amov = read_movie(atmp)
                tracks.append(copy_track(amov.track_by_handler("soun")[0], 1))
            from .mp4 import write_movie
            em.stage("assemble", "Writing file")
            job.set(partial_output=partial)
            write_movie(partial, sources, vmov, tracks, faststart=True)
            em.stage("verify", "Verifying export")
            out = analyze_master(partial)
            ov = out.video
            rep_checks = []

            def chk(name, ok, detail):
                rep_checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})
            chk("frame_count", ov.frame_count == frames, f"{ov.frame_count} frames (expected {frames})")
            chk("frame_rate", ov.fps == fps, f"{ov.fps}")
            if ref is not None:
                chk("dimensions", (ov.width, ov.height) == (ref.video.width, ref.video.height),
                    f"{ov.width}x{ov.height}")
                keys = ("color_range", "color_space", "color_transfer", "color_primaries")
                diffs = {k: (ref.color.get(k), out.color.get(k)) for k in keys if ref.color.get(k) != out.color.get(k)}
                chk("color_metadata", not diffs, f"differences: {diffs}" if diffs else "identical to reference")
            if kind == "revision-ready":
                g = int(params["keyint"])
                expected = set(range(0, frames, g))
                ok = expected.issubset(set(ov.resume_points))
                chk("gop_structure", ok, f"IDR resume point every {g} frames; {len(ov.resume_points)} resume points, "
                                         f"{len(ov.cut_points)} clean cut points")
            hashes = 0
            fr = FrameReader(partial, ov.pix_fmt, ov.width, ov.height, cancel=self.cancel)
            while fr.read() is not None:
                hashes += 1
                if hashes % 100 == 0:
                    em.progress("verify", hashes / max(1, frames))
            err = fr.finish()
            chk("decode", hashes == frames and not err.strip(),
                f"full decode produced {hashes} frames" + (f"; errors: {err[-300:]}" if err.strip() else ", no errors"))
            if out.audio and ref is not None and ref.audio:
                ra, oa = ref.audio[0], out.audio[0]
                chk("audio_layout", (ra.sample_rate, ra.channels) == (oa.sample_rate, oa.channels),
                    f"{oa.sample_rate} Hz, {oa.channels} ch")
            status = "passed" if all(c["status"] == "pass" for c in rep_checks) else "failed"
            rep = {"status": status, "kind": kind, "checks": rep_checks, "output_summary": out.summary(),
                   "engine_version": __version__,
                   "tradeoffs": revision_ready_tradeoffs(int(params["keyint"]), fps) if kind == "revision-ready" else None}
            report_json = os.path.join(job.dir, "report.json")
            if status != "passed":
                failed_copy = os.path.join(job.dir, "FAILED-" + os.path.basename(output_path))
                shutil.move(partial, failed_copy)
                with open(report_json, "w") as f:
                    jsonutil.dump(rep, f, indent=2)
                raise ExportError("export verification failed: " +
                                  "; ".join(c["detail"] for c in rep_checks if c["status"] == "fail"),
                                  "verification_failed", {"report": report_json})
            commit_output(partial, output_path)
            rep["output"] = {"path": os.path.abspath(output_path), "sha256": file_sha256(output_path)}
            with open(report_json, "w") as f:
                jsonutil.dump(rep, f, indent=2)
            write_markdown_report(rep, os.path.join(job.dir, "report.md"))
            job.finish("succeeded", keep_temp=opts.keep_temp, final_output=os.path.abspath(output_path))
            result = {"status": "succeeded", "verification": status, "output": os.path.abspath(output_path),
                      "report": report_json, "report_md": os.path.join(job.dir, "report.md"), "job": job.id}
            em.result(result)
            return result
        except Cancelled:
            self._abort(job, partial, source)
            job.finish("cancelled")
            em.error("cancelled", "cancelled")
            raise
        except ExportError as e:
            self._abort(job, partial, source)
            job.finish("failed", keep_temp=opts.keep_temp, error=str(e))
            em.error(str(e), e.code, **e.details)
            raise
        except Exception as e:
            self._abort(job, partial, source)
            job.finish("failed", keep_temp=True, error=str(e), traceback=traceback.format_exc())
            em.error(f"{e}", "export_failed")
            raise


def revision_ready_tradeoffs(gop: int, fps: Fraction) -> dict:
    secs = gop / float(fps)
    if gop == 1:
        return {"structure": "all-intra H.264 (every frame IDR)",
                "max_reencoded_unchanged_frames_per_revision": 0,
                "pixel_identity": "every frame outside the revision ranges stays pixel-identical",
                "size": "typically 3-6x larger than long-GOP delivery at the same quality",
                "compatibility": "standard High profile H.264; plays everywhere, high bitrate may stress "
                                 "web upload and older hardware"}
    return {"structure": f"closed GOP, IDR every {gop} frames ({secs:.2f} s), no scene-cut keyframes",
            "max_reencoded_unchanged_frames_per_revision": f"up to {gop - 1} after a revision + up to 3 before",
            "pixel_identity": "frames outside the rebuilt GOPs stay pixel-identical",
            "size": f"about {max(2, int(round(12 / max(secs, 0.1))))}% larger than a 10 s GOP master"
            if secs < 10 else "comparable to a normal delivery master",
            "compatibility": "standard High profile H.264 MP4"}


def _summary(rep: dict) -> dict:
    v = rep.get("video", {})
    return {
        "status": rep.get("status"),
        "output_frames": v.get("output_frames"),
        "master_frames": v.get("master_frames"),
        "compared_unchanged": v.get("compared_unchanged"),
        "identical_unchanged": v.get("identical_unchanged"),
        "reencoded_frames": v.get("reencoded_frames"),
        "boundary_frames": v.get("boundary_frames"),
        "rendered_percent": rep.get("plan_stats", {}).get("rendered_percent"),
        "warnings": rep.get("warnings", []),
    }
