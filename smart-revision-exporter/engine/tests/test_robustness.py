"""Transitions, strict mode, duration changes, repeated cycles, interruption,
recovery and error handling (requirements 6, 14, 15, 16 and section 11)."""

import hashlib
import json
import os
import signal
import subprocess
import sys
import time

import pytest

from conftest import (ENGINE, AudioChange, Revision, SynthTimeline, VideoChange, audiohashes, framehashes,
                      independent_identity, make_master, options, run_export)
from srx.events import Emitter
from srx.exporter import ExportError, Exporter
from srx.jobs import list_jobs, recover_jobs
from srx.media import AnalysisError, analyze_master
from srx.plan import PlanError
from srx.render import RenderError, SyntheticRenderSource
from srx.synthetic import DurationChange


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# ---------------------------------------------------------------- transitions
def test_transition_outside_declared_range_is_detected(work):
    """A cross-fade that starts 8 frames before the declared revision changes
    frames the user did not declare.  Verification must refuse the result."""
    tl = SynthTimeline(fps="25/1", frames=250)
    m = make_master(work, tl, gop=50, bframes=0)
    rev = tl.revised([VideoChange(110, 130, fade_in=8)])
    with pytest.raises(ExportError) as e:
        run_export(work, m, [Revision(110, 130, audio=False)], rev)
    assert e.value.code == "verification_failed"
    assert "OUTSIDE the declared revision" in str(e.value)
    assert not os.path.exists(work / "out.mp4")


def test_transition_with_handles_passes(work):
    tl = SynthTimeline(fps="25/1", frames=250)
    m = make_master(work, tl, gop=50, bframes=0)
    rev = tl.revised([VideoChange(110, 130, fade_in=8)])
    res = run_export(work, m, [Revision(110, 130, audio=False, handles_before=8)], rev)
    rep = res["report_data"]
    assert rep["status"] == "passed"
    same, preserved, _, _ = independent_identity(m, str(work / "out.mp4"), rep)
    assert same == preserved


# ---------------------------------------------------------------- strict mode
def test_strict_mode_refuses_reencoding_unchanged_frames(work):
    tl = SynthTimeline(fps="25/1", frames=200)
    m = make_master(work, tl, gop=50)
    rev = tl.revised([VideoChange(60, 70)])
    with pytest.raises(ExportError) as e:
        run_export(work, m, [Revision(60, 70)], rev, strict=True)
    assert "Strict Verified Frame Preservation cannot be met" in str(e.value)
    assert "Revision-Ready Master" in str(e.value)


def test_strict_mode_on_all_intra_master(work):
    tl = SynthTimeline(fps="25/1", frames=150)
    m = make_master(work, tl, gop=1, bframes=0)
    rev = tl.revised([VideoChange(60, 70)], [AudioChange(60, 70)])
    res = run_export(work, m, [Revision(60, 70)], rev, strict=True)
    rep = res["report_data"]
    assert rep["status"] == "passed"
    assert rep["video"]["boundary_frames"] == 0
    assert rep["video"]["identical_unchanged"] == 140


# ---------------------------------------------------------------- duration change
@pytest.mark.parametrize("insert,remove", [(10, 0), (0, 6), (12, 4)])
def test_duration_changing_revision(work, insert, remove):
    tl = SynthTimeline(fps="25/1", frames=200)
    m = make_master(work, tl, gop=25, bframes=2)
    at = 80
    rev = tl.revised(duration_change=DurationChange(at=at, remove=remove, insert=insert))
    span = max(remove, 1)
    delta = insert - remove
    revision = Revision(at, at + span, delta=delta + (span - remove) if remove == 0 else delta)
    if remove == 0:
        # replacing one original frame with that frame + inserted frames
        revision = Revision(at, at + 1, delta=insert)
        rev = tl.revised(duration_change=DurationChange(at=at, remove=0, insert=insert))
    res = run_export(work, m, [revision], rev)
    rep = res["report_data"]
    assert rep["status"] == "passed", rep["failures"]
    out = analyze_master(str(work / "out.mp4"))
    assert out.video.frame_count == 200 + insert - remove
    assert rep["audio"][0]["strategy"] == "full"


