"""Phase B: reveal animation correctness of the rendered output."""

import os

import cv2
import numpy as np
import pytest

from maxtrace import geometry as geo
from maxtrace.easing import Curve, duration_to_frames, frame_progress
from maxtrace.render import SequenceSpec, StrokeStyle, render_sequence, render_still

W, H = 640, 360
PATH = np.array([[40.0, 300.0], [140.0, 80.0], [200.0, 260.0], [330.0, 60.0], [420.0, 240.0], [600.0, 120.0]])


def _alpha(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    assert img is not None and img.shape == (H, W, 4)
    return img[:, :, 3].astype(np.float32) / 255.0, img


def _seq(tmp_path, curve="linear", start=10, frames=30, comp=(0, 60), style=None):
    style = style or StrokeStyle(color=(1.0, 0.125, 0.125), thickness=8.0, softness=0.1)
    spec = SequenceSpec(comp[0], comp[1], start, frames, Curve.from_settings(curve))
    info = render_sequence(PATH, W, H, style, spec, str(tmp_path))
    files = sorted(os.listdir(tmp_path))
    return info, [os.path.join(tmp_path, f) for f in files if f.endswith(".png")]


def test_frame_count_and_duration(tmp_path):
    info, files = _seq(tmp_path)
    assert info["frames"] == 61 and len(files) == 61
    assert duration_to_frames(2.5, 24) == 60
    assert duration_to_frames(2.5, 29.97) == 75
    assert duration_to_frames(0.5, 60) == 30


def test_invisible_before_and_at_start_full_at_end(tmp_path):
    info, files = _seq(tmp_path)
    for i in range(0, 11):  # comp frames 0..10, start = 10
        a, _ = _alpha(files[i])
        assert a.max() == 0.0, f"frame {i} not empty"
    a_mid, _ = _alpha(files[25])
    a_end, _ = _alpha(files[40])
    assert 0 < a_mid.sum() < a_end.sum()
    # Held after the end, identical pixels (hard links or copies).
    for i in range(40, 61):
        a, _ = _alpha(files[i])
        assert np.array_equal(a, a_end)


def test_full_line_reached_and_covers_path(tmp_path):
    info, files = _seq(tmp_path)
    a_end, _ = _alpha(files[40])
    samples = np.array([geo.point_at_length(PATH, s) for s in np.linspace(0, geo.total_length(PATH), 400)])
    vals = a_end[np.floor(samples[:, 1]).astype(int), np.floor(samples[:, 0]).astype(int)]
    assert (vals > 0.95).all()


def test_monotonic_no_erasing_no_flicker(tmp_path):
    info, files = _seq(tmp_path)
    prev = None
    for f in files:
        a, _ = _alpha(f)
        if prev is not None:
            assert (a >= prev - 1.0 / 255.0).all(), "pixels disappeared (erasing/flicker)"
        prev = a


def test_reveal_direction_first_to_last(tmp_path):
    info, files = _seq(tmp_path)
    a, _ = _alpha(files[14])
    ys, xs = np.nonzero(a > 0.5)
    assert xs.max() < 200  # early frames only show the beginning of the path
    p0 = PATH[0]
    assert a[int(p0[1]), int(p0[0])] > 0.9


def test_linear_mode_constant_arc_length_speed(tmp_path):
    """Revealed length grows by equal amounts per frame (arc length, not points)."""
    path = np.array([[20.0, 180.0], [300.0, 180.0]] + [[300.0 + 4 * k, 180.0 + (12 if k % 2 else -12)] for k in range(1, 70)])
    style = StrokeStyle(color=(1, 1, 1), thickness=4.0)
    spec = SequenceSpec(0, 40, 0, 40, Curve.from_settings("linear"))
    info = render_sequence(path, W, H, style, spec, str(tmp_path))
    areas = []
    for i in range(41):
        a, _ = _alpha(os.path.join(tmp_path, f"MaxTrace_{i:05d}.png"))
        areas.append(a.sum())
    inc = np.diff(areas)[2:-2]
    # The first half is one long straight segment with 2 points, the second
    # half dozens of short segments: with arc-length timing increments stay equal.
    assert inc.std() / inc.mean() < 0.12


def test_easing_curves():
    lin = Curve.from_settings("linear")
    sm = Curve.from_settings("smooth")
    nat = Curve.from_settings("natural")
    x = np.linspace(0, 1, 11)
    assert np.allclose(lin.progress(x), x)
    p = sm.progress(x)
    assert p[0] == 0 and p[-1] == pytest.approx(1.0)
    assert np.all(np.diff(p) >= -1e-9)
    assert p[1] < 0.1 and p[5] == pytest.approx(0.5, abs=0.01)  # ease in/out symmetric
    q = nat.progress(x)
    assert np.all(np.diff(q) >= -1e-9) and q[-1] == pytest.approx(1.0)
    # Natural: no excessive acceleration -> max per-step change bounded
    assert np.max(np.diff(q)) < 0.25
    c = Curve.from_settings("custom", (0.2, 0.0, 0.2, 1.0))
    assert c.progress(np.array([1.0]))[0] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        Curve.from_settings("custom", (1.5, 0, 0.2, 1))


def test_progress_reaches_one_exactly_on_last_frame():
    c = Curve.from_settings("smooth")
    p = frame_progress(c, 100, 60, np.array([99, 100, 130, 160, 161]))
    assert p[0] == 0 and p[1] == 0 and 0 < p[2] < 1 and p[3] == pytest.approx(1.0) and p[4] == pytest.approx(1.0)


def test_trace_range_trims_exactly():
    L = geo.total_length(PATH)
    sub = geo.trim_fraction(PATH, 0.0, 0.58)
    assert geo.total_length(sub) == pytest.approx(0.58 * L, rel=1e-9)
    mid = geo.trim_fraction(PATH, 0.2, 0.6)
    assert geo.total_length(mid) == pytest.approx(0.4 * L, rel=1e-9)
    # Trimmed path lies exactly on the original geometry.
    d = geo.distance_to_polyline(mid, PATH)
    assert d.max() < 1e-9


def test_colour_and_opacity(tmp_path):
    style = StrokeStyle(color=(1.0, 0.82, 0.12), thickness=10.0, opacity=0.6)
    spec = SequenceSpec(0, 5, 0, 5, Curve.from_settings("linear"))
    render_sequence(PATH, W, H, style, spec, str(tmp_path))
    a, img = _alpha(os.path.join(tmp_path, "MaxTrace_00005.png"))
    assert a.max() == pytest.approx(0.6, abs=0.01)
    on = a > 0.3
    bgr = img[:, :, :3][on].mean(axis=0)
    assert np.allclose(bgr[::-1] / 255.0, style.color, atol=0.01)  # straight (unpremultiplied) colour


def test_thick_strokes_are_antialiased():
    a = render_still(PATH, W, H, StrokeStyle(color=(1, 0, 0), thickness=24.0), 1.0)
    edge = (a > 0.02) & (a < 0.98)
    inside = a >= 0.98
    # A sizeable band of fractional coverage along the edges, not a binary mask.
    assert edge.sum() > 0.04 * inside.sum()
    # Round caps: the coverage extends half a width beyond the end point.
    e = PATH[-1]
    assert a[int(e[1]), int(e[0] + 10)] > 0.9 and a[int(e[1]), int(e[0] + 14)] < 0.1


def test_softness_halo_glow_increase_soft_area_only_modestly():
    base = render_still(PATH, W, H, StrokeStyle(color=(1, 0, 0), thickness=8.0), 1.0)
    soft = render_still(PATH, W, H, StrokeStyle(color=(1, 0, 0), thickness=8.0, halo=0.4), 1.0)
    glow = render_still(PATH, W, H, StrokeStyle(color=(1, 0, 0), thickness=8.0, glow=0.3), 1.0)
    assert soft.sum() > base.sum() and glow.sum() > base.sum()
    # Halo stays subtle: no pixel outside the stroke gets more than ~35% alpha.
    outside = base < 0.01
    assert soft[outside].max() < 0.35 and glow[outside].max() < 0.3
