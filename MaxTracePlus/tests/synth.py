"""Synthetic chart generator with exact ground truth.

Charts are drawn with OpenCV's own antialiased line renderer (independent of
MaxTrace's renderer) at native resolution, with axes, gridlines, labels,
legends and annotations. Ground-truth polylines are stored in MaxTrace's
continuous pixel convention (pixel centre = i + 0.5).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import cv2
import numpy as np

SHIFT = 6


@dataclass
class Series:
    points: np.ndarray  # (N,2) continuous pixel coords
    color: tuple[int, int, int]  # RGB 0..255
    thickness: int


@dataclass
class Chart:
    name: str
    rgb: np.ndarray  # uint8 RGB
    series: list[Series]
    target: int = 0
    jpeg_quality: int | None = None
    pick_hex: str | None = None  # for multi-line tests: colour the user picks
    expect_warning: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def gt(self) -> Series:
        return self.series[self.target]

    @property
    def size(self) -> tuple[int, int]:
        return self.rgb.shape[1], self.rgb.shape[0]


def _cv(pts: np.ndarray) -> np.ndarray:
    return np.round((np.asarray(pts) - 0.5) * (1 << SHIFT)).astype(np.int32)


def _bgr(rgb):
    return (int(rgb[2]), int(rgb[1]), int(rgb[0]))


def draw_series(img_bgr: np.ndarray, s: Series) -> None:
    cv2.polylines(img_bgr, [_cv(s.points)], False, _bgr(s.color), s.thickness, cv2.LINE_AA, SHIFT)


def plot_frame(w: int, h: int, bg=(255, 255, 255), margin=(0.08, 0.10, 0.04, 0.12)):
    left, top, right, bottom = margin
    x0, x1 = int(w * left), int(w * (1 - right))
    y0, y1 = int(h * top), int(h * (1 - bottom))
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = _bgr(bg)
    return img, (x0, y0, x1, y1)


def gridlines(img, box, n=6, color=(225, 225, 225), vertical=True, thickness=1):
    x0, y0, x1, y1 = box
    for i in range(n + 1):
        y = int(y0 + (y1 - y0) * i / n)
        cv2.line(img, (x0, y), (x1, y), _bgr(color), thickness, cv2.LINE_8)
    if vertical:
        for i in range(n + 3):
            x = int(x0 + (x1 - x0) * i / (n + 2))
            cv2.line(img, (x, y0), (x, y1), _bgr(color), thickness, cv2.LINE_8)


def axes(img, box, color=(40, 40, 40), thickness=2, labels=True, scale=1.0):
    x0, y0, x1, y1 = box
    cv2.line(img, (x0, y0), (x0, y1), _bgr(color), thickness, cv2.LINE_AA)
    cv2.line(img, (x0, y1), (x1, y1), _bgr(color), thickness, cv2.LINE_AA)
    if labels:
        fs = 0.55 * scale
        for i in range(7):
            y = int(y0 + (y1 - y0) * i / 6)
            cv2.putText(img, f"{(6 - i) * 50}", (int(x0 - 70 * scale), y + 6), cv2.FONT_HERSHEY_SIMPLEX, fs, _bgr(color), max(1, int(scale)), cv2.LINE_AA)
        for i in range(9):
            x = int(x0 + (x1 - x0) * i / 8)
            cv2.putText(img, f"{2000 + i * 3}", (x - int(22 * scale), int(y1 + 30 * scale)), cv2.FONT_HERSHEY_SIMPLEX, fs, _bgr(color), max(1, int(scale)), cv2.LINE_AA)


def title(img, text, scale=1.0, color=(20, 20, 20)):
    cv2.putText(img, text, (int(40 * scale), int(55 * scale)), cv2.FONT_HERSHEY_DUPLEX, 1.3 * scale, _bgr(color), max(1, int(2 * scale)), cv2.LINE_AA)


def zigzag(box, n, rng, amp=0.35, trend=0.0, sharp=True):
    x0, y0, x1, y1 = box
    xs = np.linspace(x0 + 4, x1 - 4, n + 1)
    mid = (y0 + y1) / 2
    ys = []
    v = 0.0
    for i in range(n + 1):
        if sharp:
            v = (1 if i % 2 else -1) * rng.uniform(0.3, 1.0) * amp + rng.uniform(-0.15, 0.15)
        else:
            v = np.clip(v + rng.uniform(-0.3, 0.3), -1, 1) * amp
        ys.append(mid + (v - trend * (i / n - 0.5)) * (y1 - y0))
    ys = np.clip(np.array(ys), y0 + 8, y1 - 8)
    return np.column_stack([xs, ys])


def random_walk(box, n, rng, vol=0.05, drift=0.0):
    x0, y0, x1, y1 = box
    xs = np.linspace(x0 + 4, x1 - 4, n)
    steps = rng.normal(drift, vol, n)
    v = np.cumsum(steps)
    v = (v - v.min()) / max(1e-9, v.max() - v.min())
    ys = y1 - 10 - v * (y1 - y0 - 20)
    return np.column_stack([xs, ys])


def smooth_curve(box, n=400):
    x0, y0, x1, y1 = box
    t = np.linspace(0, 1, n)
    xs = x0 + 6 + t * (x1 - x0 - 12)
    ys = (y0 + y1) / 2 - (np.sin(t * 2.6 * np.pi) * 0.3 + t * 0.15) * (y1 - y0)
    return np.column_stack([xs, ys])


def finish(img_bgr):
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def jpeg(rgb, q):
    ok, enc = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.cvtColor(cv2.imdecode(enc, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)


# --------------------------------------------------------------------------


def case_red_zigzag(seed=1):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    s = Series(zigzag(box, 28, rng), (225, 32, 32), 4)
    draw_series(img, s)
    return Chart("01_red_zigzag_white", finish(img), [s])


def case_blue_grid(seed=2):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(200, 200, 200))
    axes(img, box)
    s = Series(random_walk(box, 160, rng), (30, 90, 220), 3)
    draw_series(img, s)
    return Chart("02_blue_line_grey_grid", finish(img), [s])


def case_thin_jpeg(seed=3):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(230, 230, 230))
    axes(img, box)
    s = Series(random_walk(box, 220, rng), (20, 60, 160), 1)
    draw_series(img, s)
    c = Chart("03_thin_line_jpeg", jpeg(finish(img), 55), [s])
    c.jpeg_quality = 55
    return c


def case_thick_aa(seed=4):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(235, 235, 235))
    s = Series(zigzag(box, 9, rng, amp=0.3, sharp=False), (20, 160, 60), 12)
    draw_series(img, s)
    return Chart("04_thick_antialiased", finish(img), [s])


def case_many_peaks(seed=5):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(225, 225, 225))
    axes(img, box)
    s = Series(zigzag(box, 90, rng, amp=0.4), (210, 30, 30), 3)
    draw_series(img, s)
    return Chart("05_dozens_of_sharp_peaks", finish(img), [s])


def case_labels_axes(seed=6):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(222, 222, 222), vertical=False)
    axes(img, box)
    title(img, "Global Revenue, 2000-2024 (USD bn)")
    col = (205, 35, 45)
    s = Series(random_walk(box, 120, rng, drift=0.01), col, 4)
    draw_series(img, s)
    # Legend with a swatch in the line colour (classic distractor).
    lx, ly = box[2] - 300, box[1] + 30
    cv2.line(img, (lx, ly), (lx + 60, ly), _bgr(col), 4, cv2.LINE_AA)
    cv2.putText(img, "Revenue", (lx + 75, ly + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, _bgr((40, 40, 40)), 2, cv2.LINE_AA)
    # Annotation in line colour near the end of the line.
    end = s.points[-1]
    cv2.putText(img, "$412bn", (int(end[0]) - 120, int(end[1]) - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, _bgr(col), 2, cv2.LINE_AA)
    return Chart("06_labels_and_axes", finish(img), [s])


def case_multi_lines(seed=7):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(225, 225, 225))
    axes(img, box)
    a = Series(random_walk(box, 140, rng), (220, 40, 40), 3)
    b = Series(random_walk(box, 140, rng), (40, 80, 220), 3)
    c = Series(random_walk(box, 140, rng), (40, 170, 70), 3)
    for s in (a, b, c):
        draw_series(img, s)
    ch = Chart("07_multiple_lines_pick_blue", finish(img), [a, b, c], target=1)
    ch.pick_hex = "#2850DC"
    return ch


def case_interrupted(seed=8):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(225, 225, 225))
    axes(img, box)
    s = Series(random_walk(box, 150, rng), (220, 50, 30), 4)
    draw_series(img, s)
    # Label box occluding ~3% of the width over the line.
    i = int(len(s.points) * 0.55)
    p = s.points[i]
    w = 52
    cv2.rectangle(img, (int(p[0]) - w // 2, int(p[1]) - 26), (int(p[0]) + w // 2, int(p[1]) + 26), (255, 255, 255), -1)
    cv2.putText(img, "Q3", (int(p[0]) - 18, int(p[1]) + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 2, cv2.LINE_AA)
    ch = Chart("08_partially_interrupted", finish(img), [s])
    ch.notes.append("occluded span ~52px")
    return ch


def case_1080p(seed=9):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(228, 228, 228))
    axes(img, box)
    title(img, "S&P 500 Index")
    s = Series(random_walk(box, 300, rng, drift=0.004), (230, 40, 40), 3)
    draw_series(img, s)
    return Chart("09_financial_1080p", finish(img), [s])


def case_4k(seed=10):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(3840, 2160)
    gridlines(img, box, color=(225, 225, 225), thickness=2)
    axes(img, box, thickness=4, scale=2.0)
    title(img, "Inflation rate (%)", scale=2.0)
    s = Series(zigzag(box, 60, rng, amp=0.38), (200, 20, 20), 6)
    draw_series(img, s)
    return Chart("10_graph_4k", finish(img), [s])


def case_dark_theme(seed=11):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080, bg=(14, 16, 22))
    gridlines(img, box, color=(48, 52, 60))
    axes(img, box, color=(150, 150, 150))
    s = Series(random_walk(box, 200, rng), (255, 140, 20), 3)
    draw_series(img, s)
    return Chart("11_dark_theme_orange", finish(img), [s])


def case_already_highlighted(seed=12):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(225, 225, 225))
    axes(img, box)
    pts = random_walk(box, 160, rng)
    k = int(len(pts) * 0.55)
    red = Series(pts[: k + 1], (225, 30, 30), 4)
    blue = Series(pts[k:], (40, 90, 200), 4)
    draw_series(img, blue)
    draw_series(img, red)
    full = Series(pts, (225, 30, 30), 4)
    ch = Chart("12_already_highlighted_split", finish(img), [full, red, blue], target=0)
    ch.expect_warning = "split"
    return ch


def case_black_line_black_axes(seed=13):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1920, 1080)
    axes(img, box, color=(0, 0, 0), thickness=2)
    gridlines(img, box, color=(235, 235, 235), vertical=False)
    title(img, "Unemployment", color=(0, 0, 0))
    s = Series(random_walk(box, 130, rng), (10, 10, 10), 3)
    draw_series(img, s)
    return Chart("13_black_line_black_axes", finish(img), [s])


def case_smooth(seed=14):
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(225, 225, 225))
    s = Series(smooth_curve(box), (130, 40, 200), 5)
    draw_series(img, s)
    return Chart("14_smooth_curve_purple", finish(img), [s])


def case_1440(seed=15):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(2560, 1440)
    gridlines(img, box, color=(225, 225, 225))
    axes(img, box, scale=1.4)
    s = Series(zigzag(box, 45, rng), (240, 180, 0), 5)
    draw_series(img, s)
    return Chart("15_yellow_1440p", finish(img), [s])


def case_odd_size(seed=16):
    rng = np.random.default_rng(seed)
    img, box = plot_frame(1200, 800)
    gridlines(img, box, color=(220, 220, 220))
    axes(img, box, scale=0.8)
    s = Series(random_walk(box, 90, rng), (0, 150, 170), 3)
    draw_series(img, s)
    c = Chart("16_screenshot_1200x800_jpeg", jpeg(finish(img), 80), [s])
    c.jpeg_quality = 80
    return c


ALL_CASES = [
    case_red_zigzag,
    case_blue_grid,
    case_thin_jpeg,
    case_thick_aa,
    case_many_peaks,
    case_labels_axes,
    case_multi_lines,
    case_interrupted,
    case_1080p,
    case_4k,
    case_dark_theme,
    case_already_highlighted,
    case_black_line_black_axes,
    case_smooth,
    case_1440,
    case_odd_size,
]


def save_chart(chart: Chart, directory: str) -> str:
    os.makedirs(directory, exist_ok=True)
    ext = ".jpg" if chart.jpeg_quality else ".png"
    path = os.path.join(directory, chart.name + ext)
    bgr = cv2.cvtColor(chart.rgb, cv2.COLOR_RGB2BGR)
    if chart.jpeg_quality:
        # Already compressed in-memory; store at max quality to avoid double loss.
        cv2.imwrite(path, bgr, [cv2.IMWRITE_JPEG_QUALITY, 100])
    else:
        cv2.imwrite(path, bgr)
    return path


def case_loop_curve(seed=17):
    """Non x-monotonic curve (doubles back) to exercise general-curve mode."""
    img, box = plot_frame(1920, 1080)
    gridlines(img, box, color=(228, 228, 228))
    x0, y0, x1, y1 = box
    t = np.linspace(0, 1, 500)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    xs = cx + (t - 0.5) * (x1 - x0) * 0.8 - np.sin(t * 2 * np.pi) * 260
    ys = cy - np.cos(t * 2 * np.pi) * 250 + (t - 0.5) * 120
    s = Series(np.column_stack([xs, ys]), (220, 40, 120), 4)
    draw_series(img, s)
    ch = Chart("17_loop_curve_non_monotonic", finish(img), [s])
    ch.notes.append("x-backtracking")
    return ch


ALL_CASES.append(case_loop_curve)
