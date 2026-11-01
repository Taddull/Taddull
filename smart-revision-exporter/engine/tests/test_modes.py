"""Revision-Ready Master, Safe Full Export, Resolve bridge (mock), CLI request
mode and manual render import."""

import json
import os
import subprocess
import sys

import pytest

from conftest import ENGINE, Revision, SynthTimeline, VideoChange, AudioChange, framehashes, make_master, options
from srx.events import Emitter
from srx.exporter import Exporter
from srx.media import analyze_master
from srx.render import FileRenderSource, ManualRender, SyntheticRenderSource


def _cli(work, *args, env_extra=None):
    env = dict(os.environ, SRX_HOME=str(work / "home"), PYTHONPATH=ENGINE)
    env.update(env_extra or {})
    r = subprocess.run([sys.executable, "-m", "srx", *args], capture_output=True, text=True, env=env, cwd=ENGINE)
    def strict(c):
        raise ValueError(f"non-standard JSON constant {c}")
    # every line must be strict JSON (the Swift app's decoder rejects NaN/Infinity)
    events = [json.loads(l, parse_constant=strict) for l in r.stdout.splitlines() if l.startswith("{")]
    return r.returncode, events, r.stderr


@pytest.mark.parametrize("gop", [1, 25])
def test_revision_ready_master_then_patch(work, gop):
    tl = SynthTimeline(fps="25/1", frames=200)
    src = SyntheticRenderSource(tl)
    em = Emitter(quiet=True)
    out = str(work / "rr.mp4")
    res = Exporter(em).encode_full(src, out, 0, 200, tl.rate, "revision-ready", options(work), gop=gop)
    assert res["verification"] == "passed"
    a = analyze_master(out).video
    assert set(range(0, 200, gop)) <= set(a.resume_points)
    rep = json.load(open(res["report"]))
    assert rep["tradeoffs"]["structure"]
    # a later patch on the revision-ready master touches at most one GOP of unchanged frames
    rev = tl.revised([VideoChange(103, 111)], [AudioChange(103, 111)])
    r2 = Exporter(Emitter(quiet=True)).smart_export(out, str(work / "rr_v2.mp4"), [Revision(103, 111)],
                                                    SyntheticRenderSource(rev), options(work))
    rep2 = json.load(open(r2["report"]))
    assert rep2["status"] == "passed"
    assert rep2["video"]["boundary_frames"] <= max(0, gop - 1) + 3
    if gop == 1:
        assert rep2["video"]["boundary_frames"] == 0


def test_safe_full_export(work):
    tl = SynthTimeline(fps="30000/1001", frames=150)
    m = make_master(work, tl, gop=60)
    rev = tl.revised([VideoChange(10, 20)])
    out = str(work / "full.mp4")
    res = Exporter(Emitter(quiet=True)).encode_full(SyntheticRenderSource(rev), out, 0, 150, tl.rate,
                                                    "full-export", options(work), reference=m)
    assert res["verification"] == "passed"
    rep = json.load(open(res["report"]))
    names = {c["name"]: c["status"] for c in rep["checks"]}
    assert names["frame_count"] == names["color_metadata"] == names["decode"] == "pass"
    assert analyze_master(out).video.frame_count == 150


def test_manual_render_import_source(work):
    """Fallback when Resolve scripting is unavailable: the user renders the
    requested range manually; the engine validates and uses it."""
    tl = SynthTimeline(fps="25/1", frames=200, start_frame=90000)
    m = make_master(work, tl, gop=50)
    rev = tl.revised([VideoChange(70, 85)], [AudioChange(70, 85)])
    manual = str(work / "manual_render.mov")
    rev.render_intermediate(40, 120, manual)  # user rendered a generous range around the revision
    src = FileRenderSource([ManualRender(manual, 90000 + 40)], tl.rate)
    res = Exporter(Emitter(quiet=True)).smart_export(m, str(work / "o.mp4"), [Revision(70, 85)], src,
                                                     options(work, timeline_offset=90000))
    assert json.load(open(res["report"]))["status"] == "passed"


def test_manual_render_not_covering_range_is_reported(work):
    tl = SynthTimeline(fps="25/1", frames=200)
    m = make_master(work, tl, gop=50)
    rev = tl.revised([VideoChange(70, 85)])
    manual = str(work / "manual_render.mov")
    rev.render_intermediate(72, 80, manual)
    src = FileRenderSource([ManualRender(manual, 72)], tl.rate)
    with pytest.raises(Exception) as e:
        Exporter(Emitter(quiet=True)).smart_export(m, str(work / "o.mp4"), [Revision(70, 85)], src, options(work))
    assert "no imported render covers" in str(e.value)


def test_cli_doctor_probe_plan(work):
    tl = SynthTimeline(fps="25/1", frames=100)
    m = make_master(work, tl, gop=25)
    code, ev, err = _cli(work, "doctor", "--json", "--no-resolve")
    assert code == 0 and ev[-1]["ok"]
    code, ev, err = _cli(work, "probe", m, "--json", "--gop-map")
    assert code == 0 and ev[-1]["probe"]["video"]["frame_count"] == 100
    assert len(ev[-1]["probe"]["frame_types"]) == 100
    code, ev, err = _cli(work, "plan", m, "--rev", "30:40", "--json")
    assert code == 0 and ev[-1]["plan"]["stats"]["revised_frames"] == 10


