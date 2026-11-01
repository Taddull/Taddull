"""In-process mock of the DaVinci Resolve scripting API for automated tests.

It mirrors the *documented* object model (Resolve -> ProjectManager -> Project
-> Timeline) closely enough to exercise ResolveSession/ResolveRenderSource.
Renders are produced by the synthetic timeline renderer.  This mock proves the
bridge's orchestration logic only; it is NOT evidence that the real Resolve
behaves identically - see docs/MANUAL_RESOLVE_TESTS.md.

Enabled with SRX_RESOLVE_MOCK=/path/to/mock.json:
  {"timeline": {...SynthTimeline...}, "project": "Doc", "timeline_name": "Edit v3",
   "mark_in": 1234, "mark_out": 1300, "markers": {"120": {"color": "Purple", "duration": 25, "name": "REV 1"}},
   "fail_render": false}
"""

from __future__ import annotations

import json
import os
import threading
from typing import Optional

from .synthetic import SynthTimeline


class _Timeline:
    def __init__(self, cfg: dict, tl: SynthTimeline):
        self.cfg = cfg
        self.tl = tl

    def GetName(self):
        return self.cfg.get("timeline_name", "Timeline 1")

    def GetStartFrame(self):
        return self.tl.start_frame

    def GetEndFrame(self):
        return self.tl.start_frame + self.tl.length

    def GetStartTimecode(self):
        from .timecode import frames_to_tc
        return frames_to_tc(self.tl.start_frame, self.tl.rate)

    def GetSetting(self, key=None):
        r = self.tl.rate
        vals = {"timelineFrameRate": f"{float(r):.3f}".rstrip("0").rstrip("."),
                "timelineResolutionWidth": str(self.tl.width), "timelineResolutionHeight": str(self.tl.height),
                "timelineDropFrameTimecode": "0"}
        return vals.get(key) if key else vals

    def GetMarkers(self):
        return {float(k): v for k, v in self.cfg.get("markers", {}).items()}

    def GetMarkInOut(self):
        if "mark_in" not in self.cfg:
            return {}
        return {"video": {"in": self.cfg["mark_in"], "out": self.cfg["mark_out"]},
                "audio": {"in": self.cfg["mark_in"], "out": self.cfg["mark_out"]}}

    def GetTrackCount(self, kind):
        return 0


