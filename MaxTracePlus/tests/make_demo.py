"""Render demo strips (source + highlight at several reveal points) for the docs."""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "engine"))
sys.path.insert(0, HERE)

import synth  # noqa: E402
from maxtrace import detect  # noqa: E402
from maxtrace.easing import Curve, frame_progress  # noqa: E402
from maxtrace.render import StrokeStyle, render_preview, render_still  # noqa: E402
from maxtrace.worker import thickness_in_source  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "docs", "images")


def comp_over(rgb, alpha, color):
    a = alpha[..., None]
    return rgb * (1 - a) + np.asarray(color)[None, None, :] * a


def strip(chart, style, name, fractions=(0.0, 0.35, 0.7, 1.0)):
    rgb = chart.rgb.astype(np.float32) / 255.0
    an = detect.analyze(rgb, detect.DetectParams(mode="color", color_hex=chart.pick_hex) if chart.pick_hex else detect.DetectParams())
    line = an.selected_line()
    W, H = chart.size
    T = thickness_in_source({"thickness": style.thickness}, W, H, 1920, 1080)
    st = StrokeStyle(color=style.color, thickness=T, softness=style.softness, halo=style.halo, opacity=style.opacity)
    curve = Curve.from_settings("natural")
    tiles = []
    for f in fractions:
        p = float(frame_progress(curve, 0, 100, np.array([f * 100]))[0])
        a = render_still(line.path, W, H, st, p)
        img = comp_over(rgb, a, style.color)
        tile = cv2.resize(img, (W // 2, H // 2) if W <= 1920 else (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        tile = (np.clip(tile, 0, 1) * 255).astype(np.uint8)
        cv2.putText(tile, f"t = {int(f * 100)}%", (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (50, 50, 50), 2, cv2.LINE_AA)
        tiles.append(tile)
    grid = np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])
    cv2.imwrite(os.path.join(OUT, name + ".png"), cv2.cvtColor(grid, cv2.COLOR_RGB2BGR))
    # Full-resolution crop around a sharp region for pixel inspection.
    a = render_still(line.path, W, H, st, 1.0)
    full = comp_over(rgb, a, style.color)
    cx, cy = int(line.path[len(line.path) // 3][0]), int(line.path[len(line.path) // 3][1])
    x0, y0 = max(0, cx - 200), max(0, cy - 120)
    crop = full[y0 : y0 + 240, x0 : x0 + 400]
    crop = cv2.resize(crop, (crop.shape[1] * 2, crop.shape[0] * 2), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(os.path.join(OUT, name + "_zoom.png"), cv2.cvtColor((np.clip(crop, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    render_preview(rgb, an.lines, an.selected, os.path.join(OUT, name + "_preview.png"), highlight_rgb=style.color)
    return line


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    s = StrokeStyle(color=(1.0, 0.125, 0.125), thickness=7, softness=0.12)
    strip(synth.case_1080p(), StrokeStyle(color=(1.0, 0.82, 0.12), thickness=7, softness=0.12), "demo_financial_yellow")
    strip(synth.case_many_peaks(), StrokeStyle(color=(0.13, 0.83, 0.93), thickness=7, softness=0.12), "demo_peaks_cyan")
    strip(synth.case_blue_grid(), s, "demo_blue_grid_red")
    strip(synth.case_multi_lines(), StrokeStyle(color=(1.0, 0.82, 0.12), thickness=8, softness=0.3, halo=0.35), "demo_multiline_soft")
    print("written to", OUT)
