"""Patch-segment H.264 encoding with libx264, matched to the master's stream.

The patch segment must coexist with the master's parameter sets inside one
'avc1' track.  We therefore:

* encode with libx264 using a parameter-set id (``sps-id``) that no copied
  master frame references, so both SPS/PPS sets can live in one avcC record and
  are activated by the IDR that starts each segment;
* also repeat the patch SPS/PPS in-band before every patch IDR for decoders that
  only load the first avcC entry;
* match profile, level, chroma format, bit depth, entropy coder, 8x8 transform,
  VUI colour description, SAR and chroma location;
* restrict B-frame reordering so the patch never needs a larger composition
  offset than the master's edit list provides.

Hardware encoders (VideoToolbox) are deliberately not used for patch segments:
they cannot be constrained to a chosen parameter-set id or GOP structure, so the
joined stream could not be guaranteed decodable.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Sequence

from . import h264
from .ffmpeg import CancelToken, ffmpeg, passthrough_args, run
from .media import VideoAnalysis
from .mp4 import Movie, avcc_from_entry, read_movie

COLORPRIM = {1: "bt709", 2: "undef", 4: "bt470m", 5: "bt470bg", 6: "smpte170m", 7: "smpte240m", 8: "film",
             9: "bt2020", 10: "smpte428", 11: "smpte431", 12: "smpte432"}
TRANSFER = {1: "bt709", 2: "undef", 4: "bt470m", 5: "bt470bg", 6: "smpte170m", 7: "smpte240m", 8: "linear",
            9: "log100", 10: "log316", 11: "iec61966-2-4", 12: "bt1361e", 13: "iec61966-2-1",
            14: "bt2020-10", 15: "bt2020-12", 16: "smpte2084", 17: "smpte428", 18: "arib-std-b67"}
COLORMATRIX = {0: "GBR", 1: "bt709", 2: "undef", 4: "fcc", 5: "bt470bg", 6: "smpte170m", 7: "smpte240m",
               8: "YCgCo", 9: "bt2020nc", 10: "bt2020c", 11: "smpte2085", 12: "chroma-derived-nc",
               13: "chroma-derived-c", 14: "ICtCp"}
# ffmpeg option names for the same codes
FF_PRIM = {1: "bt709", 4: "bt470m", 5: "bt470bg", 6: "smpte170m", 7: "smpte240m", 8: "film", 9: "bt2020",
           10: "smpte428", 11: "smpte431", 12: "smpte432"}
FF_TRC = {1: "bt709", 4: "gamma22", 5: "gamma28", 6: "smpte170m", 7: "smpte240m", 8: "linear", 9: "log100",
          10: "log316", 11: "iec61966-2-4", 12: "bt1361e", 13: "iec61966-2-1", 14: "bt2020-10",
          15: "bt2020-12", 16: "smpte2084", 17: "smpte428", 18: "arib-std-b67"}
FF_MATRIX = {0: "gbr", 1: "bt709", 4: "fcc", 5: "bt470bg", 6: "smpte170m", 7: "smpte240m", 8: "ycgco",
             9: "bt2020nc", 10: "bt2020c", 11: "smpte2085", 12: "chroma-derived-nc", 13: "chroma-derived-c",
             14: "ictcp"}

X264_PROFILES = {66: "baseline", 77: "main", 100: "high", 110: "high10", 122: "high422", 244: "high444"}


class EncodeError(RuntimeError):
    pass


@dataclass
class EncoderSettings:
    profile: str
    level: str
    pix_fmt: str
    fps: str
    sps_id: int
    x264_params: Dict[str, str]
    preset: str = "slow"
    crf: Optional[float] = 16.0
    bitrate_kbps: Optional[int] = None   # for two-pass "match" mode
    two_pass: bool = False
    color_args: List[str] = field(default_factory=list)
    vf_extra: List[str] = field(default_factory=list)
    threads: int = 0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def free_parameter_set_id(used_sps: Sequence[int], used_pps: Sequence[int]) -> int:
    for i in range(1, 32):
        if i not in used_sps and i not in used_pps:
            return i
    if 0 not in used_sps and 0 not in used_pps:
        return 0
    raise EncodeError("all 32 SPS ids are in use; run a Safe Full Export to reset the stream")


def derive_settings(video: VideoAnalysis, used_sps: Sequence[int], used_pps: Sequence[int],
                    quality: str = "high", preset: str = "slow", threads: int = 0,
                    local_bitrate_kbps: Optional[int] = None) -> EncoderSettings:
    from .media import peak_bitrate_kbps
    sps = video.active_sps()
    pps = video.active_pps()
    notes: List[str] = []
    prof = X264_PROFILES.get(sps.profile_idc)
    if prof is None:
        raise EncodeError(f"no x264 profile matches master profile_idc {sps.profile_idc}")
    level = sps.level_str
    params: Dict[str, str] = {}
    sid = free_parameter_set_id(used_sps, used_pps)
    params["sps-id"] = str(sid)
    params["repeat-headers"] = "1"
    params["open-gop"] = "0"
    params["force-cfr"] = "1"
    # entropy coding & transform
    params["cabac"] = "1" if pps.entropy_coding_mode else "0"
    if sps.profile_idc >= 100:
        params["8x8dct"] = "1" if pps.transform_8x8_mode else "0"
    # B-frames: composition shift available in the master
    shift_frames = video.cts0 // video.frame_duration if video.cts0 % video.frame_duration == 0 else 0
    reorder = sps.vui.max_num_reorder_frames if (sps.vui and sps.vui.bitstream_restriction) else video.max_reorder_delay
    allowed = min(shift_frames, reorder if reorder is not None else 0, video.max_reorder_delay or 0)
    if sps.profile_idc == 66:
        allowed = 0
    if allowed >= 2:
        params["bframes"] = "3"
        params["b-pyramid"] = "normal"
    elif allowed == 1:
        params["bframes"] = "3"
        params["b-pyramid"] = "none"
    else:
        params["bframes"] = "0"
    # references
    refs = max(1, min(sps.max_num_ref_frames or 1, 4))
    params["ref"] = str(refs)
    # keyframe interval similar to master GOP so long patches stay seekable
    gl = video.gop_lengths()
    keyint = int(sorted(gl)[len(gl) // 2]) if gl else 250
    keyint = max(1, min(keyint, 600))
    params["keyint"] = str(keyint)
    params["min-keyint"] = str(max(1, min(keyint, keyint // 4 or 1)))
    if keyint == 1:
        params["bframes"] = "0"
    # VUI
    color_args: List[str] = []
    vui = sps.vui
    if vui and vui.colour_description_present:
        params["colorprim"] = COLORPRIM.get(vui.colour_primaries, "undef")
        params["transfer"] = TRANSFER.get(vui.transfer_characteristics, "undef")
        params["colormatrix"] = COLORMATRIX.get(vui.matrix_coefficients, "undef")
        if vui.colour_primaries in FF_PRIM:
            color_args += ["-color_primaries", FF_PRIM[vui.colour_primaries]]
        if vui.transfer_characteristics in FF_TRC:
            color_args += ["-color_trc", FF_TRC[vui.transfer_characteristics]]
        if vui.matrix_coefficients in FF_MATRIX:
            color_args += ["-colorspace", FF_MATRIX[vui.matrix_coefficients]]
    else:
        color_args += ["-color_primaries", "unknown", "-color_trc", "unknown", "-colorspace", "unknown"]
        params["colorprim"] = "undef"
        params["transfer"] = "undef"
        params["colormatrix"] = "undef"
    full = bool(vui and vui.full_range)
    params["range"] = "pc" if full else "tv"
    color_args += ["-color_range", "pc" if full else "tv"]
    if vui and vui.video_signal_type_present and vui.video_format is not None and vui.video_format != 5:
        fmt = {0: "component", 1: "pal", 2: "ntsc", 3: "secam", 4: "mac"}.get(vui.video_format)
        if fmt:
            params["videoformat"] = fmt
    # NB: "w/h" form - a ':' would be taken as FFmpeg's option separator and
    # silently swallow the following x264 option.
    if vui and vui.sar:
        params["sar"] = f"{vui.sar[0]}/{vui.sar[1]}"
    else:
        params["sar"] = "1/1"
    if vui and vui.chroma_loc_present and vui.chroma_loc_top is not None:
        params["chromaloc"] = str(vui.chroma_loc_top)
    if vui and vui.overscan_info_present:
        params["overscan"] = "show" if vui.overscan_appropriate else "crop"
    if vui and vui.nal_hrd:
        notes.append("master signals NAL HRD parameters; patch uses VBV without HRD signalling")
    # VBV: conform to the declared level - unless the master itself already
    # exceeds it, in which case the patch may use up to 1.25x the master's own
    # measured peak (never lower the quality below the master's).
    limits = h264.LEVEL_LIMITS.get(sps.level_idc)
    factor = h264.profile_bitrate_factor(sps.profile_idc)
    peak = peak_bitrate_kbps(video)
    if limits:
        maxrate = int(limits[3] * factor * 0.95)
        bufsize = int(limits[4] * factor * 0.95)
        if peak * 1.25 > maxrate:
            notes.append(f"master peak bitrate {peak} kbit/s exceeds its declared level {sps.level_str} "
                         f"({maxrate} kbit/s); patch VBV matched to 1.25x the master's peak instead")
            maxrate = int(peak * 1.25)
            bufsize = max(bufsize, maxrate)
        params["vbv-maxrate"] = str(maxrate)
        params["vbv-bufsize"] = str(bufsize)
    else:
        notes.append(f"unknown level_idc {sps.level_idc}: no VBV cap applied")
    if threads:
        params["threads"] = str(threads)
    crf: Optional[float] = {"transparent": 12.0, "high": 16.0, "balanced": 19.0}.get(quality)
    bitrate = None
    two_pass = False
    if quality == "match":
        if not local_bitrate_kbps:
            raise EncodeError("match-bitrate mode needs the master's local bitrate")
        crf = None
        bitrate = int(local_bitrate_kbps * 1.15)
        two_pass = True
    elif crf is None:
        raise EncodeError(f"unknown quality setting '{quality}'")
    fps = f"{video.fps.numerator}/{video.fps.denominator}"
    vf_extra = []
    return EncoderSettings(profile=prof, level=level, pix_fmt=sps.pix_fmt, fps=fps, sps_id=sid,
                           x264_params=params, preset=preset, crf=crf, bitrate_kbps=bitrate,
                           two_pass=two_pass, color_args=color_args, vf_extra=vf_extra,
                           threads=threads, notes=notes)


def retime_filters(fps: str) -> List[str]:
    """Give frames perfect consecutive timestamps in a 1/fps time base so the
    CFR output stage can neither duplicate nor drop frames."""
    num, den = fps.split("/") if "/" in fps else (fps, "1")
    return [f"settb=expr={den}/{num}", "setpts=N"]


def cfr_output_args(fps: str) -> List[str]:
    from .ffmpeg import supports_fps_mode
    return (["-fps_mode", "cfr"] if supports_fps_mode() else ["-vsync", "cfr"]) + ["-r", fps]


def x264_param_string(params: Dict[str, str]) -> str:
    for k, v in params.items():
        if ":" in str(v) or ":" in k:
            raise EncodeError(f"x264 parameter {k}={v} contains ':' (would be mis-parsed by FFmpeg)")
    return ":".join(f"{k}={v}" for k, v in params.items())


_X264_KEYS = {  # our param -> key in x264's SEI options string
    "bframes": "bframes", "keyint": "keyint", "min-keyint": "keyint_min", "ref": "ref", "cabac": "cabac",
    "8x8dct": "8x8dct", "vbv-maxrate": "vbv_maxrate", "vbv-bufsize": "vbv_bufsize", "open-gop": "open_gop",
}


def check_applied_params(requested: Dict[str, str], applied: Optional[dict]) -> List[dict]:
    """Compare requested x264 settings with those x264 reports it used."""
    out = []
    if applied is None:
        return [{"field": "x264_sei", "master": "present", "patch": "missing", "ok": False,
                 "severity": "warning"}]
    for ours, key in _X264_KEYS.items():
        if ours not in requested or key not in applied:
            continue
        want = str(requested[ours])
        got = str(applied[key])
        same = want == got
        if ours in ("ref",):
            same = int(got) <= int(want)          # x264 may lower refs to satisfy level/DPB limits
        if ours == "min-keyint":
            same = int(got) <= int(want)          # x264 clamps keyint_min to keyint/2+1
        out.append({"field": f"x264.{key}", "master": want, "patch": got, "ok": same,
                    "severity": "error" if ours in ("bframes", "keyint", "vbv-maxrate", "vbv-bufsize", "cabac",
                                                    "open-gop") else "warning"})
    pyr = {"none": "0", "strict": "1", "normal": "2"}
    if "b-pyramid" in requested and "b_pyramid" in applied and requested.get("bframes", "0") != "0":
        want = pyr.get(requested["b-pyramid"], requested["b-pyramid"])
        out.append({"field": "x264.b_pyramid", "master": want, "patch": applied["b_pyramid"],
                    "ok": want == applied["b_pyramid"], "severity": "error"})
    return out


def input_conversion_filter(src_pix_fmt: str, src_range: Optional[str], settings: EncoderSettings,
                            video: VideoAnalysis) -> List[str]:
    """Filters converting the intermediate render to the master's pixel layout."""
    sps = video.active_sps()
    full = bool(sps.vui and sps.vui.full_range)
    out_range = "pc" if full else "tv"
    filters = []
    is_rgb = src_pix_fmt.startswith(("rgb", "bgr", "gbr", "argb", "abgr", "rgba", "bgra"))
    if is_rgb:
        matrix = FF_MATRIX.get(sps.vui.matrix_coefficients if sps.vui and sps.vui.matrix_coefficients else 1, "bt709")
        if matrix not in ("bt709", "bt470bg", "smpte170m", "bt2020nc", "fcc", "smpte240m"):
            matrix = "bt709"
        filters.append(f"scale=out_color_matrix={matrix}:out_range={'full' if full else 'limited'}")
    else:
        in_range = src_range if src_range in ("tv", "pc") else "tv"
        if in_range != out_range:
            filters.append(f"scale=in_range={'full' if in_range == 'pc' else 'limited'}:"
                           f"out_range={'full' if full else 'limited'}")
    filters.append(f"format={settings.pix_fmt}")
    return filters