class _Project:
    def __init__(self, cfg: dict, tl: SynthTimeline):
        self.cfg = cfg
        self.tl = tl
        self.timeline = _Timeline(cfg, tl)
        self.settings = {}
        self.fmt = {"format": "mp4", "codec": "H264"}
        self.mode = 0
        self.jobs = {}
        self.next_id = 1
        self.rendering = False
        self.presets = ["YouTube 1080p"]
        self.render_log = []

    def GetName(self):
        return self.cfg.get("project", "Mock Project")

    def GetCurrentTimeline(self):
        return self.timeline

    def GetSetting(self, key=None):
        return self.timeline.GetSetting(key)

    def GetRenderFormats(self):
        return {"QuickTime": "mov", "MP4": "mp4", "Wave": "wav"}

    def GetRenderCodecs(self, fmt):
        if fmt == "wav":
            return {"Linear PCM": "LinearPCM"}
        if fmt == "mov":
            return {"Apple ProRes 422 HQ": "ProRes422HQ", "Apple ProRes 422": "ProRes422", "H.264": "H264"}
        return {"H.264": "H264"}

    def GetCurrentRenderFormatAndCodec(self):
        return dict(self.fmt)

    def SetCurrentRenderFormatAndCodec(self, fmt, codec):
        if codec not in self.GetRenderCodecs(fmt).values():
            return False
        self.fmt = {"format": fmt, "codec": codec}
        return True

    def GetCurrentRenderMode(self):
        return self.mode

    def SetCurrentRenderMode(self, m):
        self.mode = m
        return True

    def SetRenderSettings(self, s):
        allowed = {"SelectAllFrames", "MarkIn", "MarkOut", "TargetDir", "CustomName", "ExportVideo",
                   "ExportAudio", "AudioCodec", "FormatWidth", "FormatHeight", "FrameRate", "VideoQuality"}
        if not set(s) <= allowed:
            return False
        self.settings.update(s)
        return True

    def GetRenderPresetList(self):
        return list(self.presets)

    def SaveAsNewRenderPreset(self, name):
        self.presets.append(name)
        self._saved = (dict(self.settings), dict(self.fmt), self.mode)
        return True

    def LoadRenderPreset(self, name):
        if name not in self.presets:
            return False
        if name.startswith("SRX-restore") and hasattr(self, "_saved"):
            self.settings, self.fmt, self.mode = (dict(self._saved[0]), dict(self._saved[1]), self._saved[2])
        return True

    def DeleteRenderPreset(self, name):
        if name in self.presets:
            self.presets.remove(name)
            return True
        return False

    def AddRenderJob(self):
        jid = f"mock-{self.next_id}"
        self.next_id += 1
        self.jobs[jid] = {"settings": dict(self.settings), "fmt": dict(self.fmt), "status": "Ready", "pct": 0}
        return jid

    def DeleteRenderJob(self, jid):
        return self.jobs.pop(jid, None) is not None

    def GetRenderJobList(self):
        out = []
        for jid, j in self.jobs.items():
            out.append({"JobId": jid, "TargetDir": j["settings"].get("TargetDir"),
                        "OutputFilename": j.get("output_name"), "MarkIn": j["settings"].get("MarkIn"),
                        "MarkOut": j["settings"].get("MarkOut")})
        return out

    def GetRenderJobStatus(self, jid):
        j = self.jobs.get(jid)
        if not j:
            return {}
        return {"JobStatus": j["status"], "CompletionPercentage": j["pct"]}

    def IsRenderingInProgress(self):
        return self.rendering

    def StopRendering(self):
        self.rendering = False

    def StartRendering(self, *args):
        ids = args[0] if args and isinstance(args[0], list) else list(args)
        ids = [i for i in ids if isinstance(i, str)]
        if not ids:
            return False
        self.rendering = True

        def work():
            try:
                for jid in ids:
                    j = self.jobs[jid]
                    j["status"] = "Rendering"
                    s = j["settings"]
                    if self.cfg.get("fail_render"):
                        j["status"] = "Failed"
                        continue
                    start = (self.tl.start_frame if s.get("SelectAllFrames") else s["MarkIn"]) - self.tl.start_frame
                    end = (self.tl.length if s.get("SelectAllFrames") else s["MarkOut"] - self.tl.start_frame + 1)
                    ext = "wav" if j["fmt"]["format"] == "wav" else "mov"
                    name = s.get("CustomName", "render") + "." + ext
                    os.makedirs(s["TargetDir"], exist_ok=True)
                    if ext == "wav" and s.get("ExportVideo", True):
                        j["status"] = "Failed"
                        continue
                    self.tl.render_intermediate(start, end, os.path.join(s["TargetDir"], name),
                                                video=s.get("ExportVideo", True), audio=s.get("ExportAudio", True))
                    self.render_log.append({"start": start, "end": end, "video": s.get("ExportVideo", True),
                                            "format": ext})
                    j["output_name"] = name
                    j["pct"] = 100
                    j["status"] = "Complete"
            finally:
                self.rendering = False
        threading.Thread(target=work, daemon=True).start()
        return True


class _ProjectManager:
    def __init__(self, project):
        self.project = project

    def GetCurrentProject(self):
        return self.project


class _Resolve:
    def __init__(self, cfg: dict):
        tl = SynthTimeline.from_dict(cfg["timeline"])
        self.pm = _ProjectManager(_Project(cfg, tl))
        self.page = "edit"

    def GetProjectManager(self):
        return self.pm

    def GetVersionString(self):
        return "19.1.0 (mock)"

    def GetVersion(self):
        return [19, 1, 0, 0, "mock"]

    def GetProductName(self):
        return "DaVinci Resolve Studio (mock)"

    def GetCurrentPage(self):
        return self.page

    def OpenPage(self, p):
        self.page = p
        return True


_INSTANCE: Optional[_Resolve] = None


def scriptapp(name: str):
    global _INSTANCE
    if name != "Resolve":
        return None
    path = os.environ.get("SRX_RESOLVE_MOCK")
    if not path or path == "offline":
        return None
    if _INSTANCE is None:
        with open(path) as f:
            _INSTANCE = _Resolve(json.load(f))
    return _INSTANCE


def reset():
    global _INSTANCE
    _INSTANCE = None