# ---------------------------------------------------------------- repeated cycles
def test_repeated_revision_cycles_no_generation_loss(work):
    tl = SynthTimeline(fps="25/1", frames=300)
    m = make_master(work, tl, gop=50)
    v1 = tl.revised([VideoChange(60, 80)], [AudioChange(60, 80)])
    r1 = run_export(work, m, [Revision(60, 80)], v1, out_name="v1.mp4")
    assert r1["report_data"]["status"] == "passed"
    # cycle 2: different region, timeline still contains the cycle-1 change
    v2 = tl.revised([VideoChange(60, 80), VideoChange(210, 230)], [AudioChange(60, 80), AudioChange(210, 230)])
    r2 = run_export(work, str(work / "v1.mp4"), [Revision(210, 230)], v2, out_name="v2.mp4")
    assert r2["report_data"]["status"] == "passed"
    # cycle 3: revise the cycle-1 region again
    v3 = tl.revised([VideoChange(60, 80, effect="negate"), VideoChange(210, 230)],
                    [AudioChange(60, 80, freq=990), AudioChange(210, 230)])
    r3 = run_export(work, str(work / "v2.mp4"), [Revision(60, 80)], v3, out_name="v3.mp4")
    assert r3["report_data"]["status"] == "passed"
    h1, h2, h3 = framehashes(str(work / "v1.mp4")), framehashes(str(work / "v2.mp4")), framehashes(str(work / "v3.mp4"))
    # the cycle-1 patch survives cycle 2 bit-exactly (packets copied, never re-encoded)
    assert h2[60:80] == h1[60:80]
    # the cycle-2 patch survives cycle 3 bit-exactly
    assert h3[210:230] == h2[210:230]
    # parameter sets do not accumulate: only sets referenced by frames are kept
    out3 = analyze_master(str(work / "v3.mp4")).video
    used_pps = set(out3.pps_id)
    used_sps = {p.sps_id for p in out3.pps if p.pps_id in used_pps}
    assert {s.sps_id for s in out3.sps} == used_sps
    assert {p.pps_id for p in out3.pps} == used_pps
    # project history recorded three cycles
    proj = json.load(open(next((work / "projects").glob("*.json"))))
    assert len(proj["cycles"]) == 3
    assert proj["cycles"][1]["base"]["fingerprint"] == proj["cycles"][0]["output"]["fingerprint"]


# ---------------------------------------------------------------- safety
def test_never_overwrites(work):
    tl = SynthTimeline(fps="25/1", frames=60)
    m = make_master(work, tl, gop=30)
    (work / "out.mp4").write_bytes(b"existing")
    rev = tl.revised([VideoChange(10, 20)])
    with pytest.raises(ExportError) as e:
        run_export(work, m, [Revision(10, 20)], rev)
    assert e.value.code == "output_exists"
    assert (work / "out.mp4").read_bytes() == b"existing"
    with pytest.raises(ExportError) as e:
        Exporter(Emitter(quiet=True)).smart_export(m, m, [Revision(10, 20)], SyntheticRenderSource(rev), options(work))
    assert e.value.code in ("output_exists", "output_is_master")


def test_missing_master(work):
    with pytest.raises(Exception):
        analyze_master(str(work / "nope.mp4"))


def test_unsupported_codec_hevc(work):
    p = str(work / "hevc.mp4")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=25",
                        "-frames:v", "30", "-c:v", "libx265", "-tag:v", "hvc1", p], capture_output=True)
    if r.returncode != 0:
        pytest.skip("libx265 unavailable")
    with pytest.raises(AnalysisError) as e:
        analyze_master(p)
    assert "unsupported video codec" in str(e.value)


def test_variable_frame_rate_master_is_refused(work):
    p = str(work / "vfr.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=25",
                    "-frames:v", "60", "-vf", "setpts='if(lt(N,30),N,N*1.5)/25/TB'", "-fps_mode", "vfr",
                    "-c:v", "libx264", "-preset", "veryfast", p], check=True)
    a = analyze_master(p)
    assert not a.video.patchable
    assert any("frame rate" in i for i in a.video.blocking_issues)
    from srx.plan import build_plan
    with pytest.raises(PlanError):
        build_plan(a, [Revision(10, 20)])


def test_interlaced_master_is_refused(work):
    p = str(work / "int.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=25",
                    "-frames:v", "30", "-c:v", "libx264", "-preset", "veryfast", "-x264-params", "tff=1",
                    "-flags", "+ildct+ilme", p], check=True)
    a = analyze_master(p)
    assert any("interlaced" in i for i in a.video.blocking_issues)


