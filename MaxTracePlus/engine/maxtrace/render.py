"""Antialiased stroke rasterisation, rendered-fallback sequences and previews.

Strokes are rasterised on a supersampled canvas with round caps and round
joins (OpenCV thick lines), then area-filtered down to the output
resolution. Reveal animation is incremental: frame k draws only the path
piece between the previous and the current reveal length, so each frame is
the exact union of round-capped pieces of the revealed path (no erasing,
no flicker, no point jumping).
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

import cv2
import numpy as np

from . import geometry as geo
from .easing import Curve, frame_progress

SHIFT = 4  # OpenCV sub-pixel bits for polyline vertices


def choose_supersample(width: int, height: int, thickness: float) -> int:
    px = width * height
    if px <= 2_500_000:
        ss = 4
    elif px <= 9_000_000:
        ss = 3
    else:
        ss = 2
    if thickness < 2.5:
        ss = max(ss, 4)
    return ss


@dataclass
class StrokeStyle:
    color: tuple[float, float, float]  # linear 0..1 RGB as displayed (sRGB values)
    thickness: float  # source pixels
    opacity: float = 1.0
    softness: float = 0.0  # 0..1, edge feather of the main stroke
    halo: float = 0.0  # 0..1, strength of the soft secondary stroke
    halo_width: float = 2.6  # halo width as a multiple of thickness
    glow: float = 0.0  # 0..1, very subtle additive glow

    def validate(self) -> None:
        if not (0.25 <= self.thickness <= 400):
            raise ValueError("thickness out of range")
        for v in self.color:
            if not (0.0 <= v <= 1.0):
                raise ValueError("colour out of range")
        self.opacity = float(np.clip(self.opacity, 0.0, 1.0))
        self.softness = float(np.clip(self.softness, 0.0, 1.0))
        self.halo = float(np.clip(self.halo, 0.0, 1.0))
        self.glow = float(np.clip(self.glow, 0.0, 1.0))


class IncrementalStroke:
    """Supersampled coverage canvas restricted to the path bounding box."""

    def __init__(self, path: np.ndarray, width: int, height: int, thickness: float, ss: int, pad: float):
        self.path = geo.dedupe(path)
        self.cum = geo.cumulative_length(self.path)
        self.length = float(self.cum[-1]) if len(self.cum) else 0.0
        self.w = width
        self.h = height
        self.ss = ss
        self.th = thickness
        mn = self.path.min(axis=0) - pad
        mx = self.path.max(axis=0) + pad
        self.bx0 = int(max(0, np.floor(mn[0])))
        self.by0 = int(max(0, np.floor(mn[1])))
        self.bx1 = int(min(width, np.ceil(mx[0])))
        self.by1 = int(min(height, np.ceil(mx[1])))
        if self.bx1 <= self.bx0 or self.by1 <= self.by0:
            raise ValueError("path lies outside the canvas")
        self.canvas = np.zeros(((self.by1 - self.by0) * ss, (self.bx1 - self.bx0) * ss), np.uint8)
        self.drawn = 0.0
        self.thick_ss = max(1, int(round(thickness * ss)))

    def _to_ss(self, pts: np.ndarray) -> np.ndarray:
        local = (pts - np.array([self.bx0, self.by0])) * self.ss - 0.5
        return np.round(local * (1 << SHIFT)).astype(np.int32)

    def draw_until(self, s: float) -> None:
        s = float(np.clip(s, 0.0, self.length))
        if s <= self.drawn + 1e-9:
            return
        piece = geo.sub_path(self.path, self.drawn, s, self.cum)
        cv2.polylines(self.canvas, [self._to_ss(piece)], False, 255, self.thick_ss, cv2.LINE_8, SHIFT)
        self.drawn = s

    def draw_dot(self) -> None:
        """Round cap at the start point (reveal of an infinitesimal length)."""
        p = self._to_ss(self.path[:1])[0]
        cv2.circle(self.canvas, (int(p[0]), int(p[1])), max(1, self.thick_ss // 2) << SHIFT, 255, -1, cv2.LINE_8, SHIFT)

    def coverage(self) -> np.ndarray:
        bw, bh = self.bx1 - self.bx0, self.by1 - self.by0
        return cv2.resize(self.canvas, (bw, bh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def compose_alpha(cov: np.ndarray, style: StrokeStyle) -> np.ndarray:
    """Final straight alpha (0..1) for the highlight layer from raw coverage."""
    a = cov
    if style.softness > 0:
        sigma = 0.15 + style.softness * 0.35 * style.thickness
        a = cv2.GaussianBlur(a, (0, 0), sigma)
        # Re-normalise so the core stays fully opaque for thin feathering.
        a = np.clip(a * (1.0 + 0.6 * style.softness), 0.0, 1.0)
    out = a
    if style.halo > 0:
        sigma = max(0.8, style.thickness * (style.halo_width - 1.0) * 0.5)
        h = cv2.GaussianBlur(cov, (0, 0), sigma)
        h = np.clip(h * (0.55 * style.halo), 0.0, 1.0)
        out = out + h * (1.0 - out)
    if style.glow > 0:
        sigma = max(1.0, style.thickness * 2.0)
        g = cv2.GaussianBlur(cov, (0, 0), sigma)
        g = np.clip(g * (0.35 * style.glow), 0.0, 1.0)
        out = out + g * (1.0 - out)
    return np.clip(out * style.opacity, 0.0, 1.0)


def style_pad(style: StrokeStyle) -> float:
    pad = style.thickness * 0.5 + 3
    if style.halo > 0:
        pad = max(pad, style.thickness * style.halo_width * 1.6 + 3)
    if style.glow > 0:
        pad = max(pad, style.thickness * 7.0 + 3)
    if style.softness > 0:
        pad += style.thickness
    return pad


def render_still(path: np.ndarray, width: int, height: int, style: StrokeStyle, progress: float = 1.0) -> np.ndarray:
    """Full-canvas straight alpha for a given reveal fraction."""
    ss = choose_supersample(width, height, style.thickness)
    inc = IncrementalStroke(path, width, height, style.thickness, ss, style_pad(style))
    alpha = np.zeros((height, width), np.float32)
    if progress <= 0:
        return alpha
    inc.draw_until(progress * inc.length)
    alpha[inc.by0 : inc.by1, inc.bx0 : inc.bx1] = compose_alpha(inc.coverage(), style)
    return alpha


def _rgba_frame(buf: np.ndarray, alpha_bbox: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    buf[y0:y1, x0:x1, 3] = np.round(alpha_bbox * 255.0).astype(np.uint8)
    return buf


def _write_png(path: str, img: np.ndarray) -> None:
    tmp = path + ".tmp.png"
    ok, enc = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 1])
    if not ok:
        raise IOError("PNG encoding failed")
    with open(tmp, "wb") as f:
        f.write(enc.tobytes())
    os.replace(tmp, path)


def _link_or_copy(src: str, dst: str) -> None:
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        import shutil

        shutil.copyfile(src, dst)


@dataclass
class SequenceSpec:
    comp_start: int  # first comp frame covered by the sequence
    comp_end: int  # last comp frame covered
    anim_start: int  # comp frame where progress == 0
    anim_frames: int  # progress reaches 1 at anim_start + anim_frames
    curve: Curve


def render_sequence(
    path: np.ndarray,
    width: int,
    height: int,
    style: StrokeStyle,
    spec: SequenceSpec,
    out_dir: str,
    basename: str = "MaxTrace_",
    progress_cb: Callable[[float, str], None] | None = None,
    cancel_cb: Callable[[], bool] | None = None,
) -> dict:
    """Write a frame-accurate straight-alpha PNG sequence covering the comp range.

    Frame file index 0 corresponds to ``spec.comp_start``. Frames before the
    animation share one fully transparent file and frames after it share the
    final frame (hard links), so the Loader needs no hold/extend logic and
    the disk cost is only the animated frames.
    """
    style.validate()
    if spec.comp_end < spec.comp_start:
        raise ValueError("invalid comp range")
    os.makedirs(out_dir, exist_ok=True)
    total = spec.comp_end - spec.comp_start + 1
    ss = choose_supersample(width, height, style.thickness)
    inc = IncrementalStroke(path, width, height, style.thickness, ss, style_pad(style))
    bbox = (inc.bx0, inc.by0, inc.bx1, inc.by1)
    bgra = np.zeros((height, width, 4), np.uint8)
    r, g, b = (int(round(c * 255)) for c in style.color)
    bgra[:, :, 0], bgra[:, :, 1], bgra[:, :, 2] = b, g, r  # straight colour everywhere

    frames = np.arange(spec.comp_start, spec.comp_end + 1)
    prog = frame_progress(spec.curve, spec.anim_start, spec.anim_frames, frames)
    names = [os.path.join(out_dir, f"{basename}{i:05d}.png") for i in range(total)]
    pool = ThreadPoolExecutor(max_workers=max(2, min(8, (os.cpu_count() or 4))))
    pending = []
    empty_written: str | None = None
    last_unique: str | None = None
    last_p = None
    report_every = max(1, total // 50)
    try:
        for i, (fr, p) in enumerate(zip(frames, prog)):
            if cancel_cb and cancel_cb():
                raise InterruptedError("cancelled")
            p = float(p)
            if p <= 1e-9:
                if empty_written is None:
                    img = bgra.copy()
                    img[:, :, 3] = 0
                    _write_png(names[i], img)
                    empty_written = names[i]
                else:
                    pending.append(("link", empty_written, names[i]))
            elif last_p is not None and abs(p - last_p) < 1e-9 and last_unique is not None:
                pending.append(("link", last_unique, names[i]))
            else:
                inc.draw_until(p * inc.length)
                a = compose_alpha(inc.coverage(), style)
                img = _rgba_frame(bgra.copy(), a, bbox)
                pending.append(("write", pool.submit(_write_png, names[i], img), names[i]))
                last_unique = names[i]
            last_p = p
            if progress_cb and (i % report_every == 0):
                progress_cb((i + 1) / total * 0.9, f"Rendering frame {i + 1}/{total}")
            # Keep memory bounded.
            if len(pending) > 24:
                _flush(pending)
        _flush(pending)
    finally:
        pool.shutdown(wait=True)
    if progress_cb:
        progress_cb(1.0, "Sequence complete")
    return {
        "first_file": names[0],
        "pattern": os.path.join(out_dir, basename + "%05d.png"),
        "frames": total,
        "width": width,
        "height": height,
        "supersample": ss,
        "bbox": list(bbox),
    }


def _flush(pending: list) -> None:
    # Writes must finish before links that may point at them.
    for item in pending:
        if item[0] == "write":
            item[1].result()
    for item in pending:
        if item[0] == "link":
            _link_or_copy(item[1], item[2])
    pending.clear()


# --------------------------------------------------------------------------
# Previews
# --------------------------------------------------------------------------

PALETTE = [(0, 220, 255), (255, 190, 0), (120, 255, 120), (255, 120, 220), (200, 200, 255), (255, 255, 255)]


def render_preview(
    rgb: np.ndarray,
    lines: list,
    selected: int,
    out_path: str,
    trim: tuple[float, float] = (0.0, 1.0),
    region: tuple[int, int, int, int] | None = None,
    max_width: int = 440,
    highlight_rgb: tuple[float, float, float] | None = None,
) -> dict:
    """Small preview: dimmed source, candidates, selected path, start/end."""
    h, w = rgb.shape[:2]
    scale = min(1.0, max_width / float(w))
    pw, ph = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    base = cv2.resize(np.clip(rgb, 0, 1), (pw, ph), interpolation=cv2.INTER_AREA)
    img = (base * 0.55 + 0.45 * base.mean()) * 255.0
    img = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2BGR)
    ss = 4

    def poly(pts, color, thick):
        q = np.round((np.asarray(pts) * scale * ss - 0.5) * (1 << SHIFT)).astype(np.int32)
        big = cv2.resize(img, (pw * ss, ph * ss), interpolation=cv2.INTER_NEAREST)
        cv2.polylines(big, [q], False, color, max(1, int(thick * ss)), cv2.LINE_AA, SHIFT)
        return cv2.resize(big, (pw, ph), interpolation=cv2.INTER_AREA)

    if region is not None:
        x0, y0, x1, y1 = region
        cv2.rectangle(img, (int(x0 * scale), int(y0 * scale)), (int(x1 * scale) - 1, int(y1 * scale) - 1), (90, 90, 90), 1)
    for k, ln in enumerate(lines):
        if ln.id == selected:
            continue
        img = poly(ln.path, PALETTE[(k + 1) % len(PALETTE)], 1.0)
        p = ln.path[len(ln.path) // 2] * scale
        cv2.putText(img, str(ln.id + 1), (int(p[0]) + 3, int(p[1]) - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (230, 230, 230), 1, cv2.LINE_AA)
    sel = next((ln for ln in lines if ln.id == selected), None)
    if sel is not None:
        col = highlight_rgb or (1.0, 0.13, 0.13)
        bgr = tuple(int(c * 255) for c in col[::-1])
        trimmed = geo.trim_fraction(sel.path, trim[0], trim[1])
        img = poly(sel.path, (70, 70, 70), 2.2)
        img = poly(trimmed, bgr, 2.2)
        for x0, x1 in sel.ambiguous_ranges:
            cv2.line(img, (int(x0 * scale), ph - 3), (max(int(x0 * scale) + 1, int(x1 * scale)), ph - 3), (0, 200, 255), 3)
        s = trimmed[0] * scale
        e = trimmed[-1] * scale
        cv2.circle(img, (int(round(s[0])), int(round(s[1]))), 4, (80, 220, 80), -1, cv2.LINE_AA)
        cv2.circle(img, (int(round(e[0])), int(round(e[1]))), 4, (255, 255, 255), 1, cv2.LINE_AA)
        p = sel.path[len(sel.path) // 2] * scale
        cv2.putText(img, str(sel.id + 1), (int(p[0]) + 3, int(p[1]) - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    _write_png(out_path, img)
    return {"path": out_path, "width": pw, "height": ph}
