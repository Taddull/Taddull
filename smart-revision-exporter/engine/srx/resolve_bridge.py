"""DaVinci Resolve integration through the official scripting API.

Only methods documented in Blackmagic's scripting README (Developer/Scripting/
README.txt shipped with Resolve 18/19) are used:

  scriptapp("Resolve"), Resolve.GetVersion/GetVersionString/GetProductName,
  Resolve.GetProjectManager/OpenPage/GetCurrentPage,
  ProjectManager.GetCurrentProject,
  Project.GetName/GetCurrentTimeline/GetSetting/GetRenderFormats/GetRenderCodecs/
          GetCurrentRenderFormatAndCodec/SetCurrentRenderFormatAndCodec/
          GetCurrentRenderMode/SetCurrentRenderMode/SetRenderSettings/AddRenderJob/
          DeleteRenderJob/StartRendering/IsRenderingInProgress/StopRendering/
          GetRenderJobStatus/GetRenderJobList/GetRenderPresetList/LoadRenderPreset/
          SaveAsNewRenderPreset/DeleteRenderPreset,
  Timeline.GetName/GetStartFrame/GetEndFrame/GetStartTimecode/GetSetting/
           GetMarkers/GetMarkInOut (Resolve 19+, optional)/GetTrackCount/GetItemListInTrack,
  TimelineItem.GetStart/GetEnd/GetName.

Methods that may not exist in the installed version are probed at runtime and
reported by `api_report()`; nothing else is assumed.  Resolve cannot report
which frames changed since the last export, so revision ranges always come from
the user (In/Out marks, range markers or manual entry).

Requirements on the user's Mac: DaVinci Resolve running with a project open and
Preferences > System > General > "External scripting using" = Local.
(Blackmagic restricts external scripting in some free-version releases; the
`files` render source is the documented fallback.)
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional

from .plan import RenderRequest
from .render import RenderError, RenderSource, inspect_clip
from .timecode import frames_to_tc, parse_rate, tc_to_frames

MAC_API = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
MAC_LIB = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
WIN_API = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"
LINUX_API = "/opt/resolve/Developer/Scripting"
LINUX_LIB = "/opt/resolve/libs/Fusion/fusionscript.so"

INTERMEDIATE_CODEC_PREFERENCE = [
    ("ProRes422HQ", "422 HQ"),
    ("ProRes4444", "4444"),
    ("ProRes422", "422"),
    ("DNxHR HQX", "HQX"),
    ("DNxHR444", "444"),
]


class ResolveError(RuntimeError):
    def __init__(self, message: str, code: str = "resolve_error"):
        super().__init__(message)
        self.code = code


def _default_paths() -> Dict[str, str]:
    if sys.platform == "darwin":
        return {"api": MAC_API, "lib": MAC_LIB}
    if sys.platform.startswith("win"):
        return {"api": WIN_API, "lib": r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"}
    return {"api": LINUX_API, "lib": LINUX_LIB}


def locate_scripting() -> dict:
    """Locate the DaVinciResolveScript module without modifying the installation."""
    paths = _default_paths()
    api = os.environ.get("RESOLVE_SCRIPT_API", paths["api"])
    lib = os.environ.get("RESOLVE_SCRIPT_LIB", paths["lib"])
    module_dir = os.path.join(api, "Modules")
    return {
        "api_dir": api,
        "module_dir": module_dir,
        "module_present": os.path.isfile(os.path.join(module_dir, "DaVinciResolveScript.py")),
        "lib": lib,
        "lib_present": os.path.isfile(lib),
        "readme": os.path.join(api, "README.txt"),
        "readme_present": os.path.isfile(os.path.join(api, "README.txt")),
    }


def load_module():
    """Import DaVinciResolveScript (from env/standard location)."""
    if os.environ.get("SRX_RESOLVE_MOCK"):
        from . import resolve_mock
        return resolve_mock
    try:
        return importlib.import_module("DaVinciResolveScript")
    except ImportError:
        pass
    loc = locate_scripting()
    if not loc["module_present"]:
        raise ResolveError("DaVinci Resolve scripting module not found at "
                           f"{loc['module_dir']}. Is DaVinci Resolve installed?", "resolve_not_installed")
    os.environ.setdefault("RESOLVE_SCRIPT_API", loc["api_dir"])
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", loc["lib"])
    if loc["module_dir"] not in sys.path:
        sys.path.append(loc["module_dir"])
    try:
        return importlib.import_module("DaVinciResolveScript")
    except Exception as e:  # module present but fusionscript failed to load
        raise ResolveError(f"cannot load Resolve scripting library ({e}). Check that the Python "
                           f"version is supported by your Resolve release.", "resolve_module_error")


def _call(obj, name: str, *args):
    """Call an API method; returns (ok, value).  ok=False if missing or raised."""
    fn = getattr(obj, name, None)
    if fn is None:
        return False, None
    try:
        return True, fn(*args)
    except Exception as e:  # noqa
        return False, e


@dataclass
class TimelineInfo:
    project: str
    timeline: str
    fps: str
    fps_float: float
    drop_frame: bool
    start_frame: int
    end_frame: int
    start_timecode: str
    width: int
    height: int
    resolve_version: str
    product: str
    mark_in: Optional[int] = None    # absolute frames, inclusive
    mark_out: Optional[int] = None   # absolute frames, inclusive
    markers: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duration_frames"] = self.end_frame - self.start_frame
        return d


class ResolveSession:
    def __init__(self, module=None):
        self.module = module or load_module()
        self.resolve = None
        self._api_report: Dict[str, bool] = {}

    def connect(self, timeout: float = 5.0):
        deadline = time.time() + timeout
        while True:
            try:
                r = self.module.scriptapp("Resolve")
            except Exception as e:
                r = None
                err = e
            if r is not None:
                self.resolve = r
                return self
            if time.time() > deadline:
                raise ResolveError("Could not connect to DaVinci Resolve. Make sure Resolve is running and "
                                   "Preferences > System > General > External scripting using is set to 'Local'.",
                                   "resolve_not_running")
            time.sleep(0.5)

    # ---- objects ---------------------------------------------------------------
    def project(self):
        pm = self.resolve.GetProjectManager()
        p = pm.GetCurrentProject() if pm else None
        if not p:
            raise ResolveError("No project is open in DaVinci Resolve.", "no_project")
        return p

    def timeline(self):
        tl = self.project().GetCurrentTimeline()
        if not tl:
            raise ResolveError("The current project has no active timeline.", "no_timeline")
        return tl

    def version(self) -> str:
        ok, v = _call(self.resolve, "GetVersionString")
        if ok and isinstance(v, str):
            return v
        ok, v = _call(self.resolve, "GetVersion")
        if ok and isinstance(v, (list, tuple)):
            return ".".join(str(x) for x in v[:4])
        return "unknown"

    def api_report(self) -> Dict[str, bool]:
        """Probe which documented methods exist in this Resolve version."""
        p = self.project()
        tl = self.timeline()
        checks = {
            "Resolve.GetVersionString": (self.resolve, "GetVersionString", ()),
            "Resolve.GetProductName": (self.resolve, "GetProductName", ()),
            "Resolve.GetCurrentPage": (self.resolve, "GetCurrentPage", ()),
            "Project.GetRenderFormats": (p, "GetRenderFormats", ()),
            "Project.GetRenderJobList": (p, "GetRenderJobList", ()),
            "Project.GetRenderPresetList": (p, "GetRenderPresetList", ()),
            "Project.GetCurrentRenderFormatAndCodec": (p, "GetCurrentRenderFormatAndCodec", ()),
            "Project.GetCurrentRenderMode": (p, "GetCurrentRenderMode", ()),
            "Project.IsRenderingInProgress": (p, "IsRenderingInProgress", ()),
            "Timeline.GetStartFrame": (tl, "GetStartFrame", ()),
            "Timeline.GetEndFrame": (tl, "GetEndFrame", ()),
            "Timeline.GetStartTimecode": (tl, "GetStartTimecode", ()),
            "Timeline.GetMarkers": (tl, "GetMarkers", ()),
            "Timeline.GetMarkInOut": (tl, "GetMarkInOut", ()),
            "Timeline.GetSetting": (tl, "GetSetting", ("timelineFrameRate",)),
        }
        rep = {}
        for k, (obj, name, args) in checks.items():
            ok, val = _call(obj, name, *args)
            rep[k] = bool(ok and val is not None and not isinstance(val, Exception))
        self._api_report = rep
        return rep

    def _setting(self, tl, p, key):
        ok, v = _call(tl, "GetSetting", key)
        if ok and v not in (None, "") and not isinstance(v, Exception):
            return v
        ok, v = _call(p, "GetSetting", key)
        if ok and v not in (None, "") and not isinstance(v, Exception):
            return v
        return None

    def timeline_info(self) -> TimelineInfo:
        p = self.project()
        tl = self.timeline()
        fps_s = self._setting(tl, p, "timelineFrameRate")
        if fps_s is None:
            raise ResolveError("cannot read the timeline frame rate", "timeline_settings")
        rate = parse_rate(fps_s)
        df = str(self._setting(tl, p, "timelineDropFrameTimecode") or "0") in ("1", "True", "true")
        w = int(self._setting(tl, p, "timelineResolutionWidth") or 0)
        h = int(self._setting(tl, p, "timelineResolutionHeight") or 0)
        start = int(tl.GetStartFrame())
        end = int(tl.GetEndFrame())
        ok, stc = _call(tl, "GetStartTimecode")
        stc = stc if ok and isinstance(stc, str) else frames_to_tc(start, rate, df)
        ok, prod = _call(self.resolve, "GetProductName")
        info = TimelineInfo(project=p.GetName(), timeline=tl.GetName(), fps=f"{rate.numerator}/{rate.denominator}",
                            fps_float=float(rate), drop_frame=df, start_frame=start, end_frame=end,
                            start_timecode=stc, width=w, height=h, resolve_version=self.version(),
                            product=prod if ok and isinstance(prod, str) else "DaVinci Resolve")
        mi, mo = self.mark_in_out(tl, start)
        info.mark_in, info.mark_out = mi, mo
        info.markers = self.markers(tl, start)
        return info

    def mark_in_out(self, tl, start_frame: int):
        """Timeline In/Out (Resolve 19+ GetMarkInOut).  Returns absolute inclusive frames."""
        ok, v = _call(tl, "GetMarkInOut")
        if not ok or not isinstance(v, dict):
            return None, None
        d = v.get("video") or v.get("all") or v
        if not isinstance(d, dict) or "in" not in d or "out" not in d:
            return None, None
        i, o = int(d["in"]), int(d["out"])
        if i < start_frame:  # relative to timeline start
            i += start_frame
            o += start_frame
        return i, o

    def markers(self, tl, start_frame: int) -> List[dict]:
        ok, v = _call(tl, "GetMarkers")
        if not ok or not isinstance(v, dict):
            return []
        out = []
        for frame, m in sorted(v.items(), key=lambda kv: float(kv[0])):
            f = int(float(frame))
            out.append({"frame": start_frame + f, "relative_frame": f, "duration": int(m.get("duration", 1) or 1),
                        "color": m.get("color", ""), "name": m.get("name", ""), "note": m.get("note", "")})
        return out

    def edit_points_near(self, frames: List[int], window: int = 12) -> List[dict]:
        """Clip boundaries within `window` frames of the given absolute frames
        (used to warn about transitions next to a revision edge)."""
        tl = self.timeline()
        hits = []
        for kind in ("video", "audio"):
            ok, n = _call(tl, "GetTrackCount", kind)
            if not ok or not isinstance(n, int):
                continue
            for t in range(1, n + 1):
                ok, items = _call(tl, "GetItemListInTrack", kind, t)
                if not ok or not items:
                    continue
                for it in items:
                    for edge in (it.GetStart(), it.GetEnd()):
                        for f in frames:
                            if abs(int(edge) - f) <= window:
                                hits.append({"track": f"{kind}{t}", "edge": int(edge), "near": f,
                                             "clip": it.GetName()})
        return hits

    # ---- rendering ---------------------------------------------------------------
    def choose_audio_only(self, p) -> dict:
        """Audio-only render target: Wave if offered, else QuickTime with video disabled."""
        formats = p.GetRenderFormats() or {}
        for desc, ext in formats.items():
            if str(ext).lower() == "wav" or "wave" in str(desc).lower():
                codecs = p.GetRenderCodecs(ext) or {}
                codec = next(iter(codecs.values()), "")
                return {"format": ext, "codec": codec, "description": f"{desc} audio"}
        inter = self.choose_intermediate(p)
        inter["description"] += " (video export disabled)"
        return inter

    def choose_intermediate(self, p) -> dict:
        formats = p.GetRenderFormats() or {}
        fmt = None
        for desc, ext in formats.items():
            if str(ext).lower() == "mov" or "quicktime" in str(desc).lower():
                fmt = ext
                break
        if fmt is None:
            raise ResolveError("QuickTime render format not available", "render_format")
        codecs = p.GetRenderCodecs(fmt) or {}
        for name, frag in INTERMEDIATE_CODEC_PREFERENCE:
            for desc, cname in codecs.items():
                if cname == name or (frag in str(desc) and ("ProRes" in str(desc) or "DNx" in str(desc))):
                    return {"format": fmt, "codec": cname, "description": desc}
        raise ResolveError(f"no high-quality intermediate codec available (have: {list(codecs.values())})",
                           "render_codec")

    def render_range(self, start: int, end_inclusive: int, target_dir: str, name: str, video: bool = True,
                     audio: bool = True, progress=None, cancel=None, log=None, on_job=None) -> str:
        """Render absolute timeline frames [start, end_inclusive] to an intermediate .mov."""
        p = self.project()
        tl = self.timeline()
        log = log or (lambda s: None)
        if p.IsRenderingInProgress():
            raise ResolveError("Resolve is already rendering; wait for the render queue to finish", "render_busy")
        tl_start, tl_end = int(tl.GetStartFrame()), int(tl.GetEndFrame())
        # GetEndFrame() is accepted as either inclusive or exclusive end
        if start < tl_start or end_inclusive > tl_end or end_inclusive < start:
            raise ResolveError(f"render range {start}-{end_inclusive} outside timeline {tl_start}-{tl_end}",
                               "invalid_range")
        ok, prev_page = _call(self.resolve, "GetCurrentPage")
        ok_fc, prev_fc = _call(p, "GetCurrentRenderFormatAndCodec")
        ok_rm, prev_mode = _call(p, "GetCurrentRenderMode")
        restore_preset = f"SRX-restore-{int(time.time())}"
        saved, _ = _call(p, "SaveAsNewRenderPreset", restore_preset)
        os.makedirs(target_dir, exist_ok=True)
        job_id = None
        try:
            _call(self.resolve, "OpenPage", "deliver")
            inter = self.choose_intermediate(p) if video else self.choose_audio_only(p)
            if not p.SetCurrentRenderFormatAndCodec(inter["format"], inter["codec"]):
                raise ResolveError(f"cannot select {inter['description']}", "render_codec")
            _call(p, "SetCurrentRenderMode", 1)
            settings = {"SelectAllFrames": False, "MarkIn": int(start), "MarkOut": int(end_inclusive),
                        "TargetDir": target_dir, "CustomName": name, "ExportVideo": bool(video),
                        "ExportAudio": bool(audio)}
            if not p.SetRenderSettings(settings):
                raise ResolveError(f"Resolve rejected render settings {settings}", "render_settings")
            # Linear PCM keeps the patch audio first-generation; ignored if unsupported.
            _call(p, "SetRenderSettings", {"AudioCodec": "lpcm"})
            job_id = p.AddRenderJob()
            if not job_id:
                raise ResolveError("AddRenderJob failed", "render_job")
            if on_job:
                on_job(job_id)
            log(f"Resolve render job {job_id}: frames {start}-{end_inclusive} as {inter['description']}")
            ok, started = _call(p, "StartRendering", [job_id], False)
            if not ok or started is False:
                ok, started = _call(p, "StartRendering", job_id)
            if not ok or started is False:
                raise ResolveError("StartRendering failed", "render_start")
            last = None
            while True:
                if cancel is not None and cancel.cancelled:
                    p.StopRendering()
                    raise ResolveError("render cancelled", "cancelled")
                st = p.GetRenderJobStatus(job_id) or {}
                status = str(st.get("JobStatus", ""))
                pct = st.get("CompletionPercentage")
                if progress and isinstance(pct, (int, float)):
                    progress(float(pct) / 100.0)
                if status != last:
                    log(f"Resolve job {job_id}: {status}")
                    last = status
                if status == "Complete":
                    break
                if status in ("Failed", "Cancelled"):
                    raise ResolveError(f"Resolve render {status.lower()}: {st.get('Error', '')}", "render_failed")
                if not p.IsRenderingInProgress() and status not in ("Rendering", "Ready", "Queued", ""):
                    raise ResolveError(f"Resolve stopped rendering with status '{status}'", "render_failed")
                time.sleep(0.5)
            path = None
            ok, jobs = _call(p, "GetRenderJobList")
            if ok and isinstance(jobs, list):
                for j in jobs:
                    if j.get("JobId") == job_id and j.get("OutputFilename"):
                        path = os.path.join(j.get("TargetDir", target_dir), j["OutputFilename"])
            if not path or not os.path.isfile(path):
                cands = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.startswith(name)]
                if len(cands) != 1:
                    raise ResolveError(f"cannot locate render output for job {job_id} in {target_dir}",
                                       "render_output")
                path = cands[0]
            return path
        finally:
            if job_id:
                _call(p, "DeleteRenderJob", job_id)
            if saved is True:
                _call(p, "LoadRenderPreset", restore_preset)
                _call(p, "DeleteRenderPreset", restore_preset)
            else:
                if ok_fc and isinstance(prev_fc, dict) and prev_fc.get("format"):
                    _call(p, "SetCurrentRenderFormatAndCodec", prev_fc["format"], prev_fc.get("codec", ""))
                if ok_rm and isinstance(prev_mode, int):
                    _call(p, "SetCurrentRenderMode", prev_mode)
            if isinstance(prev_page, str) and prev_page:
                _call(self.resolve, "OpenPage", prev_page)

    def render_with_preset(self, preset: str, target_dir: str, name: str, progress=None, cancel=None,
                           log=None, on_job=None) -> str:
        """Safe Full Export: render the whole timeline with a user's delivery preset."""
        p = self.project()
        presets = p.GetRenderPresetList() or []
        if preset not in presets:
            raise ResolveError(f"render preset '{preset}' not found (available: {presets})", "preset_missing")
        if not p.LoadRenderPreset(preset):
            raise ResolveError(f"cannot load render preset '{preset}'", "preset_load")
        if not p.SetRenderSettings({"SelectAllFrames": True, "TargetDir": target_dir, "CustomName": name}):
            raise ResolveError("Resolve rejected render settings", "render_settings")
        job_id = p.AddRenderJob()
        if not job_id:
            raise ResolveError("AddRenderJob failed", "render_job")
        if on_job:
            on_job(job_id)
        try:
            ok, started = _call(p, "StartRendering", [job_id], False)
            if not ok or started is False:
                _call(p, "StartRendering", job_id)
            while True:
                if cancel is not None and cancel.cancelled:
                    p.StopRendering()
                    raise ResolveError("render cancelled", "cancelled")
                st = p.GetRenderJobStatus(job_id) or {}
                status = str(st.get("JobStatus", ""))
                if progress and isinstance(st.get("CompletionPercentage"), (int, float)):
                    progress(st["CompletionPercentage"] / 100.0)
                if status == "Complete":
                    break
                if status in ("Failed", "Cancelled"):
                    raise ResolveError(f"Resolve render {status.lower()}", "render_failed")
                time.sleep(1.0)
            cands = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.startswith(name)]
            if len(cands) != 1:
                raise ResolveError("cannot locate full render output", "render_output")
            return cands[0]
        finally:
            _call(p, "DeleteRenderJob", job_id)

    def cleanup_jobs(self, job_ids: List[str]) -> List[str]:
        p = self.project()
        removed = []
        for j in job_ids:
            ok, v = _call(p, "DeleteRenderJob", j)
            if ok and v:
                removed.append(j)
        return removed