def test_render_failure_is_reported_cleanly(work):
    tl = SynthTimeline(fps="25/1", frames=100)
    m = make_master(work, tl, gop=25)

    class Broken(SyntheticRenderSource):
        def render(self, req, out_dir, **kw):
            raise RenderError("Resolve render failed: simulated")
    with pytest.raises(ExportError) as e:
        Exporter(Emitter(quiet=True)).smart_export(m, str(work / "o.mp4"), [Revision(30, 40)], Broken(tl),
                                                   options(work))
    assert e.value.code == "render_error"
    assert not os.path.exists(work / "o.mp4")
    assert not [f for f in os.listdir(work) if "srx-partial" in f]
    job = [j for j in list_jobs(str(work / "jobs"))][-1]
    assert job["state"] == "failed"


def test_render_with_wrong_frame_count_is_rejected(work):
    tl = SynthTimeline(fps="25/1", frames=100)
    m = make_master(work, tl, gop=25)
    short = SynthTimeline(fps="25/1", frames=100)

    class Short(SyntheticRenderSource):
        def render(self, req, out_dir, **kw):
            from srx.render import inspect_clip
            path = os.path.join(out_dir, "short.mov")
            self.timeline.render_intermediate(req.timeline_start, req.timeline_end - 1, path)
            return inspect_clip(path, req.timeline_start, req.frames, self.timeline.rate, True, "short")
    with pytest.raises(ExportError) as e:
        Exporter(Emitter(quiet=True)).smart_export(m, str(work / "o.mp4"), [Revision(30, 40)], Short(short),
                                                   options(work))
    assert "frames, expected" in str(e.value)


def test_changed_frame_rate_and_resolution_are_rejected(work):
    tl = SynthTimeline(fps="25/1", frames=100)
    m = make_master(work, tl, gop=25)
    other_rate = SynthTimeline(fps="30/1", frames=120)
    with pytest.raises(ExportError) as e:
        Exporter(Emitter(quiet=True)).smart_export(m, str(work / "a.mp4"), [Revision(30, 40)],
                                                   SyntheticRenderSource(other_rate), options(work))
    assert "frame rate" in str(e.value)
    other_res = SynthTimeline(width=640, height=360, fps="25/1", frames=100)
    with pytest.raises(ExportError) as e:
        Exporter(Emitter(quiet=True)).smart_export(m, str(work / "b.mp4"), [Revision(30, 40)],
                                                   SyntheticRenderSource(other_res), options(work))
    assert e.value.code == "resolution_mismatch"


def test_wrong_master_for_timeline_is_detected(work):
    """Master rendered from a timeline that is offset by 3 frames (e.g. wrong
    master file or moved timeline): boundary/guard checks must catch it."""
    tl = SynthTimeline(fps="25/1", frames=200)
    shifted = SynthTimeline(fps="25/1", frames=203, duration_change=DurationChange(at=0, remove=0, insert=3))
    m = make_master(work, shifted.revised(duration_change=DurationChange(at=0, remove=0, insert=3)), gop=50)
    m_an = analyze_master(m)
    tl2 = SynthTimeline(fps="25/1", frames=m_an.video.frame_count)
    rev = tl2.revised([VideoChange(100, 110)])
    with pytest.raises(ExportError) as e:
        run_export(work, m, [Revision(100, 110, audio=False)], rev)
    assert e.value.code == "verification_failed"


