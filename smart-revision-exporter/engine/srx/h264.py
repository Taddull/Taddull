"""H.264 / AVC bitstream structures needed for splice-safe patching.

Parses sequence/picture parameter sets (ITU-T H.264 7.3.2.1 / 7.3.2.2), the
leading fields of slice headers (7.3.3), SEI payload types and the ISO/IEC
14496-15 AVCDecoderConfigurationRecord ('avcC').

Only fields that the patch engine needs for compatibility checks are kept, but
SPS parsing is complete (including scaling lists, VUI and HRD) because later
fields can only be reached by parsing all earlier ones.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field, asdict
from typing import Iterator, List, Optional, Tuple

from .bitio import BitReader, BitstreamError, nal_to_rbsp

# NAL unit types
NAL_SLICE = 1
NAL_DPA = 2
NAL_IDR = 5
NAL_SEI = 6
NAL_SPS = 7
NAL_PPS = 8
NAL_AUD = 9
NAL_END_SEQ = 10
NAL_END_STREAM = 11
NAL_FILLER = 12
NAL_SPS_EXT = 13
NAL_PREFIX = 14
NAL_SUBSET_SPS = 15

SLICE_TYPES = {0: "P", 1: "B", 2: "I", 3: "SP", 4: "SI"}

HIGH_PROFILES = {100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135}

PROFILE_NAMES = {
    66: "Baseline",
    77: "Main",
    88: "Extended",
    100: "High",
    110: "High 10",
    122: "High 4:2:2",
    244: "High 4:4:4 Predictive",
    44: "CAVLC 4:4:4 Intra",
}

SAR_TABLE = {
    1: (1, 1), 2: (12, 11), 3: (10, 11), 4: (16, 11), 5: (40, 33), 6: (24, 11),
    7: (20, 11), 8: (32, 11), 9: (80, 33), 10: (18, 11), 11: (15, 11),
    12: (64, 33), 13: (160, 99), 14: (4, 3), 15: (3, 2), 16: (2, 1),
}

# Level limits (Table A-1): level_idc -> (MaxMBPS, MaxFS, MaxDpbMbs, MaxBR kbit/s, MaxCPB kbit)
LEVEL_LIMITS = {
    10: (1485, 99, 396, 64, 175),
    9: (1485, 99, 396, 128, 350),  # level 1b
    11: (3000, 396, 900, 192, 500),
    12: (6000, 396, 2376, 384, 1000),
    13: (11880, 396, 2376, 768, 2000),
    20: (11880, 396, 2376, 2000, 2000),
    21: (19800, 792, 4752, 4000, 4000),
    22: (20250, 1620, 8100, 4000, 4000),
    30: (40500, 1620, 8100, 10000, 10000),
    31: (108000, 3600, 18000, 14000, 14000),
    32: (216000, 5120, 20480, 20000, 20000),
    40: (245760, 8192, 32768, 20000, 25000),
    41: (245760, 8192, 32768, 50000, 62500),
    42: (522240, 8704, 34816, 50000, 62500),
    50: (589824, 22080, 110400, 135000, 135000),
    51: (983040, 36864, 184320, 240000, 240000),
    52: (2073600, 36864, 184320, 240000, 240000),
    60: (4177920, 139264, 696320, 240000, 240000),
    61: (8355840, 139264, 696320, 480000, 480000),
    62: (16711680, 139264, 696320, 800000, 800000),
}


def profile_bitrate_factor(profile_idc: int) -> float:
    """cpbBrVclFactor/1000 relative to Baseline/Main (Table A-2)."""
    if profile_idc == 100:
        return 1.25
    if profile_idc == 110:
        return 3.0
    if profile_idc in (122, 244, 44):
        return 4.0
    return 1.0


def nal_type(nal: bytes) -> int:
    return nal[0] & 0x1F


def nal_ref_idc(nal: bytes) -> int:
    return (nal[0] >> 5) & 0x3


def iter_length_prefixed(data: bytes, length_size: int) -> Iterator[bytes]:
    pos = 0
    n = len(data)
    while pos + length_size <= n:
        size = int.from_bytes(data[pos:pos + length_size], "big")
        pos += length_size
        if size == 0 or pos + size > n:
            raise BitstreamError(f"invalid NAL length {size} at {pos} (sample size {n})")
        yield data[pos:pos + size]
        pos += size
    if pos != n:
        raise BitstreamError("trailing bytes after last NAL unit")


def iter_annexb(data: bytes) -> Iterator[bytes]:
    """Split an Annex-B byte stream into NAL units (without start codes)."""
    i = 0
    n = len(data)
    starts = []
    while i < n - 2:
        if data[i] == 0 and data[i + 1] == 0 and data[i + 2] == 1:
            starts.append(i + 3)
            i += 3
        else:
            i += 1
    for idx, s in enumerate(starts):
        e = starts[idx + 1] - 3 if idx + 1 < len(starts) else n
        nal = data[s:e]
        # strip trailing zero bytes (part of next start code / trailing_zero_8bits)
        nal = nal.rstrip(b"\x00") if idx + 1 < len(starts) else nal
        if nal:
            yield nal


@dataclass
class VUI:
    aspect_ratio_idc: Optional[int] = None
    sar: Optional[Tuple[int, int]] = None
    overscan_info_present: bool = False
    overscan_appropriate: Optional[bool] = None
    video_signal_type_present: bool = False
    video_format: Optional[int] = None
    full_range: Optional[bool] = None
    colour_description_present: bool = False
    colour_primaries: Optional[int] = None
    transfer_characteristics: Optional[int] = None
    matrix_coefficients: Optional[int] = None
    chroma_loc_present: bool = False
    chroma_loc_top: Optional[int] = None
    chroma_loc_bottom: Optional[int] = None
    timing_info_present: bool = False
    num_units_in_tick: Optional[int] = None
    time_scale: Optional[int] = None
    fixed_frame_rate: Optional[bool] = None
    nal_hrd: bool = False
    vcl_hrd: bool = False
    nal_hrd_bitrate: Optional[int] = None
    nal_hrd_cpb_size: Optional[int] = None
    nal_hrd_cbr: Optional[bool] = None
    low_delay_hrd: Optional[bool] = None
    pic_struct_present: bool = False
    bitstream_restriction: bool = False
    max_num_reorder_frames: Optional[int] = None
    max_dec_frame_buffering: Optional[int] = None


@dataclass
class SPS:
    raw: bytes
    profile_idc: int
    constraint_flags: int
    level_idc: int
    sps_id: int
    chroma_format_idc: int = 1
    separate_colour_plane: bool = False
    bit_depth_luma: int = 8
    bit_depth_chroma: int = 8
    transform_bypass: bool = False
    scaling_matrix_present: bool = False
    log2_max_frame_num: int = 4
    poc_type: int = 0
    log2_max_poc_lsb: Optional[int] = None
    max_num_ref_frames: int = 0
    gaps_in_frame_num_allowed: bool = False
    width_mbs: int = 0
    height_map_units: int = 0
    frame_mbs_only: bool = True
    mbaff: bool = False
    direct_8x8_inference: bool = True
    crop: Tuple[int, int, int, int] = (0, 0, 0, 0)
    vui: Optional[VUI] = None

    @property
    def coded_width(self) -> int:
        return self.width_mbs * 16

    @property
    def coded_height(self) -> int:
        return self.height_map_units * 16 * (1 if self.frame_mbs_only else 2)

    def _crop_units(self) -> Tuple[int, int]:
        if self.chroma_format_idc == 0 or self.separate_colour_plane:
            cx, cy = 1, 1
        elif self.chroma_format_idc == 1:
            cx, cy = 2, 2
        elif self.chroma_format_idc == 2:
            cx, cy = 2, 1
        else:
            cx, cy = 1, 1
        return cx, cy * (2 - (1 if self.frame_mbs_only else 0))

    @property
    def width(self) -> int:
        cx, _ = self._crop_units()
        return self.coded_width - cx * (self.crop[0] + self.crop[1])

    @property
    def height(self) -> int:
        _, cy = self._crop_units()
        return self.coded_height - cy * (self.crop[2] + self.crop[3])

    @property
    def profile_name(self) -> str:
        name = PROFILE_NAMES.get(self.profile_idc, f"profile {self.profile_idc}")
        if self.profile_idc == 66 and self.constraint_flags & 0x40:
            name = "Constrained Baseline"
        return name

    @property
    def level_str(self) -> str:
        if self.level_idc == 11 and self.constraint_flags & 0x10 and self.profile_idc in (66, 77, 88):
            return "1b"
        if self.level_idc == 9:
            return "1b"
        return f"{self.level_idc // 10}.{self.level_idc % 10}"

    @property
    def pix_fmt(self) -> str:
        depth = self.bit_depth_luma
        base = {0: "gray", 1: "yuv420p", 2: "yuv422p", 3: "yuv444p"}[self.chroma_format_idc]
        if depth == 8:
            return base if base != "gray" else "gray"
        if base == "gray":
            return f"gray{depth}le"
        return f"{base}{depth}le"

    def summary(self) -> dict:
        d = {
            "sps_id": self.sps_id,
            "profile": self.profile_name,
            "profile_idc": self.profile_idc,
            "constraint_flags": self.constraint_flags,
            "level": self.level_str,
            "level_idc": self.level_idc,
            "chroma_format_idc": self.chroma_format_idc,
            "bit_depth": self.bit_depth_luma,
            "width": self.width,
            "height": self.height,
            "frame_mbs_only": self.frame_mbs_only,
            "poc_type": self.poc_type,
            "max_num_ref_frames": self.max_num_ref_frames,
            "pix_fmt": self.pix_fmt,
        }
        if self.vui:
            d["vui"] = {k: v for k, v in asdict(self.vui).items() if v not in (None, False)}
        return d


def _skip_scaling_list(r: BitReader, size: int) -> None:
    last = 8
    nxt = 8
    for _ in range(size):
        if nxt != 0:
            delta = r.se()
            nxt = (last + delta + 256) % 256
        last = nxt if nxt != 0 else last


def _parse_hrd(r: BitReader, vui: VUI, nal: bool) -> None:
    cpb_cnt = r.ue() + 1
    bit_rate_scale = r.u(4)
    cpb_size_scale = r.u(4)
    for i in range(cpb_cnt):
        br = r.ue() + 1
        cs = r.ue() + 1
        cbr = r.flag()
        if nal and i == 0:
            vui.nal_hrd_bitrate = br << (6 + bit_rate_scale)
            vui.nal_hrd_cpb_size = cs << (4 + cpb_size_scale)
            vui.nal_hrd_cbr = cbr
    r.u(5)
    r.u(5)
    r.u(5)
    r.u(5)


def _parse_vui(r: BitReader) -> VUI:
    v = VUI()
    if r.flag():
        idc = r.u(8)
        v.aspect_ratio_idc = idc
        if idc == 255:
            v.sar = (r.u(16), r.u(16))
        else:
            v.sar = SAR_TABLE.get(idc)
    if r.flag():
        v.overscan_info_present = True
        v.overscan_appropriate = r.flag()
    if r.flag():
        v.video_signal_type_present = True
        v.video_format = r.u(3)
        v.full_range = r.flag()
        if r.flag():
            v.colour_description_present = True
            v.colour_primaries = r.u(8)
            v.transfer_characteristics = r.u(8)
            v.matrix_coefficients = r.u(8)
    if r.flag():
        v.chroma_loc_present = True
        v.chroma_loc_top = r.ue()
        v.chroma_loc_bottom = r.ue()
    if r.flag():
        v.timing_info_present = True
        v.num_units_in_tick = r.u(32)
        v.time_scale = r.u(32)
        v.fixed_frame_rate = r.flag()
    v.nal_hrd = r.flag()
    if v.nal_hrd:
        _parse_hrd(r, v, True)
    v.vcl_hrd = r.flag()
    if v.vcl_hrd:
        _parse_hrd(r, v, False)
    if v.nal_hrd or v.vcl_hrd:
        v.low_delay_hrd = r.flag()
    v.pic_struct_present = r.flag()
    v.bitstream_restriction = r.flag()
    if v.bitstream_restriction:
        r.flag()
        r.ue()
        r.ue()
        r.ue()
        r.ue()
        v.max_num_reorder_frames = r.ue()
        v.max_dec_frame_buffering = r.ue()
    return v


def parse_sps(nal: bytes) -> SPS:
    if nal_type(nal) != NAL_SPS:
        raise BitstreamError("not an SPS NAL unit")
    rbsp = nal_to_rbsp(nal[1:])
    r = BitReader(rbsp)
    profile_idc = r.u(8)
    constraint = r.u(8)
    level_idc = r.u(8)
    sps = SPS(raw=bytes(nal), profile_idc=profile_idc, constraint_flags=constraint,
              level_idc=level_idc, sps_id=r.ue())
    if profile_idc in HIGH_PROFILES:
        sps.chroma_format_idc = r.ue()
        if sps.chroma_format_idc == 3:
            sps.separate_colour_plane = r.flag()
        sps.bit_depth_luma = r.ue() + 8
        sps.bit_depth_chroma = r.ue() + 8
        sps.transform_bypass = r.flag()
        sps.scaling_matrix_present = r.flag()
        if sps.scaling_matrix_present:
            for i in range(8 if sps.chroma_format_idc != 3 else 12):
                if r.flag():
                    _skip_scaling_list(r, 16 if i < 6 else 64)
    sps.log2_max_frame_num = r.ue() + 4
    sps.poc_type = r.ue()
    if sps.poc_type == 0:
        sps.log2_max_poc_lsb = r.ue() + 4
    elif sps.poc_type == 1:
        r.flag()
        r.se()
        r.se()
        for _ in range(r.ue()):
            r.se()
    sps.max_num_ref_frames = r.ue()
    sps.gaps_in_frame_num_allowed = r.flag()
    sps.width_mbs = r.ue() + 1
    sps.height_map_units = r.ue() + 1
    sps.frame_mbs_only = r.flag()
    if not sps.frame_mbs_only:
        sps.mbaff = r.flag()
    sps.direct_8x8_inference = r.flag()
    if r.flag():
        sps.crop = (r.ue(), r.ue(), r.ue(), r.ue())
    if r.flag():
        sps.vui = _parse_vui(r)
    return sps


@dataclass
class PPS:
    raw: bytes
    pps_id: int
    sps_id: int
    entropy_coding_mode: bool
    bottom_field_pic_order_present: bool
    num_slice_groups: int
    num_ref_idx_l0_default: int = 1
    num_ref_idx_l1_default: int = 1
    weighted_pred: bool = False
    weighted_bipred_idc: int = 0
    pic_init_qp: int = 26
    chroma_qp_index_offset: int = 0
    deblocking_filter_control_present: bool = False
    constrained_intra_pred: bool = False
    redundant_pic_cnt_present: bool = False
    transform_8x8_mode: bool = False
    pic_scaling_matrix_present: bool = False
    second_chroma_qp_index_offset: int = 0

    def summary(self) -> dict:
        d = asdict(self)
        d.pop("raw")
        return d


def parse_pps(nal: bytes, chroma_format_idc: int = 1) -> PPS:
    if nal_type(nal) != NAL_PPS:
        raise BitstreamError("not a PPS NAL unit")
    r = BitReader(nal_to_rbsp(nal[1:]))
    pps = PPS(raw=bytes(nal), pps_id=r.ue(), sps_id=r.ue(), entropy_coding_mode=r.flag(),
              bottom_field_pic_order_present=r.flag(), num_slice_groups=r.ue() + 1)
    if pps.num_slice_groups > 1:
        # Slice groups (FMO) only exist in Baseline/Extended; we do not need the
        # remaining fields for splicing and FMO streams are rejected upstream.
        return pps
    pps.num_ref_idx_l0_default = r.ue() + 1
    pps.num_ref_idx_l1_default = r.ue() + 1
    pps.weighted_pred = r.flag()
    pps.weighted_bipred_idc = r.u(2)
    pps.pic_init_qp = 26 + r.se()
    r.se()  # pic_init_qs
    pps.chroma_qp_index_offset = r.se()
    pps.deblocking_filter_control_present = r.flag()
    pps.constrained_intra_pred = r.flag()
    pps.redundant_pic_cnt_present = r.flag()
    pps.second_chroma_qp_index_offset = pps.chroma_qp_index_offset
    if r.more_rbsp_data():
        pps.transform_8x8_mode = r.flag()
        pps.pic_scaling_matrix_present = r.flag()
        if pps.pic_scaling_matrix_present:
            n = 6 + ((2 if chroma_format_idc != 3 else 6) if pps.transform_8x8_mode else 0)
            for i in range(n):
                if r.flag():
                    _skip_scaling_list(r, 16 if i < 6 else 64)
        pps.second_chroma_qp_index_offset = r.se()
    return pps


@dataclass
class SliceHeaderPrefix:
    first_mb: int
    slice_type: int
    pps_id: int

    @property
    def type_char(self) -> str:
        return SLICE_TYPES.get(self.slice_type % 5, "?")


def parse_slice_prefix(nal: bytes) -> SliceHeaderPrefix:
    # The first three fields are within the first few bytes; read enough bytes
    # to survive possible emulation prevention bytes.
    r = BitReader(nal_to_rbsp(nal[1:24]))
    return SliceHeaderPrefix(first_mb=r.ue(), slice_type=r.ue(), pps_id=r.ue())


def sei_payload_types(nal: bytes) -> List[int]:
    """Return SEI payload types contained in an SEI NAL unit."""
    rbsp = nal_to_rbsp(nal[1:])
    types: List[int] = []
    pos = 0
    n = len(rbsp)
    while pos < n:
        if pos == n - 1 and rbsp[pos] == 0x80:
            break  # rbsp trailing bits
        ptype = 0
        while pos < n and rbsp[pos] == 0xFF:
            ptype += 255
            pos += 1
        if pos >= n:
            break
        ptype += rbsp[pos]
        pos += 1
        psize = 0
        while pos < n and rbsp[pos] == 0xFF:
            psize += 255
            pos += 1
        if pos >= n:
            break
        psize += rbsp[pos]
        pos += 1
        types.append(ptype)
        pos += psize
    return types


def sei_messages(nal: bytes) -> List[Tuple[int, bytes]]:
    """Return (payload_type, payload) for every SEI message in an SEI NAL unit."""
    rbsp = nal_to_rbsp(nal[1:])
    out: List[Tuple[int, bytes]] = []
    pos = 0
    n = len(rbsp)
    while pos < n:
        if pos == n - 1 and rbsp[pos] == 0x80:
            break
        ptype = 0
        while pos < n and rbsp[pos] == 0xFF:
            ptype += 255
            pos += 1
        if pos >= n:
            break
        ptype += rbsp[pos]
        pos += 1
        psize = 0
        while pos < n and rbsp[pos] == 0xFF:
            psize += 255
            pos += 1
        if pos >= n:
            break
        psize += rbsp[pos]
        pos += 1
        out.append((ptype, bytes(rbsp[pos:pos + psize])))
        pos += psize
    return out


def x264_options(nal: bytes) -> Optional[dict]:
    """Parse the encoder settings string libx264 stores in a user-data SEI."""
    for ptype, payload in sei_messages(nal):
        if ptype != 5 or len(payload) <= 16:
            continue
        text = payload[16:].split(b"\x00", 1)[0].decode("latin-1", "replace")
        if "x264" not in text or "options:" not in text:
            continue
        opts = {}
        for tok in text.split("options:", 1)[1].split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                opts[k] = v
        opts["_version"] = text.split(" - ")[1] if " - " in text else text[:40]
        return opts
    return None


@dataclass
class AvcConfig:
    profile: int
    compat: int
    level: int
    length_size: int
    sps: List[bytes] = field(default_factory=list)
    pps: List[bytes] = field(default_factory=list)
    ext: Optional[Tuple[int, int, int, List[bytes]]] = None  # chroma, bd_luma-8, bd_chroma-8, sps_ext

    @classmethod
    def parse(cls, data: bytes) -> "AvcConfig":
        if len(data) < 7 or data[0] != 1:
            raise BitstreamError("invalid avcC record")
        cfg = cls(profile=data[1], compat=data[2], level=data[3], length_size=(data[4] & 3) + 1)
        pos = 5
        nsps = data[pos] & 0x1F
        pos += 1
        for _ in range(nsps):
            ln = struct.unpack(">H", data[pos:pos + 2])[0]
            cfg.sps.append(bytes(data[pos + 2:pos + 2 + ln]))
            pos += 2 + ln
        npps = data[pos]
        pos += 1
        for _ in range(npps):
            ln = struct.unpack(">H", data[pos:pos + 2])[0]
            cfg.pps.append(bytes(data[pos + 2:pos + 2 + ln]))
            pos += 2 + ln
        if cfg.profile in (100, 110, 122, 144) and pos + 4 <= len(data):
            chroma = data[pos] & 3
            bdl = data[pos + 1] & 7
            bdc = data[pos + 2] & 7
            n_ext = data[pos + 3]
            pos += 4
            exts = []
            for _ in range(n_ext):
                ln = struct.unpack(">H", data[pos:pos + 2])[0]
                exts.append(bytes(data[pos + 2:pos + 2 + ln]))
                pos += 2 + ln
            cfg.ext = (chroma, bdl, bdc, exts)
        return cfg

    def build(self) -> bytes:
        if len(self.sps) > 31:
            raise BitstreamError("too many SPS for avcC")
        if len(self.pps) > 255:
            raise BitstreamError("too many PPS for avcC")
        out = bytearray([1, self.profile, self.compat, self.level, 0xFC | (self.length_size - 1),
                         0xE0 | len(self.sps)])
        for s in self.sps:
            out += struct.pack(">H", len(s)) + s
        out.append(len(self.pps))
        for p in self.pps:
            out += struct.pack(">H", len(p)) + p
        if self.ext is not None:
            chroma, bdl, bdc, exts = self.ext
            out += bytes([0xFC | chroma, 0xF8 | bdl, 0xF8 | bdc, len(exts)])
            for e in exts:
                out += struct.pack(">H", len(e)) + e
        return bytes(out)

    def parsed_sps(self) -> List[SPS]:
        return [parse_sps(s) for s in self.sps]

    def parsed_pps(self) -> List[PPS]:
        sps_map = {s.sps_id: s for s in self.parsed_sps()}
        out = []
        for p in self.pps:
            # chroma format needed only for scaling lists; peek sps id first
            tmp = parse_pps(p)
            chroma = sps_map.get(tmp.sps_id).chroma_format_idc if tmp.sps_id in sps_map else 1
            out.append(parse_pps(p, chroma))
        return out


@dataclass
class SampleNalInfo:
    """Per-sample summary derived from the NAL units of one access unit."""
    nal_types: List[int]
    is_idr: bool
    slice_type: Optional[str]
    pps_id: Optional[int]
    has_recovery_point: bool
    inband_sps: List[bytes]
    inband_pps: List[bytes]
    is_reference: bool


def analyze_access_unit(nals: List[bytes]) -> SampleNalInfo:
    types = []
    is_idr = False
    slice_type = None
    pps_id = None
    recovery = False
    in_sps: List[bytes] = []
    in_pps: List[bytes] = []
    is_ref = False
    for nal in nals:
        t = nal_type(nal)
        types.append(t)
        if t in (NAL_SLICE, NAL_IDR):
            if t == NAL_IDR:
                is_idr = True
            if nal_ref_idc(nal):
                is_ref = True
            if slice_type is None:
                sh = parse_slice_prefix(nal)
                slice_type = sh.type_char
                pps_id = sh.pps_id
        elif t == NAL_SEI:
            try:
                if 6 in sei_payload_types(nal):
                    recovery = True
            except Exception:
                pass
        elif t == NAL_SPS:
            in_sps.append(bytes(nal))
        elif t == NAL_PPS:
            in_pps.append(bytes(nal))
    return SampleNalInfo(types, is_idr, slice_type, pps_id, recovery, in_sps, in_pps, is_ref)
