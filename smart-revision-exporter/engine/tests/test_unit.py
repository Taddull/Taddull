"""Unit tests: timecode, bitstream parsing, MP4 round trip, planning logic."""

from fractions import Fraction

import pytest

from conftest import SynthTimeline, make_master
from srx import h264
from srx.bitio import BitReader, BitWriter, nal_to_rbsp, rbsp_to_nal
from srx.media import analyze_master
from srx.mp4 import OutSample, OutTrack, read_movie, write_movie
from srx.plan import PlanError, Revision, build_plan, merge_ranges, output_to_master_map
from srx.timecode import frames_to_tc, parse_rate, tc_to_frames


@pytest.mark.parametrize("s,expected", [("23.976", Fraction(24000, 1001)), ("29.97", Fraction(30000, 1001)),
                                        ("59.94", Fraction(60000, 1001)), ("25", Fraction(25)),
                                        ("30000/1001", Fraction(30000, 1001)), (24, Fraction(24))])
def test_parse_rate(s, expected):
    assert parse_rate(s) == expected


def test_timecode_ndf_roundtrip():
    r = Fraction(24000, 1001)
    for f in (0, 1, 23, 24, 86399, 86400, 123456):
        assert tc_to_frames(frames_to_tc(f, r), r) == f
    assert tc_to_frames("01:00:00:00", Fraction(25)) == 90000


def test_timecode_drop_frame():
    r = Fraction(30000, 1001)
    assert frames_to_tc(1800, r, True) == "00:01:00;02"
    assert tc_to_frames("00:01:00;02", r) == 1800
    assert frames_to_tc(17982, r, True) == "00:10:00;00"
    for f in range(0, 40000, 997):
        assert tc_to_frames(frames_to_tc(f, r, True), r, True) == f
    with pytest.raises(Exception):
        tc_to_frames("00:01:00;00", r, True)  # frames 0 and 1 are dropped at minute 1


def test_expgolomb_and_emulation_prevention():
    w = BitWriter()
    vals = [0, 1, 2, 3, 7, 255, 65535]
    for v in vals:
        w.ue(v)
    w.se(-5)
    w.se(9)
    w.trailing_bits()
    data = w.getvalue()
    r = BitReader(data)
    assert [r.ue() for _ in vals] == vals
    assert r.se() == -5 and r.se() == 9
    raw = bytes([0, 0, 1, 0, 0, 0, 0, 0, 3, 5])
    assert nal_to_rbsp(rbsp_to_nal(raw)) == raw
    assert b"\x00\x00\x01" not in rbsp_to_nal(raw)


def test_sps_parse_and_avcc_roundtrip(work):
    tl = SynthTimeline(width=320, height=180, fps="30000/1001", frames=40)
    m = make_master(work, tl, gop=20)
    a = analyze_master(m)
    sps = a.video.active_sps()
    assert (sps.width, sps.height) == (320, 180)
    assert sps.profile_idc == 100 and sps.vui.colour_primaries == 1
    assert a.video.fps == Fraction(30000, 1001)
    cfg = a.video.avcc
    assert h264.AvcConfig.parse(cfg.build()).build() == cfg.build()


def test_mp4_roundtrip_identical_samples(work):
    tl = SynthTimeline(width=160, height=90, fps="25/1", frames=60)
    m = make_master(work, tl, gop=12)
    mv = read_movie(m)
    tracks = []
    for t in mv.tracks:
        samples = [OutSample(0, t.offsets[i], t.sizes[i], t.durations[i], t.cts_offsets[i], t.is_sync(i))
                   for i in range(t.sample_count)]
        tracks.append(OutTrack(t, samples, t.stsd_entries, t.edits, [b.raw for b in t.stbl_other]))
    out = str(work / "rt.mp4")
    write_movie(out, [m], mv, tracks, faststart=False)
    mv2 = read_movie(out)
    for t1, t2 in zip(mv.tracks, mv2.tracks):
        assert t1.sizes == t2.sizes and t1.durations == t2.durations and t1.cts_offsets == t2.cts_offsets
        assert t1.edits == t2.edits
        assert [t1.is_sync(i) for i in range(t1.sample_count)] == [t2.is_sync(i) for i in range(t2.sample_count)]
    assert not mv2.moov_before_mdat


def test_merge_ranges():
    assert merge_ranges([(10, 20, 0), (15, 30, 2), (40, 50, 0)]) == [(10, 30, 2), (40, 50, 0)]
    assert merge_ranges([(10, 20, 0), (20, 25, 0)]) == [(10, 25, 0)]


def test_plan_cut_and_resume_points(work):
    tl = SynthTimeline(width=160, height=90, fps="25/1", frames=200)
    m = make_master(work, tl, gop=50, bframes=3)
    a = analyze_master(m)
    v = a.video
    assert v.resume_points[:4] == [0, 50, 100, 150]
    # every resume point is a cut point; cut points are decode-order prefixes
    for k in v.cut_points:
        assert sorted(v.disp_of_dec[:k]) == list(range(k))
    p = build_plan(a, [Revision(60, 70), Revision(65, 80), Revision(160, 170)])
    kinds = [(s.kind, s.master_start, s.master_end) for s in p.segments]
    assert kinds[0] == ("copy", 0, kinds[1][1])
    assert kinds[1][0] == "render" and kinds[1][2] == 100 and kinds[1][1] <= 60
    assert kinds[-1] == ("render", kinds[-1][1], 200)
    assert p.stats["output_frames"] == 200
    assert output_to_master_map(p) == list(range(200))


def test_plan_rejects_bad_ranges(work):
    tl = SynthTimeline(width=160, height=90, fps="25/1", frames=50)
    a = analyze_master(make_master(work, tl, gop=25))
    for bad in (Revision(-1, 5), Revision(10, 10), Revision(40, 60), Revision(5, 10, video=False, audio=False)):
        with pytest.raises(PlanError):
            build_plan(a, [bad])
    with pytest.raises(PlanError) as e:
        build_plan(a, [Revision(10, 20)], strict=True)
    assert "Strict" in str(e.value)


def test_plan_duration_change_mapping(work):
    tl = SynthTimeline(width=160, height=90, fps="25/1", frames=100)
    a = analyze_master(make_master(work, tl, gop=25, bframes=0))
    p = build_plan(a, [Revision(30, 40, delta=5)])
    assert p.output_frames == 105
    o2m = output_to_master_map(p)
    assert o2m[:30] == list(range(30))
    assert o2m[-10:] == list(range(90, 100))
    assert all(x == -1 for x in o2m[30:45])
    assert p.audio[0].strategy == "full"