def encode_segment(render_path: str, render_first_frame: int, seg_first_frame: int, seg_end_frame: int,
                   settings: EncoderSettings, video: VideoAnalysis, out_path: str, workdir: str,
                   src_pix_fmt: str, src_range: Optional[str], cancel: Optional[CancelToken] = None,
                   log=None, progress=None) -> str:
    """Encode timeline frames [seg_first, seg_end) taken from a render that starts at render_first."""
    start = seg_first_frame - render_first_frame
    end = seg_end_frame - render_first_frame
    if start < 0:
        raise EncodeError("render does not cover the start of the segment")
    nframes = end - start
    vf = [f"trim=start_frame={start}:end_frame={end}", *retime_filters(settings.fps)]
    vf += input_conversion_filter(src_pix_fmt, src_range, settings, video)
    vf += settings.vf_extra
    base = [ffmpeg(), "-hide_banner", "-nostdin", "-y", "-v", "error", "-i", render_path,
            "-map", "0:v:0", "-an", "-sn", "-dn", "-vf", ",".join(vf), *cfr_output_args(settings.fps),
            "-c:v", "libx264", "-preset", settings.preset,
            "-profile:v", settings.profile, "-level", settings.level, *settings.color_args,
            "-x264-params", x264_param_string(settings.x264_params)]
    if settings.threads:
        base += ["-threads", str(settings.threads)]

    def _prog(d):
        if progress and "frame" in d:
            try:
                progress(min(1.0, int(d["frame"]) / max(1, nframes)))
            except ValueError:
                pass

    if settings.two_pass:
        passlog = os.path.join(workdir, "x264pass")
        rate = ["-b:v", f"{settings.bitrate_kbps}k"]
        run(base + rate + ["-pass", "1", "-passlogfile", passlog, "-f", "mp4", os.devnull],
            cancel=cancel, log=log)
        run(base + rate + ["-pass", "2", "-passlogfile", passlog, "-progress", "pipe:1", out_path],
            cancel=cancel, log=log, progress=_prog)
    else:
        run(base + ["-crf", str(settings.crf), "-progress", "pipe:1", out_path], cancel=cancel, log=log,
            progress=_prog)
    return out_path


