"""Deterministic synthetic timelines for automated tests and demos.

A synthetic timeline stands in for a DaVinci Resolve timeline: it can render
any frame range to an intermediate (ProRes + PCM, like the Resolve bridge) and
can produce "delivery" H.264 masters with configurable GOP structure.

Content: FFmpeg's ``testsrc2`` (every frame differs: moving objects and a
frame counter) and a multi-tone audio signal.  Revisions are modelled as
effects over frame ranges (hue shift / negate), optional cross-fade
transitions, audio tone changes and duration changes (inserted/removed frames).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import List, Optional

from .ffmpeg import ffmpeg, run
from .timecode import parse_rate


@dataclass
class VideoChange:
    start: int                 # timeline-relative frame (in the *revised* timeline)
    end: int
    effect: str = "hue"        # hue | negate | bars
    fade_in: int = 0           # frames of cross-fade before `start` (a transition)


@dataclass
class AudioChange:
    start: int                 # frames
    end: int
    freq: float = 660.0


@dataclass
class DurationChange:
    at: int                    # original-timeline frame where new material starts
    remove: int                # original frames removed starting at `at`
    insert: int                # new frames inserted (shown as colour bars)


@dataclass
class SynthTimeline:
    width: int = 320
    height: int = 180
    fps: str = "25/1"
    frames: int = 250
    sample_rate: int = 48000
    channels: int = 2
    start_frame: int = 0       # absolute timeline frame of the first frame (e.g. 01:00:00:00)
    video_changes: List[VideoChange] = field(default_factory=list)
    audio_changes: List[AudioChange] = field(default_factory=list)
    duration_change: Optional[DurationChange] = None

    @property
    def rate(self) -> Fraction:
        return parse_rate(self.fps)

    @property
    def length(self) -> int:
        dc = self.duration_change
        return self.frames + ((dc.insert - dc.remove) if dc else 0)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "SynthTimeline":
        d = dict(d)
        d["video_changes"] = [VideoChange(**x) for x in d.get("video_changes", [])]
        d["audio_changes"] = [AudioChange(**x) for x in d.get("audio_changes", [])]
        if d.get("duration_change"):
            d["duration_change"] = DurationChange(**d["duration_change"])
        return cls(**d)

    @classmethod
    def load(cls, path: str) -> "SynthTimeline":
        with open(path) as f:
            return cls.from_dict(json.load(f))

    def revised(self, video_changes=(), audio_changes=(), duration_change=None) -> "SynthTimeline":
        return SynthTimeline(self.width, self.height, self.fps, self.frames, self.sample_rate, self.channels,
                             self.start_frame, list(video_changes), list(audio_changes), duration_change)

    # ------------------------------------------------------------------
    def _video_graph(self, start: int, end: int, out_label: str = "v") -> str:
        r = self.rate
        rs = f"{r.numerator}/{r.denominator}"
        W, H = self.width, self.height
        base = f"testsrc2=size={W}x{H}:rate={rs}"
        dc = self.duration_change
        parts = []
        if dc:
            # original [0, at) + bars [insert] + original [at+remove, frames)
            parts.append(f"{base},trim=start_frame=0:end_frame={dc.at},setpts=PTS-STARTPTS[p0]")
            if dc.insert > 0:
                parts.append(f"smptehdbars=size={W}x{H}:rate={rs},trim=start_frame=0:end_frame={dc.insert},"
                             f"setpts=PTS-STARTPTS[p1]")
            parts.append(f"{base},trim=start_frame={dc.at + dc.remove}:end_frame={self.frames},"
                         f"setpts=PTS-STARTPTS[p2]")
            n_in = 3 if dc.insert > 0 else 2
            labels = "[p0][p1][p2]" if dc.insert > 0 else "[p0][p2]"
            parts.append(f"{labels}concat=n={n_in}:v=1:a=0,format=yuv444p[t0]")
        else:
            parts.append(f"{base},format=yuv444p[t0]")
        cur = "t0"
        for i, ch in enumerate(self.video_changes):
            s0 = ch.start - ch.fade_in
            if ch.effect == "hue":
                eff = "hue=h=140:s=1.4"
            elif ch.effect == "negate":
                eff = "negate"
            else:
                eff = "hue=h=60"
            parts.append(f"[{cur}]split[a{i}][b{i}]")
            parts.append(f"[b{i}]{eff},format=yuv444p[e{i}]")
            # Frame index derived from the timestamp (blend's N counter is not
            # guaranteed to start at 0 in every FFmpeg version).
            fi = f"round(T*{r.numerator}/{r.denominator})"
            if ch.fade_in > 0:
                expr = (f"if(lt({fi},{s0}),A,if(gte({fi},{ch.end}),A,"
                        f"if(lt({fi},{ch.start}),A+(B-A)*({fi}-{s0}+1)/({ch.fade_in}+1),B)))")
            else:
                expr = f"if(between({fi},{ch.start},{ch.end - 1}),B,A)"
            parts.append(f"[a{i}][e{i}]blend=all_expr='{expr}'[c{i}]")
            cur = f"c{i}"
        parts.append(f"[{cur}]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS[{out_label}]")
        return ";".join(parts)

    def _audio_expr(self) -> str:
        r = self.rate
        base = "0.22*sin(2*PI*440*t)+0.12*sin(2*PI*1031*t+2*sin(2*PI*0.7*t))+0.05*sin(2*PI*3217*t)"
        expr = base
        for ch in self.audio_changes:
            ta = float(Fraction(ch.start) / r)
            tb = float(Fraction(ch.end) / r)
            expr = f"if(between(t,{ta:.9f},{tb:.9f}),0.3*sin(2*PI*{ch.freq}*t)+0.05*sin(2*PI*2000*t),{expr})"
        return expr

    def _audio_graph(self, start: int, end: int, out_label: str = "a") -> str:
        r = self.rate
        sr = self.sample_rate
        s0 = (Fraction(start) * sr / r).__floor__()
        s1 = (Fraction(end) * sr / r).__floor__()
        expr = self._audio_expr()
        if self.channels == 2:
            exprs = f"{expr}|0.9*({expr})"
            cl = "stereo"
        else:
            exprs = expr
            cl = "mono"
        dc = self.duration_change
        src = f"aevalsrc=exprs='{exprs}':s={sr}:c={cl}"
        if dc:
            a0 = (Fraction(dc.at) * sr / r).__floor__()
            a2 = (Fraction(dc.at + dc.remove) * sr / r).__floor__()
            ins = (Fraction(dc.at + dc.insert) * sr / r).__floor__() - a0
            total = (Fraction(self.frames) * sr / r).__floor__()
            parts = [f"{src},atrim=start_sample=0:end_sample={a0},asetpts=PTS-STARTPTS[q0]"]
            labels = "[q0]"
            if ins > 0:
                ins_expr = "0.2*sin(2*PI*1500*t)" + ("|0.2*sin(2*PI*1500*t)" if self.channels == 2 else "")
                parts.append(f"aevalsrc=exprs='{ins_expr}':s={sr}:c={cl},atrim=start_sample=0:end_sample={ins},"
                             f"asetpts=PTS-STARTPTS[q1]")
                labels += "[q1]"
            parts.append(f"{src},atrim=start_sample={a2}:end_sample={total},asetpts=PTS-STARTPTS[q2]")
            labels += "[q2]"
            parts.append(f"{labels}concat=n={labels.count('[')}:v=0:a=1[qa]")
            parts.append(f"[qa]atrim=start_sample={s0}:end_sample={s1},asetpts=PTS-STARTPTS[{out_label}]")
            return ";".join(parts)
        return f"{src},atrim=start_sample={s0}:end_sample={s1},asetpts=PTS-STARTPTS[{out_label}]"

    def render_intermediate(self, start: int, end: int, out_path: str, video: bool = True,
                            audio: bool = True, cancel=None, log=None) -> str:
        """Render timeline-relative frames [start, end) to ProRes 422 HQ + 24-bit PCM (.mov)."""
        graphs = []
        maps = []
        if video:
            graphs.append(self._video_graph(start, end, "v"))
            maps += ["-map", "[v]", "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le",
                     "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                     "-color_range", "tv", "-vendor", "apl0"]
        if audio:
            graphs.append(self._audio_graph(start, end, "a"))
            maps += ["-map", "[a]", "-c:a", "pcm_s24le"]
        cmd = [ffmpeg(), "-v", "error", "-y", "-nostdin", "-filter_complex", ";".join(graphs), *maps,
               "-r", f"{self.rate.numerator}/{self.rate.denominator}", out_path]
        run(cmd, cancel=cancel, log=log)
        return out_path

    def render_master(self, out_path: str, gop: int = 250, bframes: int = 3, profile: str = "high",
                      crf: int = 20, preset: str = "veryfast", open_gop: bool = False, pyramid: str = "normal",
                      aac_bitrate: str = "192k", audio: bool = True, extra_x264: str = "",
                      color: bool = True, scenecut: bool = True, aac_pns: bool = False,
                      pix_fmt: str = "yuv420p", cancel=None, log=None) -> str:
        """Render the whole timeline as an H.264/AAC MP4 'delivery' master."""
        graphs = [self._video_graph(0, self.length, "v0") + f";[v0]format={pix_fmt}[v]"]
        maps = ["-map", "[v]"]
        params = [f"keyint={gop}", f"bframes={bframes}", f"b-pyramid={pyramid}",
                  f"open-gop={1 if open_gop else 0}"]
        if not scenecut:
            params.append("scenecut=0")
        if extra_x264:
            params.append(extra_x264)
        vargs = ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-profile:v", profile,
                 "-x264-params", ":".join(params)]
        if color:
            vargs += ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                      "-color_range", "tv"]
        if audio:
            graphs.append(self._audio_graph(0, self.length, "a"))
            maps += ["-map", "[a]"]
            vargs += ["-c:a", "aac", "-b:a", aac_bitrate, "-aac_pns", "1" if aac_pns else "0"]
        cmd = [ffmpeg(), "-v", "error", "-y", "-nostdin", "-filter_complex", ";".join(graphs), *maps, *vargs,
               "-r", f"{self.rate.numerator}/{self.rate.denominator}", "-movflags", "+faststart", out_path]
        run(cmd, cancel=cancel, log=log)
        return out_path
