"""Minimal, strict ISO-BMFF (MP4/MOV) reader and writer.

The reader exposes every sample of every track (file offset, size, decode
timestamp, composition offset, sync flag, sample-description index) so the
patch engine can reuse compressed packets byte-for-byte.  The writer rebuilds
sample tables from an explicit sample list and copies sample payloads from one
or more source files, so the output timing is fully determined by the engine
instead of by a generic concat demuxer.
"""

from __future__ import annotations

import io
import os
import struct
import time
from dataclasses import dataclass, field
from typing import BinaryIO, Dict, List, Optional, Sequence, Tuple

CONTAINER_BOXES = {
    "moov", "trak", "edts", "mdia", "minf", "dinf", "stbl", "mvex", "moof", "traf", "mfra",
}


class Mp4Error(ValueError):
    pass


@dataclass
class Box:
    type: str
    offset: int
    size: int
    header_size: int
    raw: Optional[bytes] = None  # full box bytes (header + payload) when loaded
    children: Optional[List["Box"]] = None

    @property
    def payload(self) -> bytes:
        assert self.raw is not None
        return self.raw[self.header_size:]

    def child(self, typ: str) -> Optional["Box"]:
        for c in self.children or []:
            if c.type == typ:
                return c
        return None

    def children_of(self, typ: str) -> List["Box"]:
        return [c for c in (self.children or []) if c.type == typ]


def _read_box_header(buf: bytes, pos: int, end: int) -> Tuple[int, str, int]:
    if pos + 8 > end:
        raise Mp4Error(f"truncated box header at {pos}")
    size, typ = struct.unpack(">I4s", buf[pos:pos + 8])
    hdr = 8
    if size == 1:
        size = struct.unpack(">Q", buf[pos + 8:pos + 16])[0]
        hdr = 16
    elif size == 0:
        size = end - pos
    if size < hdr or pos + size > end:
        raise Mp4Error(f"invalid box size {size} for '{typ!r}' at {pos}")
    return size, typ.decode("latin-1"), hdr


def parse_boxes(buf: bytes, start: int, end: int, base_offset: int = 0) -> List[Box]:
    boxes = []
    pos = start
    while pos < end:
        if end - pos < 8:
            # Some writers pad with zero bytes; tolerate trailing zeros only.
            if any(buf[pos:end]):
                raise Mp4Error("garbage after last box")
            break
        size, typ, hdr = _read_box_header(buf, pos, end)
        raw = bytes(buf[pos:pos + size])
        box = Box(typ, base_offset + pos, size, hdr, raw)
        if typ in CONTAINER_BOXES:
            box.children = parse_boxes(raw, hdr, size, base_offset + pos)
        boxes.append(box)
        pos += size
    return boxes


def scan_top_level(f: BinaryIO) -> List[Box]:
    """Scan top-level boxes, loading everything except media data."""
    f.seek(0, os.SEEK_END)
    file_size = f.tell()
    f.seek(0)
    boxes = []
    pos = 0
    while pos < file_size:
        f.seek(pos)
        hdr = f.read(16)
        if len(hdr) < 8:
            break
        size, typ = struct.unpack(">I4s", hdr[:8])
        hsize = 8
        if size == 1:
            size = struct.unpack(">Q", hdr[8:16])[0]
            hsize = 16
        elif size == 0:
            size = file_size - pos
        t = typ.decode("latin-1")
        if size < hsize or pos + size > file_size:
            raise Mp4Error(f"invalid top-level box '{t}' size {size} at {pos} (file size {file_size})")
        if t in ("mdat", "free", "skip", "wide"):
            boxes.append(Box(t, pos, size, hsize, None))
        else:
            f.seek(pos)
            raw = f.read(size)
            box = Box(t, pos, size, hsize, raw)
            if t in CONTAINER_BOXES:
                box.children = parse_boxes(raw, hsize, size, pos)
            boxes.append(box)
        pos += size
    return boxes


def fullbox_vf(payload: bytes) -> Tuple[int, int]:
    return payload[0], int.from_bytes(payload[1:4], "big")


@dataclass
class EditEntry:
    segment_duration: int  # in movie timescale
    media_time: int        # in media timescale, -1 = empty edit
    rate_int: int = 1
    rate_frac: int = 0