def test_cli_request_export_with_resolve_mock(work):
    """Exercises ResolveSession/ResolveRenderSource against the API mock:
    render-job creation, settings, polling, output discovery, cleanup and
    restoration of the user's render settings."""
    tl = SynthTimeline(fps="24000/1001", frames=240, start_frame=86400)
    m = make_master(work, tl, gop=48)
    rev = tl.revised([VideoChange(100, 124)], [AudioChange(100, 124)])
    mock = work / "mock.json"
    mock.write_text(json.dumps({"timeline": json.loads(rev.to_json()), "project": "Documentary",
                                "timeline_name": "Edit v7", "mark_in": 86500, "mark_out": 86523,
                                "markers": {"150": {"color": "Purple", "duration": 10, "name": "REV logo",
                                                    "note": "", "customData": ""}}}))
    env = {"SRX_RESOLVE_MOCK": str(mock)}
    code, ev, err = _cli(work, "resolve", "status", "--json", env_extra=env)
    st = ev[-1]["resolve"]
    assert st["connected"] and st["timeline"]["fps"] == "24000/1001" and st["timeline"]["start_frame"] == 86400
    assert st["api"]["Timeline.GetMarkInOut"]
    code, ev, err = _cli(work, "resolve", "ranges", "--json", env_extra=env)
    ranges = ev[-1]["ranges"]
    assert ranges[0] == {**ranges[0], "start": 86500, "end": 86524, "master_start": 100, "master_end": 124}
    assert any(r["source"] == "marker" and r["master_start"] == 150 for r in ranges)
    req = {"master": m, "output": str(work / "out.mp4"), "mode": "verified", "preset": "veryfast",
           "revisions": [{"start": 86500, "end": 86524, "label": "In/Out"}], "revision_units": "timeline",
           "source": {"type": "resolve"}}
    (work / "req.json").write_text(json.dumps(req))
    code, ev, err = _cli(work, "export", "--request", str(work / "req.json"), "--json", env_extra=env)
    res = [e for e in ev if e["type"] == "result"]
    assert code == 0, [e for e in ev if e["type"] == "error"]
    assert res and res[-1]["verification"] == "passed"
    types = {e["type"] for e in ev}
    assert {"job", "stage", "progress", "plan", "master", "result"} <= types
    assert any(e["type"] == "log" and "Resolve render job" in e["message"] for e in ev)
    report = json.loads(open(res[-1]["report"]).read(), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert report["status"] == "passed"


def test_cli_resolve_not_running(work):
    code, ev, err = _cli(work, "resolve", "status", "--json", "--timeout", "0.5",
                         env_extra={"SRX_RESOLVE_MOCK": "offline"})
    st = ev[-1]["resolve"]
    assert not st["connected"] and st["code"] == "resolve_not_running"


def test_cli_resolve_render_failure(work):
    tl = SynthTimeline(fps="25/1", frames=120)
    m = make_master(work, tl, gop=25)
    mock = work / "mock.json"
    mock.write_text(json.dumps({"timeline": json.loads(tl.to_json()), "fail_render": True}))
    code, ev, err = _cli(work, "export", m, "-o", str(work / "o.mp4"), "--rev", "30:40", "--source", "resolve",
                         "--json", env_extra={"SRX_RESOLVE_MOCK": str(mock)})
    assert code == 1
    errs = [e for e in ev if e["type"] == "error"]
    assert errs and "render failed" in errs[-1]["message"].lower()
    assert not os.path.exists(work / "o.mp4")


def test_cli_frame_and_filmstrip(work):
    tl = SynthTimeline(fps="25/1", frames=100)
    m = make_master(work, tl, gop=25)
    code, ev, _ = _cli(work, "frame", m, "--index", "57", "-o", str(work / "f.png"), "--json")
    assert code == 0 and os.path.getsize(work / "f.png") > 0
    # exactness: the PNG must equal frame 57 decoded directly
    a = subprocess.run(["ffmpeg", "-v", "error", "-i", str(work / "f.png"), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True).stdout
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", m, "-vf", "select=eq(n\\,57)", "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    assert a == b
    code, ev, _ = _cli(work, "filmstrip", m, "-o", str(work / "s.png"), "--tiles", "10", "--json")
    assert code == 0 and os.path.getsize(work / "s.png") > 0


def test_resolve_full_audio_reencode_renders_audio_only(work):
    """Full-track audio re-encode must not trigger a full video render."""
    import importlib
    from srx import resolve_mock
    from srx.resolve_bridge import ResolveRenderSource, ResolveSession
    tl = SynthTimeline(fps="25/1", frames=200)
    m = make_master(work, tl, gop=50)
    rev = tl.revised([VideoChange(80, 95)], [AudioChange(80, 95)])
    mock = work / "mock.json"
    mock.write_text(json.dumps({"timeline": json.loads(rev.to_json())}))
    os.environ["SRX_RESOLVE_MOCK"] = str(mock)
    try:
        resolve_mock.reset()
        src = ResolveRenderSource(ResolveSession(resolve_mock).connect())
        res = Exporter(Emitter(quiet=True)).smart_export(m, str(work / "o.mp4"), [Revision(80, 95)], src,
                                                         options(work, audio_strategy="full"))
        assert json.load(open(res["report"]))["status"] == "passed"
        log = resolve_mock._INSTANCE.pm.project.render_log
        full = [r for r in log if r["end"] - r["start"] >= 200]
        assert full and all(not r["video"] for r in full)
        assert sum(r["end"] - r["start"] for r in log if r["video"]) < 60
    finally:
        os.environ.pop("SRX_RESOLVE_MOCK", None)
        resolve_mock.reset()
