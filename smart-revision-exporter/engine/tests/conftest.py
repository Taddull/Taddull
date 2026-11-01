"""Shared fixtures: synthetic masters, export runner and an independent checker.

The independent checker decodes files with FFmpeg's own framehash muxer
(SHA-256, no code shared with srx.verify) so tests do not rely solely on the
engine's verifier to judge the engine.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import List, Optional

import pytest

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ENGINE)

from srx.events import Emitter  # noqa: E402
from srx.exporter import ExportOptions, Exporter  # noqa: E402
from srx.plan import Revision  # noqa: E402
from srx.render import SyntheticRenderSource  # noqa: E402
from srx.synthetic import AudioChange, SynthTimeline, VideoChange  # noqa: E402


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: long-running test (15-minute master)")


@pytest.fixture
def work(tmp_path):
    d = tmp_path
    (d / "jobs").mkdir()
    (d / "cache").mkdir()
    (d / "projects").mkdir()
    return d


def make_master(work, tl: SynthTimeline, name="master.mp4", **kw) -> str:
    path = str(work / name)
    tl.render_master(path, **kw)
    return path


def options(work, **kw) -> ExportOptions:
    base = dict(mode="verified", job_root=str(work / "jobs"), cache_dir=str(work / "cache"),
                project_root=str(work / "projects"), preset="veryfast", keep_temp=False)
    base.update(kw)
    return ExportOptions(**base)


def run_export(work, master: str, revisions: List[Revision], revised: SynthTimeline, out_name="out.mp4",
               **kw) -> dict:
    out = str(work / out_name)
    em = Emitter(json_mode=False, quiet=True)
    res = Exporter(em).smart_export(master, out, revisions, SyntheticRenderSource(revised),
                                    options(work, timeline_offset=revised.start_frame, **kw))
    with open(res["report"]) as f:
        res["report_data"] = json.load(f)
    return res


def framehashes(path: str) -> List[str]:
    """Independent per-frame SHA-256 via FFmpeg's framehash muxer."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:v:0", "-fps_mode", "passthrough",
                        "-f", "framehash", "-hash", "sha256", "-"], capture_output=True, text=True, check=True)
    out = []
    for line in r.stdout.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        out.append(line.split(",")[-1].strip())
    return out


def audiohashes(path: str) -> List[str]:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-f", "framehash", "-hash", "sha256",
                        "-"], capture_output=True, text=True, check=True)
    return [ln.split(",")[-1].strip() for ln in r.stdout.splitlines() if ln.strip() and not ln.startswith("#")]


def frame_pts(path: str) -> List[float]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time",
                        "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    vals = [x.strip().strip(",") for x in r.stdout.split()]
    return [float(x) for x in vals if x and x != "N/A"]


def independent_identity(master: str, output: str, report: dict):
    """Check with FFmpeg framehash that every preserved frame is identical and
    return (identical_count, preserved_count, differing_reencoded_count)."""
    hm = framehashes(master)
    ho = framehashes(output)
    segs = report["video"]["segments"]
    preserved = []
    reenc = []
    for s in segs:
        rng = list(range(s["output"][0], s["output"][1]))
        if s["kind"] == "copy":
            preserved += [(j, s["master"][0] + (j - s["output"][0])) for j in rng]
        else:
            reenc += rng
    same = sum(1 for j, m in preserved if ho[j] == hm[m])
    return same, len(preserved), len(ho), len(hm)


__all__ = ["make_master", "run_export", "options", "framehashes", "audiohashes", "frame_pts",
           "independent_identity", "SynthTimeline", "VideoChange", "AudioChange", "Revision"]