class ResolveRenderSource(RenderSource):
    name = "resolve"

    def __init__(self, session: Optional[ResolveSession] = None, expect: Optional[dict] = None, job=None):
        self.session = session or ResolveSession().connect()
        self.info = self.session.timeline_info()
        self.expect = expect or {}
        self.job = job
        self.created_jobs: List[str] = []

    @property
    def rate(self) -> Fraction:
        return parse_rate(self.info.fps)

    def check_timeline(self, master_fps: Fraction, width: int, height: int) -> List[str]:
        problems = []
        if self.rate != master_fps:
            problems.append(f"timeline frame rate {self.info.fps} differs from master {master_fps}")
        if self.info.width and (self.info.width, self.info.height) != (width, height):
            problems.append(f"timeline resolution {self.info.width}x{self.info.height} differs from master "
                            f"{width}x{height} (check the render resolution / output scaling)")
        return problems

    def render(self, req: RenderRequest, out_dir: str, cancel=None, progress=None, log=None):
        cur = self.session.timeline_info()
        if (cur.project, cur.timeline) != (self.info.project, self.info.timeline):
            raise RenderError("the active Resolve project/timeline changed during the export")
        name = f"srx_{req.timeline_start}_{req.timeline_end}"
        target = os.path.join(out_dir, name)

        def on_job(jid):
            self.created_jobs.append(jid)
            if self.job is not None:
                self.job.add_resolve_job(jid)
        # Audio-only requests (audio revisions, full-track audio re-encode) never
        # render video: a full-timeline audio render must not cost a video render.
        path = self.session.render_range(req.timeline_start, req.timeline_end - 1, target, name, video=req.video,
                                         audio=req.audio, progress=progress, cancel=cancel, log=log,
                                         on_job=on_job)
        return inspect_clip(path, req.timeline_start, req.frames, self.rate, req.video, self.name)

    def describe(self) -> dict:
        return {"source": self.name, "timeline": self.info.to_dict()}

    def cleanup(self) -> None:
        try:
            self.session.cleanup_jobs(self.created_jobs)
        except Exception:
            pass


