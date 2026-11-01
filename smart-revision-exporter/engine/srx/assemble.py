"""Assemble the patched MP4 from copied master packets and patch segments."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from . import h264
from .encoder import PatchInfo
from .media import MasterAnalysis
from .mp4 import (EditEntry, OutSample, OutTrack, make_box, replace_child_in_entry, write_movie)
from .plan import Plan


class AssembleError(RuntimeError):
    pass


@dataclass
class VideoAssembly:
    track: OutTrack
    parameter_sets: dict
    out_decode_segments: List[dict]   # output decode-index ranges per segment


def _btrt(samples: Sequence[OutSample], timescale: int) -> bytes:
    total = sum(s.size for s in samples)
    dur = sum(s.duration for s in samples) / timescale
    avg = int(total * 8 / dur) if dur > 0 else 0
    # peak over 1-second windows (in decode order)
    window = timescale
    peak = 0
    acc = 0
    t_acc = 0
    j = 0
    for i, s in enumerate(samples):
        acc += s.size
        t_acc += s.duration
        while t_acc > window and j <= i:
            acc -= samples[j].size
            t_acc -= samples[j].duration
            j += 1
        peak = max(peak, acc * 8)
    buf = max((s.size for s in samples), default=0)
    return struct.pack(">III", buf, peak, avg)


def assemble_video(master: MasterAnalysis, plan: Plan, patches: Dict[int, PatchInfo],
                   patch_sources: Dict[int, int], master_src: int = 0) -> VideoAssembly:
    v = master.video
    mt = v.track
    D = v.frame_duration
    samples: List[OutSample] = []
    used_pps_ids = set()
    seg_info = []
    out_dec = 0
    for si, seg in enumerate(plan.segments):
        dec_start = out_dec
        if seg.kind == "copy":
            # display range [s, e) equals decode range [s, e) at resume/cut points
            for j in range(seg.master_start, seg.master_end):
                disp = v.disp_of_dec[j]
                if not (seg.master_start <= disp < seg.master_end):
                    raise AssembleError(f"copy segment {seg.master_start}-{seg.master_end} is not closed "
                                        f"in decode order (sample {j})")
                out_disp = seg.out_start + (disp - seg.master_start)
                dts = out_dec * D
                cts = v.cts0 + out_disp * D
                samples.append(OutSample(master_src, mt.offsets[j], mt.sizes[j], D, cts - dts, mt.is_sync(j), 1))
                used_pps_ids.add(v.pps_id[j])
                out_dec += 1
        else:
            if seg.out_len == 0:
                seg_info.append({"segment": si, "kind": seg.kind, "decode_start": dec_start, "decode_end": out_dec})
                continue
            p = patches.get(si)
            if p is None:
                raise AssembleError(f"missing patch for render segment {si}")
            pt = p.movie.track_by_handler("vide")[0]
            if p.frame_count != seg.out_len:
                raise AssembleError("patch length does not match segment")
            src = patch_sources[si]
            for j in range(p.frame_count):
                out_disp = seg.out_start + p.disp_of_dec[j]
                dts = out_dec * D
                cts = v.cts0 + out_disp * D
                if cts - dts < 0:
                    raise AssembleError("patch needs a larger composition offset than the master provides")
                samples.append(OutSample(src, pt.offsets[j], pt.sizes[j], D, cts - dts, p.is_idr[j], 1))
                out_dec += 1
        seg_info.append({"segment": si, "kind": seg.kind, "decode_start": dec_start, "decode_end": out_dec})
    if out_dec != plan.output_frames:
        raise AssembleError(f"assembled {out_dec} frames, plan expects {plan.output_frames}")
    if plan.output_frames == v.frame_count and plan.segments[-1].kind == "copy":
        samples[-1].duration = mt.durations[-1]

    # ---- parameter sets ----------------------------------------------------
    pps_by_id = {p.pps_id: p for p in v.pps}
    sps_by_id = {s.sps_id: s for s in v.sps}
    used_sps_ids = set()
    for pid in used_pps_ids:
        if pid not in pps_by_id:
            raise AssembleError(f"copied frames reference unknown PPS {pid}")
        used_sps_ids.add(pps_by_id[pid].sps_id)
    sps_out: List[bytes] = []
    pps_out: List[bytes] = []
    # keep master order (avcC first, then in-band), filtered to referenced ids
    for s in v.sps:
        if s.sps_id in used_sps_ids and s.raw not in sps_out:
            sps_out.append(s.raw)
    for p in v.pps:
        if p.pps_id in used_pps_ids and p.raw not in pps_out:
            pps_out.append(p.raw)
    for si in sorted(patches):
        pinfo = patches[si]
        for s in pinfo.sps:
            if s.sps_id in used_sps_ids and sps_by_id[s.sps_id].raw != s.raw:
                raise AssembleError(f"SPS id {s.sps_id} conflict between master and patch")
            if s.raw not in sps_out:
                sps_out.append(s.raw)
        for pp in pinfo.pps:
            if pp.pps_id in used_pps_ids and pps_by_id[pp.pps_id].raw != pp.raw:
                raise AssembleError(f"PPS id {pp.pps_id} conflict between master and patch")
            if pp.raw not in pps_out:
                pps_out.append(pp.raw)
    # ids must be unique within the record
    ids = [h264.parse_sps(s).sps_id for s in sps_out]
    if len(ids) != len(set(ids)):
        raise AssembleError(f"duplicate SPS ids in output parameter sets: {ids}")
    pids = [h264.parse_pps(p).pps_id for p in pps_out]
    if len(pids) != len(set(pids)):
        raise AssembleError(f"duplicate PPS ids in output parameter sets: {pids}")
    base = v.avcc
    first = h264.parse_sps(sps_out[0])
    cfg = h264.AvcConfig(profile=first.profile_idc, compat=first.constraint_flags, level=first.level_idc,
                         length_size=base.length_size, sps=sps_out, pps=pps_out, ext=base.ext)
    entry = replace_child_in_entry(mt.stsd_entries[0], "avcC", cfg.build())
    if b"btrt" in mt.stsd_entries[0]:
        # keep the optional bit-rate box but make its values truthful
        entry = replace_child_in_entry(entry, "btrt", _btrt(samples, mt.timescale))

    edits = mt.edits
    if edits is not None and plan.output_frames != v.frame_count:
        delta_media = (plan.output_frames - v.frame_count) * D
        delta_movie = delta_media * master.movie.timescale // mt.timescale
        new = []
        for e in edits:
            if e.media_time != -1:
                e = EditEntry(max(0, e.segment_duration + delta_movie), e.media_time, e.rate_int, e.rate_frac)
            new.append(e)
        edits = new
    track = OutTrack(template=mt, samples=samples, stsd_entries=[entry], edits=edits,
                     stbl_extra=[b.raw for b in mt.stbl_other if b.type not in ("sdtp", "cslg", "sgpd", "sbgp")])
    return VideoAssembly(track=track,
                         parameter_sets={"sps_ids": ids, "pps_ids": pids, "count": len(ids)},
                         out_decode_segments=seg_info)


def write_output(master: MasterAnalysis, video_track: OutTrack, audio_tracks: Dict[int, OutTrack],
                 other_tracks: Dict[int, OutTrack], sources: List[str], out_path: str,
                 faststart: Optional[bool] = None, progress=None, cancel_check=None) -> None:
    tracks: List[OutTrack] = []
    ai = 0
    for t in master.movie.tracks:
        if t is master.video.track:
            tracks.append(video_track)
        elif t.handler == "soun":
            tracks.append(audio_tracks[ai])
            ai += 1
        else:
            tracks.append(other_tracks[t.track_id])
    fs = master.movie.moov_before_mdat if faststart is None else faststart
    write_movie(out_path, sources, master.movie, tracks, faststart=fs, progress=progress,
                cancel_check=cancel_check)


def extract_video_clip(master: MasterAnalysis, start: int, end: int, out_path: str) -> None:
    """Write master frames [start, end) (start: resume point, end: cut point) as a
    standalone MP4 by stream copy.  Decodes identically to the same frames in the
    master because the range starts with an IDR and is closed in decode order."""
    v = master.video
    if start not in set(v.resume_points) and start != 0:
        raise AssembleError(f"clip start {start} is not a resume point")
    if end != v.frame_count and end not in set(v.cut_points):
        raise AssembleError(f"clip end {end} is not a clean cut point")
    mt = v.track
    D = v.frame_duration
    samples = []
    for j in range(start, end):
        disp = v.disp_of_dec[j] - start
        samples.append(OutSample(0, mt.offsets[j], mt.sizes[j], D, v.cts0 + disp * D - (j - start) * D,
                                 mt.is_sync(j), mt.desc_index[j]))
    edits = None
    if mt.edits is not None:
        seg = (end - start) * D * master.movie.timescale // mt.timescale
        edits = [EditEntry(seg, v.cts0, 1, 0)]
    track = OutTrack(template=mt, samples=samples, stsd_entries=mt.stsd_entries, edits=edits)
    write_movie(out_path, [master.path], master.movie, [track], faststart=True)