@dataclass
class Track:
    track_id: int
    handler: str
    timescale: int
    media_duration: int
    tkhd: Box
    mdhd: Box
    hdlr: Box
    trak: Box
    edits: Optional[List[EditEntry]]
    elst_version: int
    stsd_entries: List[bytes]       # raw sample entry boxes
    stsd_version_flags: bytes
    # per-sample arrays, decode order
    offsets: List[int] = field(default_factory=list)
    sizes: List[int] = field(default_factory=list)
    dts: List[int] = field(default_factory=list)
    durations: List[int] = field(default_factory=list)
    cts_offsets: List[int] = field(default_factory=list)
    sync: Optional[List[bool]] = None   # None => every sample is sync
    desc_index: List[int] = field(default_factory=list)  # 1-based
    stbl_other: List[Box] = field(default_factory=list)  # sgpd, sbgp, sdtp, ...

    @property
    def sample_count(self) -> int:
        return len(self.sizes)

    def is_sync(self, i: int) -> bool:
        return True if self.sync is None else self.sync[i]

    def cts(self, i: int) -> int:
        return self.dts[i] + self.cts_offsets[i]

    @property
    def sample_entry_type(self) -> str:
        return self.stsd_entries[0][4:8].decode("latin-1") if self.stsd_entries else ""


@dataclass
class Movie:
    path: str
    file_size: int
    ftyp: Optional[Box]
    moov: Box
    mvhd: Box
    timescale: int
    duration: int
    tracks: List[Track]
    mdat_boxes: List[Box]
    moov_before_mdat: bool
    fragmented: bool
    moov_other: List[Box]  # moov children other than mvhd/trak (udta, meta, iods...)

    def track_by_handler(self, handler: str) -> List[Track]:
        return [t for t in self.tracks if t.handler == handler]


def _parse_mvhd(box: Box) -> Tuple[int, int]:
    p = box.payload
    v, _ = fullbox_vf(p)
    if v == 1:
        timescale, duration = struct.unpack(">IQ", p[20:32])
    else:
        timescale, duration = struct.unpack(">II", p[12:20])
    return timescale, duration


def _parse_mdhd(box: Box) -> Tuple[int, int]:
    return _parse_mvhd(box)  # identical layout for timescale/duration


def _parse_tkhd_id(box: Box) -> int:
    p = box.payload
    v, _ = fullbox_vf(p)
    if v == 1:
        return struct.unpack(">I", p[20:24])[0]
    return struct.unpack(">I", p[12:16])[0]


def _parse_elst(box: Box) -> Tuple[int, List[EditEntry]]:
    p = box.payload
    v, _ = fullbox_vf(p)
    n = struct.unpack(">I", p[4:8])[0]
    out = []
    pos = 8
    for _ in range(n):
        if v == 1:
            sd, mt = struct.unpack(">Qq", p[pos:pos + 16])
            pos += 16
        else:
            sd, mt = struct.unpack(">Ii", p[pos:pos + 8])
            pos += 8
        ri, rf = struct.unpack(">hh", p[pos:pos + 4])
        pos += 4
        out.append(EditEntry(sd, mt, ri, rf))
    return v, out


def _parse_stsd(box: Box) -> Tuple[bytes, List[bytes]]:
    p = box.payload
    n = struct.unpack(">I", p[4:8])[0]
    entries = []
    pos = 8
    for _ in range(n):
        size = struct.unpack(">I", p[pos:pos + 4])[0]
        if size < 8 or pos + size > len(p):
            raise Mp4Error("invalid sample description entry")
        entries.append(bytes(p[pos:pos + size]))
        pos += size
    return bytes(p[:4]), entries


def _expand_stts(box: Box) -> List[int]:
    p = box.payload
    n = struct.unpack(">I", p[4:8])[0]
    out: List[int] = []
    for i in range(n):
        cnt, delta = struct.unpack(">II", p[8 + 8 * i:16 + 8 * i])
        out.extend([delta] * cnt)
    return out


def _expand_ctts(box: Box) -> List[int]:
    p = box.payload
    v, _ = fullbox_vf(p)
    n = struct.unpack(">I", p[4:8])[0]
    out: List[int] = []
    fmt = ">Ii" if v == 1 else ">II"
    for i in range(n):
        cnt, off = struct.unpack(fmt, p[8 + 8 * i:16 + 8 * i])
        if v == 0 and off >= 0x80000000:
            # Some writers store negative offsets in version 0 boxes.
            off -= 1 << 32
        out.extend([off] * cnt)
    return out


