"""Phase A: computer-vision accuracy against synthetic charts with known ground truth.

Thresholds are in source pixels. Source strokes in these charts are 1.4-13.5
px wide (OpenCV antialiased widths), the default highlight is ~7 px, so a
mean centre-line error below ~0.7 px and endpoints within ~2 px are
invisible at normal viewing scale.
"""

import json
import os

import numpy as np
import pytest

import metrics
import synth
from maxtrace import detect

RESULTS: dict = {}

# (mean, p95, gt_max, covered) limits. gt_max is the worst distance from any
# ground-truth point to the detected path; covered is the fraction of ground
# truth within 2 px. Occluded charts allow the hidden span. The 1080p case is a
# 300-point random walk whose 6 px line has double corners closer than two
# line widths (the corners are visually merged in the source itself).
LIMITS = {
    "default": (0.7, 2.0, 6.5, 0.97),
    "07_multiple_lines_pick_blue": (0.7, 2.0, 14.0, 0.97),  # crossings hide the line
    "08_partially_interrupted": (0.7, 2.0, 14.0, 0.97),  # label box hides ~52 px
    "09_financial_1080p": (0.7, 2.0, 8.0, 0.94),
}

# Max fraction of the source line's ink left uncovered by the default 7 px
# highlight (scaled to resolution, never thinner than source + 1.5 px).
UNCOVERED = {"default": 0.005, "07_multiple_lines_pick_blue": 0.02, "08_partially_interrupted": 0.02, "09_financial_1080p": 0.02}


def uncovered_fraction(chart, line):
    """Fraction of the source line's ink not hidden by the default highlight."""
    from maxtrace.render import StrokeStyle, render_still
    from maxtrace.worker import thickness_in_source

    W, H = chart.size
    img = np.full((H, W, 3), 255, np.uint8)
    synth.draw_series(img, chart.gt)
    ink = (255 - img.min(axis=2)).astype(np.float32) / 255 > 0.5
    T = max(thickness_in_source({"thickness": 7}, W, H, 1920, 1080), line.thickness + 1.5)
    a = render_still(line.path, W, H, StrokeStyle(color=(1, 0, 0), thickness=T), 1.0)
    return float((ink & (a < 0.5)).sum()) / max(1, int(ink.sum()))


def _detect(chart):
    params = detect.DetectParams(mode="color", color_hex=chart.pick_hex) if chart.pick_hex else detect.DetectParams()
    return detect.analyze(chart.rgb.astype(np.float32) / 255.0, params)


@pytest.mark.parametrize("case", synth.ALL_CASES, ids=lambda f: f.__name__)
def test_trace_matches_ground_truth(case):
    chart = case()
    analysis = _detect(chart)
    line = analysis.selected_line()
    m = metrics.alignment(line.path, chart.gt.points)
    RESULTS[chart.name] = {k: round(v, 3) for k, v in m.items()} | {
        "points": int(len(line.path)),
        "thickness": round(line.thickness, 2),
        "confidence": round(line.confidence, 3),
        "method": line.method,
        "kind": line.kind,
        "size": list(chart.size),
    }
    mean_l, p95_l, gtmax_l, cov_l = LIMITS.get(chart.name, LIMITS["default"])
    assert m["mean_px"] <= mean_l, m
    assert m["p95_px"] <= p95_l, m
    assert m["gt_max_px"] <= gtmax_l, m
    assert m["covered_frac"] >= cov_l, m
    unc = uncovered_fraction(chart, line)
    RESULTS[chart.name]["uncovered_ink"] = round(unc, 5)
    assert unc <= UNCOVERED.get(chart.name, UNCOVERED["default"]), unc
    assert m["start_err_px"] <= 2.5 and m["end_err_px"] <= 2.5, m
    assert line.confidence >= 0.5
    # Simplification must keep far fewer points than one per column.
    assert len(line.path) < 0.4 * (chart.gt.points[:, 0].max() - chart.gt.points[:, 0].min())


def test_multiple_lines_are_all_candidates():
    chart = synth.case_multi_lines()
    analysis = detect.analyze(chart.rgb.astype(np.float32) / 255.0, detect.DetectParams())
    assert len(analysis.lines) >= 3
    for s in chart.series:
        best = min(metrics.alignment(l.path, s.points)["mean_px"] for l in analysis.lines)
        assert best < 0.7
    assert any("Several graph lines" in w for w in analysis.warnings)


def test_candidate_selection_by_color_is_stable():
    chart = synth.case_multi_lines()
    rgb = chart.rgb.astype(np.float32) / 255.0
    a = detect.analyze(rgb, detect.DetectParams())
    blue = min(a.lines, key=lambda l: metrics.alignment(l.path, chart.series[1].points)["mean_px"])
    hex_ = blue.summary(a.width, a.height)["color"]
    b = detect.analyze(rgb, detect.DetectParams(candidate=blue.id, candidate_hex=hex_))
    assert metrics.alignment(b.selected_line().path, chart.series[1].points)["mean_px"] < 0.7


def test_split_colour_line_is_joined_and_flagged():
    chart = synth.case_already_highlighted()
    a = _detect(chart)
    line = a.selected_line()
    assert line.kind == "joined"
    assert len(line.parts) == 2 and line.parts[0]["to"] == pytest.approx(0.55, abs=0.06)
    assert any("changes colour" in n for n in line.notes)


def test_manual_region_restricts_detection():
    chart = synth.case_multi_lines()
    rgb = chart.rgb.astype(np.float32) / 255.0
    # Region covering only the left half: path must stay inside it.
    a = detect.analyze(rgb, detect.DetectParams(mode="color", color_hex=chart.pick_hex, region=(0.0, 0.0, 0.5, 1.0)))
    assert a.selected_line().path[:, 0].max() <= 0.5 * a.width + 1


def test_no_line_reports_reason():
    blank = np.ones((400, 600, 3), np.float32)
    with pytest.raises(detect.DetectionError) as e:
        detect.analyze(blank, detect.DetectParams())
    assert e.value.code in ("no_colors", "no_line")


def test_picked_background_colour_is_rejected():
    chart = synth.case_red_zigzag()
    with pytest.raises(detect.DetectionError) as e:
        detect.analyze(chart.rgb.astype(np.float32) / 255.0, detect.DetectParams(mode="color", color_hex="#FFFFFF"))
    assert e.value.code == "color_is_background"


def test_resolution_independence_scaled_copy():
    """The same chart at 1x and 2x must trace to the same normalised path."""
    import cv2

    chart = synth.case_red_zigzag()
    rgb = chart.rgb.astype(np.float32) / 255.0
    a = detect.analyze(rgb, detect.DetectParams()).selected_line().path
    big = cv2.resize(rgb, (rgb.shape[1] * 2, rgb.shape[0] * 2), interpolation=cv2.INTER_CUBIC)
    b = detect.analyze(np.clip(big, 0, 1), detect.DetectParams()).selected_line().path / 2.0
    m = metrics.alignment(b, a)
    assert m["mean_px"] < 0.5 and m["gt_max_px"] < 3.0


def teardown_module(module):
    out = os.environ.get("MAXTRACE_TEST_REPORT")
    if out and RESULTS:
        with open(out, "w") as f:
            json.dump(RESULTS, f, indent=1, sort_keys=True)
