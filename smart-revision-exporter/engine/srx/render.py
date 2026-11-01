"""Render sources: where freshly rendered timeline frames come from.

* ResolveRenderSource   - DaVinci Resolve via the official scripting API
                          (see resolve_bridge.py)
* FileRenderSource      - renders the user exported manually from Resolve
                          (fallback when external scripting is unavailable)
* SyntheticRenderSource - deterministic synthetic timeline (tests / demo)

Every render is validated before use: exact frame count, frame rate, frame
size and audio layout must match what the plan requested.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import List, Optional

from .ffmpeg import ffprobe_json
from .mp4 import read_movie
from .plan import RenderRequest
from .synthetic import SynthTimeline


class RenderError(RuntimeError):
    pass


@dataclass
class RenderedClip:
    path: str
    timeline_start: int
    timeline_end: int
    has_video: bool
    has_audio: bool
    width: int = 0
    height: int = 0
    pix_fmt: str = ""
    color_range: Optional[str] = None
    fps: str = ""
    frame_count: int = 0
    audio_streams: List[dict] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_clip(path: str, timeline_start: int, expect_frames: Optional[int], fps: Fraction,
                 need_video: bool, source: str) -> RenderedClip:
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise RenderError(f"render output missing or empty: {path}")
    probe = ffprobe_json(path, ["-show_streams"])
    vs = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    aus = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
    clip = RenderedClip(path=path, timeline_start=timeline_start, timeline_end=timeline_start,
                        has_video=bool(vs), has_audio=bool(aus), source=source)
    clip.audio_streams = [{"index": i, "codec": s.get("codec_name"), "channels": s.get("channels"),
                           "sample_rate": int(s.get("sample_rate", 0))} for i, s in enumerate(aus)]
    if need_video:
        if not vs:
            raise RenderError(f"render has no video stream: {path}")
        v = vs[0]
        clip.width, clip.height = v["width"], v["height"]
        clip.pix_fmt = v.get("pix_fmt", "")
        clip.color_range = v.get("color_range")
        # exact frame count from the container sample table (MOV/MP4) or by counting packets
        count = None
        try:
            mv = read_movie(path)
            vt = mv.track_by_handler("vide")
            if vt:
                t = vt[0]
                count = t.sample_count
                d = t.durations[0] if t.durations else 0
                if d:
                    r = Fraction(t.timescale, d)
                    if r != fps:
                        raise RenderError(f"render frame rate {r} != timeline/master rate {fps}")
                    clip.fps = f"{r.numerator}/{r.denominator}"
                if len(set(t.durations[:-1])) > 1:
                    raise RenderError("render is variable frame rate")
        except RenderError:
            raise
        except Exception:
            count = None
        if count is None:
            p2 = ffprobe_json(path, ["-select_streams", "v:0", "-count_packets", "-show_entries",
                                     "stream=nb_read_packets,r_frame_rate"])
            st = p2["streams"][0]
            count = int(st["nb_read_packets"])
            rr = Fraction(st["r_frame_rate"])
            if rr != fps:
                raise RenderError(f"render frame rate {rr} != timeline/master rate {fps}")
            clip.fps = st["r_frame_rate"]
        clip.frame_count = count
        if expect_frames is not None and count != expect_frames:
            raise RenderError(f"render contains {count} frames, expected {expect_frames} "
                              f"(timeline frames {timeline_start}-{timeline_start + expect_frames - 1})")
        clip.timeline_end = timeline_start + count
    else:
        if not aus:
            raise RenderError(f"audio-only render has no audio stream: {path}")
        if expect_frames is None:
            raise RenderError("audio-only render needs an expected frame count")
        a0 = aus[0]
        sr = int(a0.get("sample_rate", 0))
        dur_ts = a0.get("duration_ts")
        nsamp = int(dur_ts) if dur_ts not in (None, "N/A") else int(float(a0.get("duration", 0)) * sr)
        need = int(Fraction(expect_frames) * sr / fps)
        if nsamp + 2 < need:
            raise RenderError(f"audio render has {nsamp} samples, expected about {need}")
        clip.timeline_end = timeline_start + expect_frames
    return clip


class RenderSource:
    name = "abstract"
    rate: Optional[Fraction] = None   # timeline frame rate, when known

    def render(self, req: RenderRequest, out_dir: str, cancel=None, progress=None, log=None) -> RenderedClip:
        raise NotImplementedError

    def describe(self) -> dict:
        return {"source": self.name}

    def cleanup(self) -> None:
        pass


class SyntheticRenderSource(RenderSource):
    name = "synthetic"

    def __init__(self, timeline: SynthTimeline):
        self.timeline = timeline
        self.rate = timeline.rate

    def render(self, req: RenderRequest, out_dir: str, cancel=None, progress=None, log=None) -> RenderedClip:
        tl = self.timeline
        s = req.timeline_start - tl.start_frame
        e = req.timeline_end - tl.start_frame
        if s < 0 or e > tl.length:
            raise RenderError(f"requested frames outside synthetic timeline ({s}..{e} of {tl.length})")
        path = os.path.join(out_dir, f"render_{req.timeline_start}_{req.timeline_end}.mov")
        tl.render_intermediate(s, e, path, video=req.video, audio=req.audio, cancel=cancel, log=log)
        if progress:
            progress(1.0)
        return inspect_clip(path, req.timeline_start, e - s, tl.rate, req.video, self.name)

    def describe(self) -> dict:
        return {"source": self.name, "timeline": json.loads(self.timeline.to_json())}


@dataclass
class ManualRender:
    path: str
    timeline_start: int   # absolute timeline frame of the file's first frame


class FileRenderSource(RenderSource):
    """Use renders exported manually from Resolve.

    Each file must be a frame-accurate render (ProRes/DNx/uncompressed + PCM
    recommended) whose first frame is `timeline_start`.  A full-timeline render
    covers every request.
    """
    name = "files"

    def __init__(self, renders: List[ManualRender], fps: Fraction):
        self.renders = renders
        self.fps = fps
        self.rate = fps
        self._inspected = {}

    def _clip(self, r: ManualRender) -> RenderedClip:
        if r.path not in self._inspected:
            self._inspected[r.path] = inspect_clip(r.path, r.timeline_start, None, self.fps, True, self.name)
        return self._inspected[r.path]

    def render(self, req: RenderRequest, out_dir: str, cancel=None, progress=None, log=None) -> RenderedClip:
        for r in self.renders:
            c = self._clip(r)
            if c.timeline_start <= req.timeline_start and c.timeline_end >= req.timeline_end:
                if progress:
                    progress(1.0)
                return c
        raise RenderError(
            f"no imported render covers timeline frames {req.timeline_start}-{req.timeline_end - 1}. "
            f"Render that range (In/Out) from Resolve as ProRes 422 HQ with Linear PCM audio and import it.")

    def describe(self) -> dict:
        return {"source": self.name, "renders": [asdict(r) for r in self.renders]}
