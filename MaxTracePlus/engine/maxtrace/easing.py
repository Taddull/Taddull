"""Reveal-timing curves.

Every motion preset is a cubic Bezier in (normalised time, progress) space,
the same model Fusion's BezierSpline uses for keyframe handles. That lets the
native Fusion output (two keyframes with handles) and the rendered fallback
(per-frame progress computed here) produce identical timing.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# (x1, y1, x2, y2) control points, CSS cubic-bezier convention.
PRESETS: dict[str, tuple[float, float, float, float]] = {
    "linear": (1.0 / 3.0, 1.0 / 3.0, 2.0 / 3.0, 2.0 / 3.0),
    "smooth": (0.42, 0.0, 0.58, 1.0),
    "natural": (0.30, 0.06, 0.22, 1.0),
}


@dataclass(frozen=True)
class Curve:
    x1: float
    y1: float
    x2: float
    y2: float
    linear: bool = False

    @staticmethod
    def from_settings(motion: str, custom: tuple[float, float, float, float] | None = None) -> "Curve":
        motion = (motion or "linear").lower()
        if motion == "custom":
            if not custom or len(custom) != 4:
                raise ValueError("custom motion needs four bezier values")
            x1, y1, x2, y2 = (float(v) for v in custom)
            if not (0.0 <= x1 <= 1.0 and 0.0 <= x2 <= 1.0):
                raise ValueError("custom bezier x values must be within 0..1")
            return Curve(x1, y1, x2, y2)
        if motion not in PRESETS:
            raise ValueError(f"unknown motion '{motion}'")
        return Curve(*PRESETS[motion], linear=(motion == "linear"))

    def _bx(self, t: np.ndarray) -> np.ndarray:
        u = 1 - t
        return 3 * u * u * t * self.x1 + 3 * u * t * t * self.x2 + t ** 3

    def _by(self, t: np.ndarray) -> np.ndarray:
        u = 1 - t
        return 3 * u * u * t * self.y1 + 3 * u * t * t * self.y2 + t ** 3

    def progress(self, x: np.ndarray | float) -> np.ndarray:
        """Progress (0..1) at normalised time x (0..1)."""
        xs = np.clip(np.asarray(x, dtype=np.float64), 0.0, 1.0)
        if self.linear:
            return xs
        # Solve bx(t) = x with bisection (monotonic because 0<=x1,x2<=1).
        lo = np.zeros_like(xs)
        hi = np.ones_like(xs)
        for _ in range(60):
            mid = (lo + hi) * 0.5
            too_big = self._bx(mid) > xs
            hi = np.where(too_big, mid, hi)
            lo = np.where(too_big, lo, mid)
        out = np.clip(self._by((lo + hi) * 0.5), 0.0, 1.0)
        # Exact endpoints: nothing may be visible at the first frame and the
        # whole line must be visible at the last.
        out = np.where(xs <= 0.0, 0.0, np.where(xs >= 1.0, 1.0, out))
        return out


def frame_progress(curve: Curve, start_frame: int, frames: int, query_frames: np.ndarray) -> np.ndarray:
    """Reveal progress for integer comp frames.

    The reveal starts at ``start_frame`` (progress exactly 0) and reaches 1 at
    ``start_frame + frames`` (the last animation frame), so the duration in
    frames is exactly ``frames``.
    """
    if frames < 1:
        raise ValueError("animation must last at least one frame")
    x = (np.asarray(query_frames, dtype=np.float64) - start_frame) / float(frames)
    return curve.progress(x)


def duration_to_frames(seconds: float, fps: float) -> int:
    if fps <= 0:
        raise ValueError("invalid frame rate")
    return max(1, int(round(float(seconds) * float(fps))))
