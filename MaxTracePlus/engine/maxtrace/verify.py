"""Measure a highlight that Fusion actually rendered.

The launcher renders the MaxTrace highlight layer (transparent background)
at a few frames through a temporary Saver. This module compares those
frames with the path that was sent to Fusion:

* geometry: alignment error, and an axis-aligned affine fit
  (rendered = s * expected + o) used to correct the coordinate calibration;
* stroke width (alpha area / path length) used to correct the brush size;
* timing: empty before/at the first frame, partial in the middle with the
  arc-length fraction expected from the timing curve, complete at the end.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from . import geometry as geo
from .fusion_setting import Calibration
from .imageio import load_alpha, ImageLoadError


def layer_coverage(path: str, color: tuple[float, float, float] | None) -> np.ndarray:
    """Coverage (0..1) of a rendered highlight layer.

    Uses the alpha channel when it carries information; otherwise derives
    coverage from the premultiplied colour over black (a Saver writing RGB
    only still yields a usable measurement).
    """
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ImageLoadError(f"Could not decode verification frame {path}")
    scale = 65535.0 if img.dtype == np.uint16 else (255.0 if img.dtype == np.uint8 else 1.0)
    f = img.astype(np.float32) / scale
    if f.ndim == 3 and f.shape[2] == 4:
        a = f[:, :, 3]
        if float(a.min()) < 0.999:
            return np.clip(a, 0.0, 1.0)
        f = f[:, :, :3]
    if f.ndim == 2:
        return np.clip(f, 0, 1)
    rgb = f[:, :, ::-1]
    if color is None or sum(color) < 1e-3:
        return np.clip(rgb.max(axis=2), 0, 1)
    c = np.asarray(color, np.float32)
    return np.clip((rgb @ c) / float(c @ c), 0.0, 1.0)


def centreline_columns(cov: np.ndarray, level: float = 0.3) -> np.ndarray:
    """Per-column weighted centroid of the coverage (x-monotonic layers)."""
    m = cov > level
    cols = np.nonzero(m.any(axis=0))[0]
    if len(cols) == 0:
        return np.zeros((0, 2))
    w = cov[:, cols] * m[:, cols]
    ys = (np.arange(cov.shape[0], dtype=np.float32) + 0.5)[:, None]
    mass = w.sum(axis=0)
    cy = (w * ys).sum(axis=0) / np.maximum(mass, 1e-6)
    return np.column_stack([cols + 0.5, cy])


def _fit_axis(src: np.ndarray, dst: np.ndarray) -> tuple[float, float]:
    """Least squares dst = s * src + o."""
    A = np.column_stack([src, np.ones_like(src)])
    sol, *_ = np.linalg.lstsq(A, dst, rcond=None)
    return float(sol[0]), float(sol[1])


def estimate_affine(rendered: np.ndarray, expected: np.ndarray, width: int, height: int) -> dict[str, float]:
    """Axis-aligned affine (about the image centre) mapping expected -> rendered."""
    c = np.array([width / 2.0, height / 2.0])
    # Ignore the round caps beyond the path ends (they are not path geometry).
    lo, hi = expected[:, 0].min(), expected[:, 0].max()
    inside = (rendered[:, 0] >= lo) & (rendered[:, 0] <= hi)
    if inside.sum() >= 10:
        rendered = rendered[inside]
    r = rendered - c
    e = expected - c
    # Initialise from extents, then refine with nearest-point correspondences.
    def ext(p):
        return p.max(axis=0) - p.min(axis=0)

    er, ee = ext(r), ext(e)
    sx = float(er[0] / ee[0]) if ee[0] > 1 else 1.0
    sy = float(er[1] / ee[1]) if ee[1] > 1 else 1.0
    ox = float(r[:, 0].mean() - sx * e[:, 0].mean())
    oy = float(r[:, 1].mean() - sy * e[:, 1].mean())
    exp_dense = _densify(e, 1.0)
    for _ in range(12):
        mapped = np.column_stack([exp_dense[:, 0] * sx + ox, exp_dense[:, 1] * sy + oy])
        # nearest mapped expected point for each rendered sample
        idx = _nearest_idx(r, mapped)
        src = exp_dense[idx]
        sx, ox = _fit_axis(src[:, 0], r[:, 0])
        sy, oy = _fit_axis(src[:, 1], r[:, 1])
    return {"sx": sx, "ox": ox, "sy": sy, "oy": oy}


def _densify(p: np.ndarray, step: float) -> np.ndarray:
    pts = geo.dedupe(p)
    if len(pts) < 2:
        return pts
    cum = geo.cumulative_length(pts)
    s = np.arange(0.0, cum[-1] + 1e-9, step)
    xs = np.interp(s, cum, pts[:, 0])
    ys = np.interp(s, cum, pts[:, 1])
    return np.column_stack([xs, ys])


def _nearest_idx(q: np.ndarray, ref: np.ndarray) -> np.ndarray:
    out = np.empty(len(q), np.int64)
    chunk = max(1, 4_000_000 // max(1, len(ref)))
    for s in range(0, len(q), chunk):
        d = ((q[s : s + chunk, None, :] - ref[None]) ** 2).sum(axis=2)
        out[s : s + chunk] = d.argmin(axis=1)
    return out


@dataclass
class VerifyInput:
    frames: dict[str, str]  # role -> png path: before, start, mid, end
    expected_px: np.ndarray  # path sent to Fusion (source px)
    width: int
    height: int
    thickness_px: float
    color: tuple[float, float, float]
    mid_progress: float  # expected arc-length fraction at the mid frame
    calibration: Calibration
    mode: str  # native | raster


def verify(inp: VerifyInput) -> dict[str, Any]:
    out: dict[str, Any] = {"ok": False, "checks": {}, "mode": inp.mode}
    covs: dict[str, np.ndarray] = {}
    for role, p in inp.frames.items():
        try:
            cov = layer_coverage(p, inp.color)
        except Exception as e:  # noqa: BLE001 - report, never crash
            out["reason"] = f"Could not read verification frame '{role}': {e}"
            return out
        if cov.shape != (inp.height, inp.width):
            out["reason"] = (
                f"Rendered layer is {cov.shape[1]}x{cov.shape[0]} but the source is {inp.width}x{inp.height}."
            )
            out["checks"]["resolution"] = False
            return out
        covs[role] = cov
    end = covs.get("end")
    if end is None:
        out["reason"] = "No final-frame render to verify."
        return out
    total_end = float(end.sum())
    T = float(inp.thickness_px)
    L = geo.total_length(inp.expected_px)
    expected_area = T * L
    if total_end < 0.02 * max(expected_area, 1.0):
        out["reason"] = "The generated stroke rendered no visible pixels."
        out["checks"]["visible"] = False
        out["nothing_rendered"] = True
        return out
    out["checks"]["visible"] = True

    rendered = centreline_columns(end)
    exp = inp.expected_px
    # Geometry error (both directions).
    r_s = rendered[:: max(1, len(rendered) // 3000)]
    d_r = geo.distance_to_polyline(r_s, exp)
    e_s = _densify(exp, 2.0)
    covered = _coverage_at(end, e_s) >= 0.3
    out["align_mean_px"] = float(np.mean(d_r))
    out["align_p95_px"] = float(np.percentile(d_r, 95))
    out["end_completeness"] = float(covered.mean())
    width_meas = total_end / max(1.0, L + T)
    out["width_px"] = float(width_meas)
    out["width_ratio"] = float(width_meas / max(T, 1e-6))

    aff = estimate_affine(rendered, exp, inp.width, inp.height)
    out["affine"] = aff
    tol_mean = max(0.75, 0.12 * T)
    tol_p95 = max(2.0, 0.35 * T)
    geom_ok = out["align_mean_px"] <= tol_mean and out["align_p95_px"] <= tol_p95 and out["end_completeness"] >= 0.97
    # Rendered sequences carry baked halo/glow, so their alpha area is not a
    # stroke-width measurement; MaxTrace drew them, only timing/placement matter.
    width_ok = True if inp.mode == "raster" else (0.75 <= out["width_ratio"] <= 1.35)
    out["checks"]["geometry"] = bool(geom_ok)
    out["checks"]["width"] = bool(width_ok)

    # Timing.
    timing_ok = True
    for role in ("before", "start"):
        if role in covs:
            frac = float(covs[role].sum()) / total_end
            out[f"{role}_fraction"] = frac
            if frac > 0.01:
                timing_ok = False
    if "mid" in covs:
        frac = float(covs["mid"].sum()) / total_end
        # Caps make the visible fraction slightly larger than the arc fraction.
        cap = (math.pi * (T / 2) ** 2) / max(1.0, expected_area)
        exp_frac = min(1.0, inp.mid_progress + cap)
        out["mid_fraction"] = frac
        out["mid_expected"] = exp_frac
        if abs(frac - exp_frac) > 0.08:
            timing_ok = False
    out["checks"]["timing"] = bool(timing_ok)

    out["ok"] = bool(geom_ok and width_ok and timing_ok)
    if not out["ok"]:
        reasons = []
        if not geom_ok:
            reasons.append(
                "stroke is offset from the traced path (mean {:.1f}px)".format(out["align_mean_px"])
            )
        if not width_ok:
            reasons.append("stroke width is {:.0%} of the requested width".format(out["width_ratio"]))
        if not timing_ok:
            reasons.append("reveal timing does not match the requested animation")
        out["reason"] = "; ".join(reasons).capitalize() + "."
    out["suggested_calibration"] = suggest_calibration(inp, out, aff)
    return out


def _coverage_at(cov: np.ndarray, pts: np.ndarray) -> np.ndarray:
    h, w = cov.shape
    xi = np.clip(np.floor(pts[:, 0]).astype(int), 0, w - 1)
    yi = np.clip(np.floor(pts[:, 1]).astype(int), 0, h - 1)
    # max over a 3x3 neighbourhood to be robust to half-pixel offsets
    best = np.zeros(len(pts), np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            best = np.maximum(best, cov[np.clip(yi + dy, 0, h - 1), np.clip(xi + dx, 0, w - 1)])
    return best


def suggest_calibration(inp: VerifyInput, res: dict[str, Any], aff: dict[str, float]) -> dict[str, Any] | None:
    """Calibration that would cancel the measured transform / width error."""
    if inp.mode != "native":
        return None
    cal = Calibration.from_dict(inp.calibration.to_dict())
    changed = False
    sx, sy, ox, oy = aff["sx"], aff["sy"], aff["ox"], aff["oy"]
    W, H = float(inp.width), float(inp.height)
    if not res["checks"].get("geometry", True) and sx > 0.2 and sy > 0.2:
        # Fusion drew expected point P at s*(P-c)+c+o. Send P' = (P-c-o)/s + c.
        if abs(sy - 1.0) > 0.004:
            # Sending width-normalised Y to a height-normalised consumer draws
            # the shape H/W times too flat (and vice versa). Offsets measured
            # under a scale error are unreliable: they are re-measured in the
            # next verification pass instead.
            hw = H / W
            if cal.y_mode == "width" and abs(sy - hw) / hw < 0.03:
                cal.y_mode = "height"
            elif cal.y_mode == "height" and abs(sy - 1.0 / hw) * hw < 0.03:
                cal.y_mode = "width"
            else:
                cal.y_scale = cal.y_scale / sy
            changed = True
        else:
            if abs(oy) > 0.3:
                cal.y_offset_px = cal.y_offset_px - oy / sy
                changed = True
            if abs(ox) > 0.3 and abs(sx - 1.0) < 0.01:
                cal.x_offset_px = cal.x_offset_px - ox / sx
                changed = True
    if not res["checks"].get("width", True) and res.get("width_ratio", 0) > 0.05:
        cal.size_scale = cal.size_scale / res["width_ratio"]
        changed = True
    if not changed:
        return None
    cal.source = "measured"
    cal.verified = False
    return cal.to_dict()
