"""Alignment metrics between a detected path and ground truth."""

from __future__ import annotations

import numpy as np

from maxtrace import geometry as geo


def sample_path(points: np.ndarray, step: float = 1.0) -> np.ndarray:
    pts = geo.dedupe(np.asarray(points, float))
    L = geo.total_length(pts)
    if L <= 0:
        return pts[:1]
    cum = geo.cumulative_length(pts)
    s = np.arange(0.0, L + 1e-9, step)
    return np.array([geo.point_at_length(pts, v, cum) for v in s])


def alignment(detected: np.ndarray, gt: np.ndarray) -> dict:
    det_s = sample_path(detected)
    gt_s = sample_path(gt)
    d_det = geo.distance_to_polyline(det_s, gt)  # precision: detected lies on GT
    d_gt = geo.distance_to_polyline(gt_s, detected)  # completeness: GT covered
    return {
        "mean_px": float(d_det.mean()),
        "p95_px": float(np.percentile(d_det, 95)),
        "max_px": float(d_det.max()),
        "gt_mean_px": float(d_gt.mean()),
        "gt_p99_px": float(np.percentile(d_gt, 99)),
        "gt_max_px": float(d_gt.max()),
        "covered_frac": float((d_gt <= 2.0).mean()),
        "start_err_px": float(np.linalg.norm(np.asarray(detected[0]) - gt[0])),
        "end_err_px": float(np.linalg.norm(np.asarray(detected[-1]) - gt[-1])),
    }
