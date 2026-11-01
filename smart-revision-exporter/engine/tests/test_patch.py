"""Core patch scenarios (requirements 2-13, 17, 18).

Every test checks the engine's own verification report AND re-checks pixel
identity independently with FFmpeg's framehash muxer.
"""

import subprocess
from fractions import Fraction

import pytest

from conftest import (AudioChange, Revision, SynthTimeline, VideoChange, audiohashes, frame_pts, framehashes,
                      independent_identity, make_master, run_export)
from srx.media import analyze_master


def _assert_ok(res, master, out):
    rep = res["report_data"]
    assert res["status"] == "succeeded" and rep["status"] == "passed", rep.get("failures")
    same, preserved, n_out, n_master = independent_identity(master, out, rep)
    assert same == preserved, f"independent check: {preserved - same} preserved frames differ"
    assert n_out == rep["video"]["output_frames"]
    return rep


def test_revision_starts_between_keyframes(work):
    tl = SynthTimeline(fps="25/1", frames=250)
    m = make_master(work, tl, gop=50, bframes=3)
    a = analyze_master(m).video
    start = 63
    assert start not in a.resume_points
    rev = tl.revised([VideoChange(start, 80)], [AudioChange(start, 80)])
    res = run_export(work, m, [Revision(start, 80)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    seg = [s for s in rep["video"]["segments"] if s["kind"] == "render"][0]
    # head is preserved up to the clean cut point right before the revision (mini-GOP granularity)
    assert start - seg["output"][0] <= 4
    assert seg["output"][1] == 100  # tail extends to the next IDR


def test_revision_ends_between_keyframes(work):
    tl = SynthTimeline(fps="25/1", frames=250)
    m = make_master(work, tl, gop=50, bframes=0)
    rev = tl.revised([VideoChange(100, 117)])
    res = run_export(work, m, [Revision(100, 117)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    seg = [s for s in rep["video"]["segments"] if s["kind"] == "render"][0]
    assert seg["output"] == [100, 150]
    assert rep["video"]["boundary_frames"] == 33


def test_multiple_separate_revisions(work):
    tl = SynthTimeline(fps="30/1", frames=600)
    m = make_master(work, tl, gop=60)
    ranges = [(75, 90), (340, 352), (500, 515)]
    rev = tl.revised([VideoChange(a, b) for a, b in ranges], [AudioChange(a, b) for a, b in ranges])
    res = run_export(work, m, [Revision(a, b, label=f"r{i}") for i, (a, b) in enumerate(ranges)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    assert len([s for s in rep["video"]["segments"] if s["kind"] == "render"]) == 3
    assert rep["plan_stats"]["render_jobs"] == 3


def test_overlapping_and_adjacent_revisions_are_merged(work):
    tl = SynthTimeline(fps="25/1", frames=200)
    m = make_master(work, tl, gop=25)
    rev = tl.revised([VideoChange(30, 45), VideoChange(40, 55), VideoChange(55, 60)])
    res = run_export(work, m, [Revision(30, 45), Revision(40, 55), Revision(55, 60)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    renders = [s for s in rep["video"]["segments"] if s["kind"] == "render"]
    assert len(renders) == 1 and renders[0]["revised"] == [[30, 60]]


def test_revisions_near_beginning_and_end(work):
    tl = SynthTimeline(fps="25/1", frames=200)
    m = make_master(work, tl, gop=40)
    rev = tl.revised([VideoChange(0, 8), VideoChange(192, 200)], [AudioChange(0, 8), AudioChange(192, 200)])
    res = run_export(work, m, [Revision(0, 8), Revision(192, 200)], rev)
    _assert_ok(res, m, str(work / "out.mp4"))


def test_video_only_revision_keeps_audio_bit_identical(work):
    tl = SynthTimeline(fps="25/1", frames=200)
    m = make_master(work, tl, gop=50)
    rev = tl.revised([VideoChange(70, 90)])
    res = run_export(work, m, [Revision(70, 90, audio=False)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    assert rep["audio"][0]["strategy"] == "copy"
    assert audiohashes(m) == audiohashes(str(work / "out.mp4"))


def test_audio_only_revision_renders_no_video(work):
    tl = SynthTimeline(fps="25/1", frames=250)
    m = make_master(work, tl, gop=50)
    rev = tl.revised([], [AudioChange(100, 140, freq=880)])
    res = run_export(work, m, [Revision(100, 140, video=False)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    assert rep["video"]["reencoded_frames"] == 0
    assert rep["video"]["identical_unchanged"] == 250
    assert framehashes(m) == framehashes(str(work / "out.mp4"))
    assert rep["audio"][0]["strategy"] == "splice"
    ha, hb = audiohashes(m), audiohashes(str(work / "out.mp4"))
    assert ha != hb and len(ha) == len(hb)


def test_simultaneous_audio_and_video_revision(work):
    tl = SynthTimeline(fps="25/1", frames=250)
    m = make_master(work, tl, gop=50)
    rev = tl.revised([VideoChange(120, 145)], [AudioChange(120, 145)])
    res = run_export(work, m, [Revision(120, 145)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    a = rep["audio"][0]
    assert a["strategy"] == "splice"
    assert a["pcm_outside_transitions"]["differing"] == 0
    assert all(s.get("sync_lag_samples", 0) == 0 for s in a["splices"])


@pytest.mark.parametrize("fps", ["24000/1001", "24/1", "25/1", "30000/1001", "30/1", "60/1", "60000/1001"])
def test_frame_rates(work, fps):
    r = Fraction(fps)
    n = int(round(float(r) * 8))
    tl = SynthTimeline(fps=fps, frames=n, start_frame=int(round(float(r))) * 3600)  # 01:00:00:00 start
    gop = int(round(float(r))) * 2
    m = make_master(work, tl, gop=gop)
    a, b = int(n * 0.4) + 1, int(n * 0.4) + int(float(r))
    rev = tl.revised([VideoChange(a, b)], [AudioChange(a, b)])
    res = run_export(work, m, [Revision(a, b)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    assert analyze_master(str(work / "out.mp4")).video.fps == r
    assert rep["audio"][0]["strategy"] == "splice"


def test_b_frame_heavy_stream(work):
    tl = SynthTimeline(fps="25/1", frames=240)
    m = make_master(work, tl, gop=120, bframes=8, extra_x264="b-adapt=0")
    a = analyze_master(m).video
    assert a.max_reorder_delay >= 2
    assert sum(1 for t in a.slice_type if t == "B") > 150
    rev = tl.revised([VideoChange(97, 113)])
    res = run_export(work, m, [Revision(97, 113, audio=False)], rev)
    _assert_ok(res, m, str(work / "out.mp4"))


@pytest.mark.parametrize("gop,bframes", [(1, 0), (12, 2), (48, 3), (400, 3)])
def test_gop_lengths(work, gop, bframes):
    tl = SynthTimeline(fps="25/1", frames=300)
    m = make_master(work, tl, gop=gop, bframes=bframes, scenecut=False)
    rev = tl.revised([VideoChange(130, 150)])
    res = run_export(work, m, [Revision(130, 150, audio=False)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    if gop == 1:
        assert rep["video"]["boundary_frames"] == 0
        assert rep["video"]["identical_unchanged"] == 280


@pytest.mark.parametrize("profile,bframes", [("baseline", 0), ("main", 2), ("high", 3)])
def test_h264_profiles(work, profile, bframes):
    tl = SynthTimeline(fps="25/1", frames=150)
    m = make_master(work, tl, gop=30, bframes=bframes, profile=profile)
    pidc = analyze_master(m).video.active_sps().profile_idc
    assert pidc == {"baseline": 66, "main": 77, "high": 100}[profile]
    rev = tl.revised([VideoChange(50, 70)])
    res = run_export(work, m, [Revision(50, 70, audio=False)], rev)
    _assert_ok(res, m, str(work / "out.mp4"))
    out = analyze_master(str(work / "out.mp4")).video
    assert {s.profile_idc for s in out.sps} == {pidc}
    assert {p.entropy_coding_mode for p in out.pps} == {profile != "baseline"}


def test_master_without_colour_metadata(work):
    tl = SynthTimeline(fps="25/1", frames=120)
    m = make_master(work, tl, gop=30, color=False)
    assert analyze_master(m).video.active_sps().vui is None or \
        not analyze_master(m).video.active_sps().vui.colour_description_present
    rev = tl.revised([VideoChange(40, 55)])
    res = run_export(work, m, [Revision(40, 55, audio=False)], rev)
    _assert_ok(res, m, str(work / "out.mp4"))
    out = analyze_master(str(work / "out.mp4")).video
    assert all(not (s.vui and s.vui.colour_description_present) for s in out.sps)


def test_frame_count_and_timestamps(work):
    tl = SynthTimeline(fps="30000/1001", frames=300)
    m = make_master(work, tl, gop=60)
    rev = tl.revised([VideoChange(100, 130)], [AudioChange(100, 130)])
    run_export(work, m, [Revision(100, 130)], rev)
    pm, po = frame_pts(m), frame_pts(str(work / "out.mp4"))
    assert len(pm) == len(po) == 300
    assert pm == po
    assert sorted(po) == po and len(set(po)) == len(po)


def test_master_without_audio(work):
    tl = SynthTimeline(fps="25/1", frames=100)
    m = make_master(work, tl, gop=25, audio=False)
    rev = tl.revised([VideoChange(30, 40)])
    res = run_export(work, m, [Revision(30, 40)], rev)
    rep = _assert_ok(res, m, str(work / "out.mp4"))
    assert rep["audio"] == []


def test_fast_patch_mode(work):
    tl = SynthTimeline(fps="25/1", frames=300)
    m = make_master(work, tl, gop=50)
    rev = tl.revised([VideoChange(120, 140)], [AudioChange(120, 140)])
    res = run_export(work, m, [Revision(120, 140)], rev, mode="fast")
    rep = res["report_data"]
    assert rep["status"] == "passed" and rep["level"] == "fast"
    pi = [c for c in rep["checks"] if c["name"] == "pixel_identity"][0]
    assert pi["status"] == "warn" and "NOT decoded" in pi["detail"]
    same, preserved, _, _ = independent_identity(m, str(work / "out.mp4"), rep)
    assert same == preserved


def test_open_gop_master_uses_only_idr_resume_points(work):
    tl = SynthTimeline(fps="25/1", frames=300)
    m = make_master(work, tl, gop=50, open_gop=True, bframes=3)
    a = analyze_master(m).video
    rev = tl.revised([VideoChange(120, 135)])
    res = run_export(work, m, [Revision(120, 135, audio=False)], rev)
    _assert_ok(res, m, str(work / "out.mp4"))
    if a.open_gop_frames:
        assert any("open GOP" in w for w in a.warnings)


def test_high10_profile_if_supported(work):
    probe = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=64x64:rate=25", "-t", "0.2",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p10le", "-f", "null", "-"], capture_output=True)
    if probe.returncode != 0:
        pytest.skip("libx264 in this FFmpeg build has no 10-bit support")
    tl = SynthTimeline(fps="25/1", frames=100)
    path = make_master(work, tl, name="m10.mp4", gop=25, profile="high10", pix_fmt="yuv420p10le")
    assert analyze_master(path).video.pix_fmt == "yuv420p10le"
    rev = tl.revised([VideoChange(30, 45)])
    res = run_export(work, path, [Revision(30, 45)], rev)
    _assert_ok(res, path, str(work / "out.mp4"))