def status(timeout: float = 3.0) -> dict:
    """Connection diagnostics for the UI / doctor command."""
    out: Dict[str, Any] = {"scripting": locate_scripting(), "connected": False}
    try:
        s = ResolveSession()
    except ResolveError as e:
        out["error"] = str(e)
        out["code"] = e.code
        return out
    try:
        s.connect(timeout)
        out["connected"] = True
        out["version"] = s.version()
        info = s.timeline_info()
        out["timeline"] = info.to_dict()
        out["api"] = s.api_report()
        ok, presets = _call(s.project(), "GetRenderPresetList")
        out["render_presets"] = list(presets) if ok and isinstance(presets, (list, tuple)) else []
    except ResolveError as e:
        out["error"] = str(e)
        out["code"] = e.code
    return out


def revision_ranges_from_resolve(info: TimelineInfo, marker_color: Optional[str] = None,
                                 marker_prefix: str = "REV") -> List[dict]:
    """Candidate revision ranges: In/Out marks and duration markers.

    Ranges are returned as absolute timeline frames, end exclusive.
    """
    out = []
    if info.mark_in is not None and info.mark_out is not None and info.mark_out >= info.mark_in:
        out.append({"source": "in_out", "start": info.mark_in, "end": info.mark_out + 1, "label": "In/Out"})
    for m in info.markers:
        if m["duration"] <= 1:
            continue
        name = (m.get("name") or "") + " " + (m.get("note") or "")
        if marker_color and m.get("color", "").lower() != marker_color.lower() and \
                not name.strip().upper().startswith(marker_prefix):
            continue
        out.append({"source": "marker", "start": m["frame"], "end": m["frame"] + m["duration"],
                    "label": (m.get("name") or m.get("note") or f"marker@{m['frame']}").strip(),
                    "color": m.get("color")})
    return out