def test_corrupted_patch_is_rejected(work, monkeypatch):
    tl = SynthTimeline(fps="25/1", frames=100)
    m = make_master(work, tl, gop=25)
    import srx.exporter as ex

    real = ex.encode_segment

    def corrupt(*a, **kw):
        out = real(*a, **kw)
        with open(out, "r+b") as f:
            f.truncate(os.path.getsize(out) // 2)
        return out
    monkeypatch.setattr(ex, "encode_segment", corrupt)
    with pytest.raises(ExportError):
        run_export(work, m, [Revision(30, 40)], tl.revised([VideoChange(30, 40)]))
    assert not os.path.exists(work / "out.mp4")


def test_disk_space_exhaustion_is_detected(work, monkeypatch):
    tl = SynthTimeline(fps="25/1", frames=60)
    m = make_master(work, tl, gop=30)
    import shutil
    from collections import namedtuple
    U = namedtuple("U", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda p: U(10 ** 9, 10 ** 9, 1000))
    with pytest.raises(ExportError) as e:
        run_export(work, m, [Revision(10, 20)], tl.revised([VideoChange(10, 20)]))
    assert e.value.code == "disk_space"


# ---------------------------------------------------------------- interruption
def _cli_export(work, master, spec_path, out, extra=()):
    env = dict(os.environ, SRX_HOME=str(work / "home"), PYTHONPATH=ENGINE)
    return subprocess.Popen([sys.executable, "-m", "srx", "export", master, "-o", out, "--rev", "100:400",
                             "--source", f"synthetic:{spec_path}", "--preset", "veryslow", "--json", *extra],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=ENGINE)


def test_interrupted_export_leaves_master_untouched(work):
    tl = SynthTimeline(width=640, height=360, fps="25/1", frames=500)
    m = make_master(work, tl, gop=250)
    before = sha(m)
    rev = tl.revised([VideoChange(100, 400)])
    spec = work / "spec.json"
    spec.write_text(rev.to_json())
    out = str(work / "out.mp4")
    p = _cli_export(work, m, str(spec), out)
    # wait until encoding has started, then cancel like the app's Cancel button (SIGINT)
    t0 = time.time()
    seen = []
    while time.time() - t0 < 120:
        line = p.stdout.readline().decode()
        if not line:
            break
        seen.append(line)
        if '"stage": "encode"' in line:
            time.sleep(0.5)
            p.send_signal(signal.SIGINT)
            break
    p.wait(timeout=120)
    assert p.returncode == 130, "".join(seen)[-2000:]
    assert sha(m) == before
    assert not os.path.exists(out)
    assert not [f for f in os.listdir(work) if "srx-partial" in f]
    jobs = list_jobs(str(work / "home" / "jobs"))
    assert jobs[-1]["state"] == "cancelled"
    assert not os.path.exists(os.path.join(jobs[-1]["dir"], "tmp"))


def test_crash_recovery(work):
    tl = SynthTimeline(width=640, height=360, fps="25/1", frames=500)
    m = make_master(work, tl, gop=250)
    rev = tl.revised([VideoChange(100, 400)])
    spec = work / "spec.json"
    spec.write_text(rev.to_json())
    out = str(work / "out.mp4")
    p = _cli_export(work, m, str(spec), out)
    t0 = time.time()
    while time.time() - t0 < 120:
        line = p.stdout.readline().decode()
        if not line or '"stage": "encode"' in line:
            break
    p.kill()  # simulated crash: no cleanup handlers run
    p.wait()
    jobs = list_jobs(str(work / "home" / "jobs"))
    assert jobs[-1]["state"] == "running"
    rec = recover_jobs(str(work / "home" / "jobs"))
    assert rec and rec[0]["id"] == jobs[-1]["id"]
    jobs = list_jobs(str(work / "home" / "jobs"))
    assert jobs[-1]["state"] == "interrupted"
    assert not os.path.exists(os.path.join(jobs[-1]["dir"], "tmp"))
    assert not os.path.exists(out)


# ---------------------------------------------------------------- audio specifics
def test_full_audio_reencode_option(work):
    tl = SynthTimeline(fps="30000/1001", frames=300)
    m = make_master(work, tl, gop=60)
    rev = tl.revised([VideoChange(100, 120)], [AudioChange(100, 120)])
    res = run_export(work, m, [Revision(100, 120)], rev, audio_strategy="full")
    rep = res["report_data"]
    assert rep["status"] == "passed", rep["failures"]
    a = rep["audio"][0]
    assert a["strategy"] == "full"
    assert all(w["lag"] == 0 for w in a["alignment_windows"])


def test_pns_master_audio_splice_is_not_silently_accepted(work):
    """FFmpeg's AAC encoder can use perceptual noise substitution; the decoder's
    noise generator state then differs after a splice.  The engine must either
    prove bit-identity or refuse - never claim success without it."""
    tl = SynthTimeline(fps="25/1", frames=250)
    m = make_master(work, tl, gop=50, aac_pns=True, aac_bitrate="64k")
    rev = tl.revised([], [AudioChange(100, 130)])
    try:
        res = run_export(work, m, [Revision(100, 130, video=False)], rev)
    except ExportError as e:
        assert e.value.code if hasattr(e, "value") else True
        assert "audio" in str(e)
        return
    rep = res["report_data"]
    pcm = rep["audio"][0]["pcm_outside_transitions"]
    assert pcm["differing"] == 0  # success is only allowed with proven identity
