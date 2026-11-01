"""Revision planning: which frames are copied, rendered, re-encoded.

Frame-category vocabulary used throughout the engine and the reports:

* revised     - frames the user declared as changed (including user handles)
* boundary    - frames re-encoded only because of codec dependencies (GOP
                structure).  Their content is expected to be unchanged; they
                come from a fresh Resolve render, are NOT pixel-identical to
                the master and are reported separately.
* preserved   - frames whose compressed packets are copied byte-for-byte and
                whose decoded pixels are verified identical to the master.
* guard       - frames rendered only to detect unexpected changes next to a
                revision (never written to the output).
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import List, Optional, Tuple

from .media import MasterAnalysis


class PlanError(ValueError):
    pass


@dataclass
class Revision:
    start: int                 # first master frame (display order, inclusive)
    end: int                   # end master frame (exclusive)
    video: bool = True
    audio: bool = True
    label: str = ""
    handles_before: int = 0    # extra frames replaced before start (transitions, temporal fx)
    handles_after: int = 0
    delta: int = 0             # timeline frames added (+) / removed (-) inside this range

    @classmethod
    def from_dict(cls, d: dict) -> "Revision":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class Segment:
    kind: str                  # "copy" | "render"
    master_start: int
    master_end: int
    out_start: int
    out_end: int
    timeline_start: int = 0    # absolute Resolve timeline frames (render only)
    timeline_end: int = 0
    render_start: int = 0      # timeline range actually rendered (incl. guards)
    render_end: int = 0
    revised: List[Tuple[int, int]] = field(default_factory=list)   # output frame ranges
    revised_master: List[Tuple[int, int]] = field(default_factory=list)  # master ranges they replace
    boundary_frames: int = 0
    revised_frames: int = 0

    @property
    def out_len(self) -> int:
        return self.out_end - self.out_start


@dataclass
class AudioSplice:
    packet_start: int          # first replaced AAC packet
    packet_end: int            # end packet (exclusive)
    sample_start: int          # presentation sample range that is intended to change
    sample_end: int


@dataclass
class AudioTrackPlan:
    index: int
    strategy: str              # copy | splice | full
    reason: str
    splices: List[AudioSplice] = field(default_factory=list)


@dataclass
class RenderRequest:
    timeline_start: int        # absolute timeline frame, inclusive
    timeline_end: int          # exclusive
    video: bool
    audio: bool
    purpose: str

    @property
    def frames(self) -> int:
        return self.timeline_end - self.timeline_start


@dataclass
class Plan:
    mode: str
    strict: bool
    master_frames: int
    output_frames: int
    timeline_offset: int
    fps: str
    revisions: List[Revision]
    segments: List[Segment]
    audio: List[AudioTrackPlan]
    renders: List[RenderRequest]
    guard_frames: int
    warnings: List[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Plan":
        p = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        p.revisions = [Revision.from_dict(r) for r in d["revisions"]]
        segs = []
        for s in d["segments"]:
            s = dict(s)
            s["revised"] = [tuple(x) for x in s.get("revised", [])]
            s["revised_master"] = [tuple(x) for x in s.get("revised_master", [])]
            segs.append(Segment(**s))
        p.segments = segs
        p.audio = [AudioTrackPlan(index=a["index"], strategy=a["strategy"], reason=a["reason"],
                                  splices=[AudioSplice(**x) for x in a.get("splices", [])])
                   for a in d["audio"]]
        p.renders = [RenderRequest(**r) for r in d["renders"]]
        return p

    def render_segments(self) -> List[Segment]:
        return [s for s in self.segments if s.kind == "render"]


def normalize_revisions(revs: List[Revision], n: int) -> List[Revision]:
    out = []
    for r in revs:
        if r.start < 0 or r.end > n or r.start >= r.end:
            raise PlanError(f"revision {r.label or ''} [{r.start}, {r.end}) is outside the master (0..{n})")
        if r.handles_before < 0 or r.handles_after < 0:
            raise PlanError("handles must be >= 0")
        if not (r.video or r.audio):
            raise PlanError(f"revision [{r.start}, {r.end}) affects neither video nor audio")
        if r.delta and not r.video:
            raise PlanError("a duration-changing revision must include video")
        if (r.end - r.start) + r.delta < 0:
            raise PlanError("revision removes more frames than it spans")
        out.append(r)
    return sorted(out, key=lambda r: (r.start, r.end))


def merge_ranges(ranges: List[Tuple[int, int, int]], gap: int = 0) -> List[Tuple[int, int, int]]:
    """Merge (start, end, delta) ranges that overlap or are closer than `gap`."""
    out: List[Tuple[int, int, int]] = []
    for s, e, d in sorted(ranges):
        if out and s <= out[-1][1] + gap:
            ps, pe, pd = out[-1]
            out[-1] = (ps, max(pe, e), pd + d)
        else:
            out.append((s, e, d))
    return out


def build_plan(master: MasterAnalysis, revisions: List[Revision], mode: str = "verified",
               strict: bool = False, timeline_offset: int = 0, audio_strategy: str = "auto",
               guard_frames: int = 6, merge_gap: int = 0) -> Plan:
    v = master.video
    if not v.patchable:
        raise PlanError("master cannot be patched: " + "; ".join(v.blocking_issues))
    n = v.frame_count
    revs = normalize_revisions(revisions, n)
    if not revs:
        raise PlanError("no revision ranges given")
    warnings: List[str] = []

    vranges = [(max(0, r.start - r.handles_before), min(n, r.end + r.handles_after), r.delta)
               for r in revs if r.video]
    vmerged = merge_ranges(vranges)

    # cumulative delta mapping master -> timeline (relative frames)
    def master_to_rel(i: int) -> int:
        # i must not be strictly inside a merged revision
        acc = 0
        for s, e, d in vmerged:
            if e <= i:
                acc += d
        return i + acc

    # reconstruction regions
    regions = []
    for s, e, d in vmerged:
        k = v.prev_cut(s)
        r = v.next_resume(e)
        regions.append([k, r, [(s, e, d)]])
    regions.sort()
    merged_regions: List[list] = []
    for reg in regions:
        if merged_regions and reg[0] <= merged_regions[-1][1] + merge_gap:
            last = merged_regions[-1]
            if reg[0] > last[1]:
                # gap smaller than merge_gap: extend to next resume point
                pass
            last[1] = max(last[1], reg[1])
            last[2].extend(reg[2])
        else:
            merged_regions.append(reg)
    # a merge may make a region end at a non-resume point; re-snap
    for reg in merged_regions:
        reg[1] = v.next_resume(reg[1]) if reg[1] < n else n

    total_delta = sum(d for _, _, d in vmerged)
    n_out = n + total_delta
    segments: List[Segment] = []
    pos = 0
    for k, r, inner in merged_regions:
        if k > pos:
            segments.append(Segment("copy", pos, k, master_to_rel(pos), master_to_rel(pos) + (k - pos)))
        t0 = master_to_rel(k)
        t1 = master_to_rel(r)
        revised = []
        revised_master = []
        rev_frames = 0
        for s, e, d in inner:
            os_ = master_to_rel(s)
            oe = os_ + (e - s) + d
            revised.append((os_, oe))
            revised_master.append((s, e))
            rev_frames += oe - os_
        boundary = (t1 - t0) - rev_frames
        seg = Segment("render", k, r, t0, t1, timeline_start=timeline_offset + t0,
                      timeline_end=timeline_offset + t1, revised=revised, revised_master=revised_master,
                      boundary_frames=boundary, revised_frames=rev_frames)
        head_boundary = (revised[0][0] - t0) if revised else (t1 - t0)
        tail_boundary = (t1 - revised[-1][1]) if revised else 0
        g_before = max(0, guard_frames - head_boundary) if k > 0 else 0
        g_after = max(0, guard_frames - tail_boundary) if r < n else 0
        seg.render_start = max(timeline_offset, seg.timeline_start - g_before)
        seg.render_end = min(timeline_offset + n_out, seg.timeline_end + g_after)
        segments.append(seg)
        pos = r
    if pos < n:
        segments.append(Segment("copy", pos, n, master_to_rel(pos), master_to_rel(pos) + (n - pos)))

    # sanity: segments tile the output
    cur = 0
    for s in segments:
        if s.out_start != cur:
            raise PlanError(f"internal planning error: gap at output frame {cur}")
        cur = s.out_end
    if cur != n_out:
        raise PlanError("internal planning error: output length mismatch")

    boundary_total = sum(s.boundary_frames for s in segments if s.kind == "render")
    if strict and boundary_total > 0:
        details = []
        for s in segments:
            if s.kind == "render" and s.boundary_frames:
                details.append(f"master frames {s.master_start}-{s.master_end - 1} must be rebuilt "
                               f"({s.boundary_frames} unchanged frames would be re-encoded)")
        raise PlanError(
            "Strict Verified Frame Preservation cannot be met with this master: H.264 inter-frame "
            "dependencies require re-encoding frames outside the revision ranges. "
            + "; ".join(details)
            + ". Options: (1) disable Strict and accept re-encoded boundary frames (reported and "
              "quality-checked), (2) align revisions to the master's IDR frames, (3) create a "
              "Revision-Ready Master (short closed GOP or all-intra), or (4) Safe Full Export.")

    # ----- audio -------------------------------------------------------------
    audio_plans: List[AudioTrackPlan] = []
    arevs = [r for r in revs if r.audio]
    rate = v.fps
    for a in master.audio:
        if not arevs and total_delta == 0:
            audio_plans.append(AudioTrackPlan(a.index, "copy", "no audio revisions"))
            continue
        strategy = audio_strategy
        reason = "requested"
        if audio_strategy == "auto":
            if total_delta != 0:
                strategy, reason = "full", ("duration change shifts every later AAC frame; "
                                            "the whole track must be re-encoded")
            elif a.blocking_issues:
                strategy, reason = "full", "packet splice not possible: " + "; ".join(a.blocking_issues)
            else:
                strategy, reason = "splice", "AAC-LC packet splice with overlap guard frames"
        if strategy == "copy":
            if total_delta != 0:
                raise PlanError("audio cannot be copied when the video duration changes")
            if arevs:
                warnings.append(f"audio track {a.index}: copy requested although revisions are marked "
                                f"as affecting audio; the original audio is kept")
            audio_plans.append(AudioTrackPlan(a.index, "copy", reason))
            continue
        if strategy == "splice":
            if total_delta != 0:
                raise PlanError("audio splice is impossible when the video duration changes")
            if a.blocking_issues:
                raise PlanError("audio splice not possible: " + "; ".join(a.blocking_issues))
            F = a.frame_size
            P = a.priming
            margin = 2 * F
            sranges = []
            for r in arevs:
                s0 = math.floor(Fraction(max(0, r.start - r.handles_before)) * a.sample_rate / rate)
                s1 = math.ceil(Fraction(min(n, r.end + r.handles_after)) * a.sample_rate / rate)
                p = max(0, (s0 - margin + P) // F)
                q = min(a.packet_count, -(-(s1 + margin + P) // F))
                sranges.append((p, q, s0, s1))
            sranges.sort()
            merged: List[list] = []
            for p, q, s0, s1 in sranges:
                if merged and p <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], q)
                    merged[-1][3] = max(merged[-1][3], s1)
                else:
                    merged.append([p, q, s0, s1])
            audio_plans.append(AudioTrackPlan(a.index, "splice", reason,
                                              [AudioSplice(p, q, s0, s1) for p, q, s0, s1 in merged]))
            continue
        if strategy == "full":
            audio_plans.append(AudioTrackPlan(a.index, "full", reason))
            continue
        raise PlanError(f"unknown audio strategy '{strategy}'")

    # ----- render requests ---------------------------------------------------
    intervals: List[list] = []  # [start, end, video, purpose]
    for s in segments:
        if s.kind == "render" and s.render_end > s.render_start:
            intervals.append([s.render_start, s.render_end, True, "video"])
    full_audio = any(ap.strategy == "full" for ap in audio_plans)
    for ap in audio_plans:
        if ap.strategy != "splice":
            continue
        a = master.audio[ap.index]
        F = a.frame_size
        for sp in ap.splices:
            # Warm-up of 4 packets before/after covers any encoder delay <= 4096 samples
            # plus extra unchanged audio used to measure alignment.
            s_lo = sp.packet_start * F - a.priming - 6 * F
            s_hi = sp.packet_end * F - a.priming + 6 * F
            f_lo = math.floor(Fraction(max(0, s_lo)) * rate / a.sample_rate) - 1
            f_hi = math.ceil(Fraction(s_hi) * rate / a.sample_rate) + 1
            f_lo = max(0, f_lo)
            f_hi = min(n_out, f_hi)
            intervals.append([timeline_offset + f_lo, timeline_offset + f_hi, False, "audio-splice"])
    intervals.sort(key=lambda x: (x[0], x[1]))
    renders: List[RenderRequest] = []
    for s, e, vid, purpose in intervals:
        if renders and s <= renders[-1].timeline_end:
            last = renders[-1]
            last.timeline_end = max(last.timeline_end, e)
            last.video = last.video or vid
            if purpose not in last.purpose:
                last.purpose += "+" + purpose
        else:
            renders.append(RenderRequest(s, e, vid, True, purpose))
    # A full-track audio re-encode gets its own AUDIO-ONLY render of the whole
    # timeline.  It is never merged with a video request: that would turn a
    # cheap audio render into a full video render.
    if full_audio:
        renders.append(RenderRequest(timeline_offset, timeline_offset + n_out, False, True, "full-audio"))
    for rr in renders:
        rr.audio = True

    rendered_video = sum(rr.frames for rr in renders if rr.video)
    reencoded = sum(s.out_len for s in segments if s.kind == "render")
    preserved = sum(s.out_len for s in segments if s.kind == "copy")
    revised_total = sum(s.revised_frames for s in segments if s.kind == "render")
    stats = {
        "master_frames": n,
        "output_frames": n_out,
        "preserved_frames": preserved,
        "reencoded_frames": reencoded,
        "revised_frames": revised_total,
        "boundary_frames": boundary_total,
        "rendered_video_frames": rendered_video,
        "rendered_percent": 100.0 * rendered_video / max(1, n_out),
        "preserved_percent": 100.0 * preserved / max(1, n_out),
        "render_jobs": len(renders),
        "duration_change_frames": total_delta,
        "audio_strategies": [ap.strategy for ap in audio_plans],
    }
    if stats["rendered_percent"] > 50:
        warnings.append(f"the patch re-renders {stats['rendered_percent']:.0f}% of the video; "
                        f"a Safe Full Export or a Revision-Ready Master may be preferable")
    if boundary_total:
        warnings.append(f"{boundary_total} unchanged frame(s) next to revisions must be re-encoded because of "
                        f"the master's GOP structure (they are rendered fresh from Resolve and quality-checked)")
    return Plan(mode=mode, strict=strict, master_frames=n, output_frames=n_out,
                timeline_offset=timeline_offset, fps=f"{rate.numerator}/{rate.denominator}",
                revisions=revs, segments=segments, audio=audio_plans, renders=renders,
                guard_frames=guard_frames, warnings=warnings, stats=stats)


def output_to_master_map(plan: Plan) -> List[int]:
    """For every output frame, the master frame it corresponds to, or -1 for
    frames that only exist in the revised timeline (duration changes)."""
    out = [-1] * plan.output_frames
    for seg in plan.segments:
        if seg.kind == "copy":
            for j in range(seg.out_start, seg.out_end):
                out[j] = seg.master_start + (j - seg.out_start)
            continue
        j = seg.out_start
        i = seg.master_start
        for (os_, oe), (ms, me) in zip(seg.revised, seg.revised_master):
            while j < os_:
                out[j] = i
                j += 1
                i += 1
            if (oe - os_) == (me - ms):
                for t in range(oe - os_):
                    out[j + t] = ms + t
            j = oe
            i = me
        while j < seg.out_end:
            out[j] = i
            j += 1
            i += 1
        if i != seg.master_end:
            raise PlanError("internal mapping error in render segment")
    return out


def output_frame_classes(plan: Plan) -> List[str]:
    cls = ["preserved"] * plan.output_frames
    for seg in plan.segments:
        if seg.kind != "render":
            continue
        for j in range(seg.out_start, seg.out_end):
            cls[j] = "boundary"
        for os_, oe in seg.revised:
            for j in range(os_, oe):
                cls[j] = "revised"
    return cls