@dataclass
class PatchInfo:
    path: str
    movie: Movie
    frame_count: int
    disp_of_dec: List[int]
    is_idr: List[bool]
    sps: List[h264.SPS]
    pps: List[h264.PPS]
    avcc: h264.AvcConfig
    compatibility: List[dict]
    max_delay: int


def _eff(v, default):
    return default if v is None else v


def compare_sps(master: h264.SPS, patch: h264.SPS) -> List[dict]:
    out = []

    def chk(name, a, b, severity="error"):
        out.append({"field": name, "master": a, "patch": b, "ok": a == b, "severity": severity})

    chk("profile_idc", master.profile_idc, patch.profile_idc)
    chk("level_idc", master.level_idc, patch.level_idc, "warning")
    chk("chroma_format_idc", master.chroma_format_idc, patch.chroma_format_idc)
    chk("bit_depth_luma", master.bit_depth_luma, patch.bit_depth_luma)
    chk("bit_depth_chroma", master.bit_depth_chroma, patch.bit_depth_chroma)
    chk("width", master.width, patch.width)
    chk("height", master.height, patch.height)
    chk("frame_mbs_only", master.frame_mbs_only, patch.frame_mbs_only)
    mv, pv = master.vui, patch.vui
    chk("full_range", bool(mv and mv.full_range), bool(pv and pv.full_range))
    chk("colour_primaries", _eff(mv and mv.colour_primaries, 2), _eff(pv and pv.colour_primaries, 2))
    chk("transfer_characteristics", _eff(mv and mv.transfer_characteristics, 2),
        _eff(pv and pv.transfer_characteristics, 2))
    chk("matrix_coefficients", _eff(mv and mv.matrix_coefficients, 2), _eff(pv and pv.matrix_coefficients, 2))
    chk("sar", tuple(_eff(mv and mv.sar, (1, 1))), tuple(_eff(pv and pv.sar, (1, 1))))
    chk("chroma_sample_loc", _eff(mv and mv.chroma_loc_top, 0), _eff(pv and pv.chroma_loc_top, 0), "warning")
    mr = mv.max_num_reorder_frames if (mv and mv.bitstream_restriction) else None
    pr = pv.max_num_reorder_frames if (pv and pv.bitstream_restriction) else None
    if mr is not None and pr is not None:
        out.append({"field": "max_num_reorder_frames", "master": mr, "patch": pr, "ok": pr <= mr,
                    "severity": "error"})
    if mv and mv.timing_info_present and pv and pv.timing_info_present:
        mf = Fraction(mv.time_scale, 2 * mv.num_units_in_tick) if mv.num_units_in_tick else None
        pf = Fraction(pv.time_scale, 2 * pv.num_units_in_tick) if pv.num_units_in_tick else None
        out.append({"field": "vui_frame_rate", "master": str(mf), "patch": str(pf), "ok": mf == pf,
                    "severity": "warning"})
    return out


