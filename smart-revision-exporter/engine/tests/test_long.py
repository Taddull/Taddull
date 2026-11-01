"""Requirement 1: a five-second revision in a 15-minute H.264 master.

Run with:  python3 -m pytest tests/test_long.py -m slow
Resolution is reduced (480x270) so the synthetic master can be generated in CI
time; the patch logic is resolution independent.
"""

import json
import time

import pytest

from conftest import AudioChange, Revision, SynthTimeline, VideoChange, independent_identity, make_master, run_export


@pytest.mark.slow
def test_five_second_revision_in_fifteen_minute_master(work):
    fps = "30000/1001"
    frames = 26973  # 15:00 at 29.97 fps
    tl = SynthTimeline(width=480, height=270, fps=fps, frames=frames, start_frame=107892)  # 01:00:00;00 DF
    t0 = time.time()
    m = make_master(work, tl, gop=250, bframes=3, preset="ultrafast", crf=23)
    gen = time.time() - t0
    a, b = 13500, 13650  # 5.0 s at 7:30
    rev = tl.revised([VideoChange(a, b)], [AudioChange(a, b)])
    t0 = time.time()
    res = run_export(work, m, [Revision(a, b)], rev)
    elapsed = time.time() - t0
    rep = res["report_data"]
    assert rep["status"] == "passed", rep["failures"]
    st = rep["plan_stats"]
    assert st["revised_frames"] == 150
    assert st["rendered_percent"] < 2.0          # minimum necessary rendering
    assert rep["video"]["identical_unchanged"] == rep["video"]["compared_unchanged"] >= frames - 400
    same, preserved, n_out, n_master = independent_identity(m, str(work / "out.mp4"), rep)
    assert same == preserved and n_out == n_master == frames
    print(json.dumps({"generate_master_s": round(gen, 1), "export_s": round(elapsed, 1),
                      "timings": rep["timings_s"], "stats": st}, indent=1))