def _parse_stss(box: Box) -> List[int]:
    p = box.payload
    n = struct.unpack(">I", p[4:8])[0]
    return list(struct.unpack(f">{n}I", p[8:8 + 4 * n]))


def _parse_stsz(box: Box) -> List[int]:
    p = box.payload
    if box.type == "stz2":
        field_size = p[7]
        n = struct.unpack(">I", p[8:12])[0]
        data = p[12:]
        if field_size == 16:
            return list(struct.unpack(f">{n}H", data[:2 * n]))
        if field_size == 8:
            return list(data[:n])
        if field_size == 4:
            out = []
            for i in range(n):
                b = data[i // 2]
                out.append((b >> 4) if i % 2 == 0 else (b & 0xF))
            return out
        raise Mp4Error("invalid stz2 field size")
    size, n = struct.unpack(">II", p[4:12])
    if size:
        return [size] * n
    return list(struct.unpack(f">{n}I", p[12:12 + 4 * n]))


def _parse_stsc(box: Box) -> List[Tuple[int, int, int]]:
    p = box.payload
    n = struct.unpack(">I", p[4:8])[0]
    return [struct.unpack(">III", p[8 + 12 * i:20 + 12 * i]) for i in range(n)]


def _parse_stco(box: Box) -> List[int]:
    p = box.payload
    n = struct.unpack(">I", p[4:8])[0]
    if box.type == "co64":
        return list(struct.unpack(f">{n}Q", p[8:8 + 8 * n]))
    return list(struct.unpack(f">{n}I", p[8:8 + 4 * n]))


def _build_track(trak: Box) -> Track:
    tkhd = trak.child("tkhd")
    mdia = trak.child("mdia")
    if tkhd is None or mdia is None:
        raise Mp4Error("track missing tkhd/mdia")
    mdhd = mdia.child("mdhd")
    hdlr = mdia.child("hdlr")
    minf = mdia.child("minf")
    if mdhd is None or hdlr is None or minf is None:
        raise Mp4Error("track missing mdhd/hdlr/minf")
    stbl = minf.child("stbl")
    if stbl is None:
        raise Mp4Error("track missing stbl")
    timescale, mdur = _parse_mdhd(mdhd)
    handler = hdlr.payload[8:12].decode("latin-1")
    edits = None
    elst_version = 0
    edts = trak.child("edts")
    if edts is not None and edts.child("elst") is not None:
        elst_version, edits = _parse_elst(edts.child("elst"))
    stsd = stbl.child("stsd")
    if stsd is None:
        raise Mp4Error("track missing stsd")
    vf, entries = _parse_stsd(stsd)
    track = Track(track_id=_parse_tkhd_id(tkhd), handler=handler, timescale=timescale,
                  media_duration=mdur, tkhd=tkhd, mdhd=mdhd, hdlr=hdlr, trak=trak, edits=edits,
                  elst_version=elst_version, stsd_entries=entries, stsd_version_flags=vf)
    stts = stbl.child("stts")
    stsz = stbl.child("stsz") or stbl.child("stz2")
    stsc = stbl.child("stsc")
    stco = stbl.child("stco") or stbl.child("co64")
    if stts is None or stsz is None or stsc is None or stco is None:
        raise Mp4Error("track missing mandatory sample table boxes")
    durations = _expand_stts(stts)
    sizes = _parse_stsz(stsz)
    n = len(sizes)
    if len(durations) != n:
        raise Mp4Error(f"stts sample count {len(durations)} != stsz count {n}")
    ctts_box = stbl.child("ctts")
    cts_off = _expand_ctts(ctts_box) if ctts_box is not None else [0] * n
    if len(cts_off) != n:
        raise Mp4Error("ctts sample count mismatch")
    stss_box = stbl.child("stss")
    sync = None
    if stss_box is not None:
        sync = [False] * n
        for s in _parse_stss(stss_box):
            if 1 <= s <= n:
                sync[s - 1] = True
    chunk_offsets = _parse_stco(stco)
    stsc_entries = _parse_stsc(stsc)
    offsets: List[int] = []
    desc: List[int] = []
    si = 0
    for ei, (first_chunk, spc, sdi) in enumerate(stsc_entries):
        last_chunk = (stsc_entries[ei + 1][0] - 1) if ei + 1 < len(stsc_entries) else len(chunk_offsets)
        for chunk in range(first_chunk, last_chunk + 1):
            if chunk - 1 >= len(chunk_offsets):
                raise Mp4Error("stsc references chunk beyond stco")
            off = chunk_offsets[chunk - 1]
            for _ in range(spc):
                if si >= n:
                    break
                offsets.append(off)
                desc.append(sdi)
                off += sizes[si]
                si += 1
    if si != n:
        raise Mp4Error(f"stsc/stco describe {si} samples, expected {n}")
    dts = []
    t = 0
    for d in durations:
        dts.append(t)
        t += d
    track.offsets = offsets
    track.sizes = sizes
    track.dts = dts
    track.durations = durations
    track.cts_offsets = cts_off
    track.sync = sync
    track.desc_index = desc
    known = {"stsd", "stts", "ctts", "stss", "stsz", "stz2", "stsc", "stco", "co64"}
    track.stbl_other = [b for b in stbl.children or [] if b.type not in known]
    return track


def read_movie(path: str) -> Movie:
    with open(path, "rb") as f:
        boxes = scan_top_level(f)
        file_size = f.seek(0, os.SEEK_END)
    ftyp = next((b for b in boxes if b.type == "ftyp"), None)
    moov = next((b for b in boxes if b.type == "moov"), None)
    if moov is None:
        raise Mp4Error("no moov box (not a complete MP4/MOV file)")
    fragmented = any(b.type == "moof" for b in boxes) or moov.child("mvex") is not None
    mvhd = moov.child("mvhd")
    if mvhd is None:
        raise Mp4Error("no mvhd")
    ts, dur = _parse_mvhd(mvhd)
    tracks = [_build_track(t) for t in moov.children_of("trak")]
    mdats = [b for b in boxes if b.type == "mdat"]
    moov_before = bool(mdats) and moov.offset < mdats[0].offset
    others = [c for c in moov.children or [] if c.type not in ("mvhd", "trak")]
    return Movie(path=path, file_size=file_size, ftyp=ftyp, moov=moov, mvhd=mvhd, timescale=ts,
                 duration=dur, tracks=tracks, mdat_boxes=mdats, moov_before_mdat=moov_before,
                 fragmented=fragmented, moov_other=others)


# ---------------------------------------------------------------------------
# Sample entry helpers
# ---------------------------------------------------------------------------

VISUAL_SAMPLE_ENTRY_HEADER = 8 + 78


def sample_entry_children(entry: bytes) -> Tuple[int, List[Box]]:
    """Return (header_length, child boxes) for a visual or audio sample entry."""
    typ = entry[4:8].decode("latin-1")
    if typ in ("avc1", "avc3", "hvc1", "hev1", "mp4v", "apcn", "apch", "ap4h", "apcs", "apco", "ap4x"):
        hl = VISUAL_SAMPLE_ENTRY_HEADER
    elif typ in ("mp4a", "lpcm", "sowt", "twos", "ipcm", "alac", "ac-3", "ec-3"):
        version = struct.unpack(">H", entry[16:18])[0]
        hl = 8 + 28
        if version == 1:
            hl += 16
        elif version == 2:
            hl += 36
    else:
        return len(entry), []
    return hl, parse_boxes(entry, hl, len(entry))


def find_box_recursive(boxes: Sequence[Box], typ: str) -> Optional[Box]:
    for b in boxes:
        if b.type == typ:
            return b
        if b.type == "wave":  # QuickTime audio 'wave' container
            inner = parse_boxes(b.raw, b.header_size, b.size)
            r = find_box_recursive(inner, typ)
            if r:
                return r
    return None


def avcc_from_entry(entry: bytes) -> Optional[bytes]:
    _, kids = sample_entry_children(entry)
    for k in kids:
        if k.type == "avcC":
            return k.payload
    return None


def replace_child_in_entry(entry: bytes, typ: str, new_payload: Optional[bytes]) -> bytes:
    """Return a sample entry with child box `typ` replaced (or removed if None)."""
    hl, kids = sample_entry_children(entry)
    out = bytearray(entry[:hl])
    replaced = False
    for k in kids:
        if k.type == typ:
            replaced = True
            if new_payload is not None:
                out += make_box(typ, new_payload)
        else:
            out += k.raw
    if not replaced and new_payload is not None:
        out += make_box(typ, new_payload)
    struct.pack_into(">I", out, 0, len(out))
    return bytes(out)


def visual_entry_dimensions(entry: bytes) -> Tuple[int, int]:
    return struct.unpack(">HH", entry[32:36])


@dataclass
class EsdsInfo:
    object_type: int
    max_bitrate: int
    avg_bitrate: int
    buffer_size: int
    asc: bytes


def _read_desc_len(p: bytes, pos: int) -> Tuple[int, int]:
    ln = 0
    for _ in range(4):
        b = p[pos]
        pos += 1
        ln = (ln << 7) | (b & 0x7F)
        if not b & 0x80:
            break
    return ln, pos


def parse_esds(payload: bytes) -> EsdsInfo:
    p = payload[4:]  # skip version/flags
    pos = 0
    if p[pos] != 0x03:
        raise Mp4Error("esds: missing ES_Descriptor")
    _, pos = _read_desc_len(p, pos + 1)
    pos += 2  # ES_ID
    flags = p[pos]
    pos += 1
    if flags & 0x80:
        pos += 2
    if flags & 0x40:
        url_len = p[pos]
        pos += 1 + url_len
    if flags & 0x20:
        pos += 2
    if p[pos] != 0x04:
        raise Mp4Error("esds: missing DecoderConfigDescriptor")
    _, pos = _read_desc_len(p, pos + 1)
    oti = p[pos]
    buf = int.from_bytes(p[pos + 2:pos + 5], "big")
    maxbr, avgbr = struct.unpack(">II", p[pos + 5:pos + 13])
    pos += 13
    asc = b""
    if pos < len(p) and p[pos] == 0x05:
        ln, pos = _read_desc_len(p, pos + 1)
        asc = bytes(p[pos:pos + ln])
    return EsdsInfo(oti, maxbr, avgbr, buf, asc)


@dataclass
class AudioSpecificConfig:
    object_type: int
    sample_rate: int
    channel_config: int
    frame_length: int
    raw: bytes


AAC_RATES = [96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350]


def parse_asc(asc: bytes) -> AudioSpecificConfig:
    from .bitio import BitReader
    r = BitReader(asc)
    ot = r.u(5)
    if ot == 31:
        ot = 32 + r.u(6)
    idx = r.u(4)
    rate = r.u(24) if idx == 15 else AAC_RATES[idx]
    ch = r.u(4)
    frame_len = 1024
    if ot in (1, 2, 3, 4, 6, 7, 17, 19, 20, 21, 22, 23):
        if r.u(1):
            frame_len = 960
    return AudioSpecificConfig(ot, rate, ch, frame_len, bytes(asc))


def audio_entry_info(entry: bytes) -> dict:
    typ = entry[4:8].decode("latin-1")
    channels, samplesize = struct.unpack(">HH", entry[24:28])
    rate = struct.unpack(">I", entry[32:36])[0] >> 16
    info = {"entry_type": typ, "channels": channels, "sample_size": samplesize, "rate": rate}
    if typ == "mp4a":
        _, kids = sample_entry_children(entry)
        esds = find_box_recursive(kids, "esds")
        if esds is not None:
            e = parse_esds(esds.payload)
            info["object_type_indication"] = e.object_type
            info["avg_bitrate"] = e.avg_bitrate
            info["max_bitrate"] = e.max_bitrate
            if e.asc:
                a = parse_asc(e.asc)
                info.update(aac_object_type=a.object_type, sample_rate=a.sample_rate,
                            channel_config=a.channel_config, frame_length=a.frame_length,
                            asc_hex=a.raw.hex())
    return info


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def make_box(typ: str, payload: bytes) -> bytes:
    size = 8 + len(payload)
    if size > 0xFFFFFFFF:
        return struct.pack(">I4sQ", 1, typ.encode("latin-1"), size + 8) + payload
    return struct.pack(">I4s", size, typ.encode("latin-1")) + payload


def make_fullbox(typ: str, version: int, flags: int, payload: bytes) -> bytes:
    return make_box(typ, bytes([version]) + flags.to_bytes(3, "big") + payload)


def _set_duration(box_raw: bytes, header_size: int, kind: str, duration: int) -> bytes:
    """Patch the duration field of mvhd/mdhd/tkhd (keeps version)."""
    b = bytearray(box_raw)
    p0 = header_size
    v = b[p0]
    if kind in ("mvhd", "mdhd"):
        if v == 1:
            struct.pack_into(">Q", b, p0 + 24, duration)
        else:
            if duration > 0xFFFFFFFF:
                raise Mp4Error(f"{kind} duration overflow")
            struct.pack_into(">I", b, p0 + 16, duration)
    elif kind == "tkhd":
        if v == 1:
            struct.pack_into(">Q", b, p0 + 28, duration)
        else:
            if duration > 0xFFFFFFFF:
                raise Mp4Error("tkhd duration overflow")
            struct.pack_into(">I", b, p0 + 20, duration)
    return bytes(b)


def _set_modification_time(box_raw: bytes, header_size: int) -> bytes:
    b = bytearray(box_raw)
    p0 = header_size
    now = int(time.time()) + 2082844800  # seconds since 1904
    if b[p0] == 1:
        struct.pack_into(">Q", b, p0 + 12, now)
    else:
        struct.pack_into(">I", b, p0 + 8, now & 0xFFFFFFFF)
    return bytes(b)


@dataclass
class OutSample:
    src: int        # index into sources
    offset: int
    size: int
    duration: int
    cts_offset: int
    sync: bool
    desc_index: int = 1


@dataclass
class OutTrack:
    template: Track
    samples: List[OutSample]
    stsd_entries: List[bytes]
    edits: Optional[List[EditEntry]]
    stbl_extra: List[bytes] = field(default_factory=list)  # raw boxes appended to stbl
    timescale: Optional[int] = None  # override media timescale
    mdhd_raw: Optional[bytes] = None  # override mdhd (e.g. new audio encode)

    @property
    def media_timescale(self) -> int:
        return self.timescale or self.template.timescale


def _run_length(values: Sequence[int]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for v in values:
        if out and out[-1][1] == v:
            out[-1] = (out[-1][0] + 1, v)
        else:
            out.append((1, v))
    return out


def _build_stbl(track: OutTrack, chunk_offsets: List[int], chunk_sizes: List[Tuple[int, int]],
                use_co64: bool) -> bytes:
    """chunk_sizes: list of (num_samples, desc_index) per chunk, in track order."""
    samples = track.samples
    parts = []
    stsd_payload = bytes(track.template.stsd_version_flags) + struct.pack(">I", len(track.stsd_entries))
    stsd_payload += b"".join(track.stsd_entries)
    parts.append(make_box("stsd", stsd_payload))
    stts = _run_length([s.duration for s in samples])
    parts.append(make_fullbox("stts", 0, 0, struct.pack(">I", len(stts)) +
                              b"".join(struct.pack(">II", c, d) for c, d in stts)))
    if any(s.cts_offset != 0 for s in samples):
        ctts = _run_length([s.cts_offset for s in samples])
        neg = any(v < 0 for _, v in ctts)
        fmt = ">Ii" if neg else ">II"
        parts.append(make_fullbox("ctts", 1 if neg else 0, 0, struct.pack(">I", len(ctts)) +
                                  b"".join(struct.pack(fmt, c, v) for c, v in ctts)))
    if not all(s.sync for s in samples):
        idx = [i + 1 for i, s in enumerate(samples) if s.sync]
        parts.append(make_fullbox("stss", 0, 0, struct.pack(">I", len(idx)) +
                                  struct.pack(f">{len(idx)}I", *idx)))
    stsc = []
    for ci, (cnt, di) in enumerate(chunk_sizes):
        if not stsc or stsc[-1][1] != cnt or stsc[-1][2] != di:
            stsc.append((ci + 1, cnt, di))
    parts.append(make_fullbox("stsc", 0, 0, struct.pack(">I", len(stsc)) +
                              b"".join(struct.pack(">III", *e) for e in stsc)))
    sizes = [s.size for s in samples]
    if sizes and all(x == sizes[0] for x in sizes):
        parts.append(make_fullbox("stsz", 0, 0, struct.pack(">II", sizes[0], len(sizes))))
    else:
        parts.append(make_fullbox("stsz", 0, 0, struct.pack(">II", 0, len(sizes)) +
                                  struct.pack(f">{len(sizes)}I", *sizes)))
    if use_co64:
        parts.append(make_fullbox("co64", 0, 0, struct.pack(">I", len(chunk_offsets)) +
                                  struct.pack(f">{len(chunk_offsets)}Q", *chunk_offsets)))
    else:
        parts.append(make_fullbox("stco", 0, 0, struct.pack(">I", len(chunk_offsets)) +
                                  struct.pack(f">{len(chunk_offsets)}I", *chunk_offsets)))
    parts.extend(track.stbl_extra)
    return make_box("stbl", b"".join(parts))


def _build_elst(edits: List[EditEntry], version: int) -> bytes:
    need64 = any(e.segment_duration > 0xFFFFFFFF or abs(e.media_time) > 0x7FFFFFFF for e in edits)
    v = 1 if (version == 1 or need64) else 0
    body = struct.pack(">I", len(edits))
    for e in edits:
        if v == 1:
            body += struct.pack(">Qq", e.segment_duration, e.media_time)
        else:
            body += struct.pack(">Ii", e.segment_duration, e.media_time)
        body += struct.pack(">hh", e.rate_int, e.rate_frac)
    return make_box("edts", make_fullbox("elst", v, 0, body))


def track_presentation_duration(track: OutTrack, movie_timescale: int) -> int:
    if track.edits:
        return sum(e.segment_duration for e in track.edits)
    media = sum(s.duration for s in track.samples)
    return media * movie_timescale // track.media_timescale


def _build_trak(track: OutTrack, chunk_offsets, chunk_sizes, use_co64, movie_timescale) -> bytes:
    tpl = track.template
    media_duration = sum(s.duration for s in track.samples)
    pres = track_presentation_duration(track, movie_timescale)
    tkhd = _set_modification_time(_set_duration(tpl.tkhd.raw, tpl.tkhd.header_size, "tkhd", pres),
                                  tpl.tkhd.header_size)
    mdhd_src = track.mdhd_raw if track.mdhd_raw is not None else tpl.mdhd.raw
    mdhd_hs = 8
    mdhd = _set_modification_time(_set_duration(mdhd_src, mdhd_hs, "mdhd", media_duration), mdhd_hs)
    stbl = _build_stbl(track, chunk_offsets, chunk_sizes, use_co64)
    minf_src = tpl.trak.child("mdia").child("minf")
    minf_parts = [c.raw for c in minf_src.children if c.type != "stbl"]
    minf = make_box("minf", b"".join(minf_parts) + stbl)
    mdia_src = tpl.trak.child("mdia")
    mdia_parts = []
    for c in mdia_src.children:
        if c.type == "mdhd":
            mdia_parts.append(mdhd)
        elif c.type == "minf":
            mdia_parts.append(minf)
        else:
            mdia_parts.append(c.raw)
    mdia = make_box("mdia", b"".join(mdia_parts))
    trak_parts = []
    for c in tpl.trak.children:
        if c.type == "tkhd":
            trak_parts.append(tkhd)
            if track.edits is not None and tpl.trak.child("edts") is None:
                trak_parts.append(_build_elst(track.edits, tpl.elst_version))
        elif c.type == "edts":
            if track.edits is not None:
                trak_parts.append(_build_elst(track.edits, tpl.elst_version))
        elif c.type == "mdia":
            trak_parts.append(mdia)
        else:
            trak_parts.append(c.raw)
    return make_box("trak", b"".join(trak_parts))


@dataclass
class _Chunk:
    track_index: int
    start_time: float
    sample_indices: range
    nbytes: int


def write_movie(out_path: str, sources: Sequence[str], movie: Movie, tracks: Sequence[OutTrack],
                faststart: bool = True, chunk_seconds: float = 0.5,
                progress=None, cancel_check=None) -> None:
    """Write an MP4 file whose samples are copied from `sources`.

    `movie` supplies ftyp/mvhd/other moov-level boxes.  Track order and track
    ids follow `tracks` templates.
    """
    # 1. chunking
    chunks: List[_Chunk] = []
    for ti, tr in enumerate(tracks):
        ts = tr.media_timescale
        t = 0
        start = 0
        start_t = 0
        nbytes = 0
        limit = int(chunk_seconds * ts)
        for i, s in enumerate(tr.samples):
            if i > start and (t - start_t >= limit or s.desc_index != tr.samples[start].desc_index):
                chunks.append(_Chunk(ti, start_t / ts, range(start, i), nbytes))
                start = i
                start_t = t
                nbytes = 0
            nbytes += s.size
            t += s.duration
        if start < len(tr.samples):
            chunks.append(_Chunk(ti, start_t / ts, range(start, len(tr.samples)), nbytes))
    chunks.sort(key=lambda c: (c.start_time, c.track_index))
    total_media = sum(c.nbytes for c in chunks)

    ftyp_raw = movie.ftyp.raw if movie.ftyp is not None else make_box(
        "ftyp", b"isom" + struct.pack(">I", 512) + b"isomiso2avc1mp41")
    large_mdat = total_media + 16 > 0xFFFFFFFF
    mdat_header_size = 16 if large_mdat else 8

    def build_moov(base: int, use_co64: bool) -> bytes:
        per_track_offsets: List[List[int]] = [[] for _ in tracks]
        per_track_sizes: List[List[Tuple[int, int]]] = [[] for _ in tracks]
        pos = base
        for c in chunks:
            per_track_offsets[c.track_index].append(pos)
            tr = tracks[c.track_index]
            per_track_sizes[c.track_index].append(
                (len(c.sample_indices), tr.samples[c.sample_indices.start].desc_index))
            pos += c.nbytes
        traks = [
            _build_trak(tr, per_track_offsets[i], per_track_sizes[i], use_co64, movie.timescale)
            for i, tr in enumerate(tracks)
        ]
        mov_dur = max((track_presentation_duration(tr, movie.timescale) for tr in tracks), default=0)
        mvhd = _set_modification_time(_set_duration(movie.mvhd.raw, movie.mvhd.header_size, "mvhd", mov_dur),
                                      movie.mvhd.header_size)
        others = b"".join(b.raw for b in movie.moov_other)
        return make_box("moov", mvhd + b"".join(traks) + others)

    use_co64 = len(ftyp_raw) + total_media + 64 * 1024 * 1024 > 0xFFFFFFFF
    if faststart:
        probe = build_moov(0, use_co64)
        base = len(ftyp_raw) + len(probe) + mdat_header_size
        moov = build_moov(base, use_co64)
        if len(moov) != len(probe):
            raise Mp4Error("moov size changed between passes")
    else:
        base = len(ftyp_raw) + mdat_header_size
        moov = build_moov(base, use_co64)

    if large_mdat:
        mdat_hdr = struct.pack(">I4sQ", 1, b"mdat", total_media + 16)
    else:
        mdat_hdr = struct.pack(">I4s", total_media + 8, b"mdat")

    handles = [open(p, "rb") for p in sources]
    try:
        with open(out_path, "wb") as out:
            out.write(ftyp_raw)
            if faststart:
                out.write(moov)
            out.write(mdat_hdr)
            written = 0
            for ci, c in enumerate(chunks):
                if cancel_check is not None and ci % 64 == 0:
                    cancel_check()
                tr = tracks[c.track_index]
                # coalesce contiguous reads from the same source
                run_src = None
                run_off = 0
                run_len = 0
                for si in c.sample_indices:
                    s = tr.samples[si]
                    if run_src == s.src and run_off + run_len == s.offset:
                        run_len += s.size
                        continue
                    if run_src is not None:
                        _copy(handles[run_src], run_off, run_len, out)
                    run_src, run_off, run_len = s.src, s.offset, s.size
                if run_src is not None:
                    _copy(handles[run_src], run_off, run_len, out)
                written += c.nbytes
                if progress is not None and ci % 32 == 0:
                    progress(written / max(1, total_media))
            if not faststart:
                out.write(moov)
            out.flush()
            os.fsync(out.fileno())
    finally:
        for h in handles:
            h.close()
    if progress is not None:
        progress(1.0)


def _copy(src: BinaryIO, offset: int, length: int, dst: BinaryIO) -> None:
    src.seek(offset)
    remaining = length
    while remaining > 0:
        buf = src.read(min(remaining, 8 * 1024 * 1024))
        if not buf:
            raise Mp4Error("unexpected end of source file while copying samples")
        dst.write(buf)
        remaining -= len(buf)


def read_sample(f: BinaryIO, offset: int, size: int) -> bytes:
    f.seek(offset)
    data = f.read(size)
    if len(data) != size:
        raise Mp4Error("short read of sample data")
    return data