def validate_patch(path: str, video: VideoAnalysis, expected_frames: int, sps_id: int,
                   requested: Optional[Dict[str, str]] = None) -> PatchInfo:
    from .media import _scan_nals  # reuse NAL scanner
    mv = read_movie(path)
    vts = mv.track_by_handler("vide")
    if len(vts) != 1:
        raise EncodeError("patch file must contain exactly one video track")
    t = vts[0]
    n = t.sample_count
    if n != expected_frames:
        raise EncodeError(f"patch has {n} frames, expected {expected_frames}")
    avcc = h264.AvcConfig.parse(avcc_from_entry(t.stsd_entries[0]))
    order = sorted(range(n), key=lambda i: t.cts(i))
    disp = [0] * n
    for k, d in enumerate(order):
        disp[d] = k
    dur = t.durations[0]
    for k, d in enumerate(order):
        if t.cts(d) != t.cts(order[0]) + k * dur:
            raise EncodeError("patch timestamps are not constant frame rate")
    is_idr = [False] * n
    sps_raw = list(avcc.sps)
    pps_raw = list(avcc.pps)
    applied = None
    with open(path, "rb") as f:
        for i in range(n):
            nals = _scan_nals(f, t.offsets[i], t.sizes[i], avcc.length_size)
            if i == 0:
                for nal in nals:
                    if h264.nal_type(nal) == h264.NAL_SEI:
                        applied = applied or h264.x264_options(nal)
            info = h264.analyze_access_unit(nals)
            is_idr[i] = info.is_idr
            for s in info.inband_sps:
                if s not in sps_raw:
                    sps_raw.append(s)
            for p in info.inband_pps:
                if p not in pps_raw:
                    pps_raw.append(p)
            if info.pps_id != sps_id:
                raise EncodeError(f"patch frame {i} references PPS {info.pps_id}, expected {sps_id}")
    if not is_idr[0] or disp[0] != 0:
        raise EncodeError("patch does not start with an IDR frame in display position 0")
    if len(sps_raw) != 1 or len(pps_raw) != 1:
        raise EncodeError("patch must contain exactly one SPS and one PPS")
    sps = [h264.parse_sps(s) for s in sps_raw]
    pps = [h264.parse_pps(p, sps[0].chroma_format_idc) for p in pps_raw]
    if sps[0].sps_id != sps_id or pps[0].pps_id != sps_id or pps[0].sps_id != sps_id:
        raise EncodeError("patch parameter-set ids do not match the allocated id")
    compat = compare_sps(video.active_sps(), sps[0])
    if requested is not None:
        compat += check_applied_params(requested, applied)
    max_delay = max((j - disp[j] for j in range(n)), default=0)
    return PatchInfo(path=path, movie=mv, frame_count=n, disp_of_dec=disp, is_idr=is_idr, sps=sps, pps=pps,
                     avcc=avcc, compatibility=compat, max_delay=max_delay)
