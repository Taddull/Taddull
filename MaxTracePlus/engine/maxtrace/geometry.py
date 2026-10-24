"""Polyline geometry: arc length, simplification, corner recovery, trimming.

Coordinate convention used throughout the engine ("source pixel space"):
pixel (column i, row j) covers [i, i+1) x [j, j+1); its centre is
(i + 0.5, j + 0.5). X grows to the right, Y grows downwards.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

Array = np.ndarray


def as_points(points: Sequence[Sequence[float]] | Array) -> Array:
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("points must have shape (N, 2)")
    return pts


def dedupe(points: Array, eps: float = 1e-6) -> Array:
    """Remove consecutive duplicate points."""
    pts = as_points(points)
    if len(pts) < 2:
        return pts.copy()
    keep = np.ones(len(pts), dtype=bool)
    keep[1:] = np.linalg.norm(np.diff(pts, axis=0), axis=1) > eps
    return pts[keep]


def cumulative_length(points: Array) -> Array:
    """Cumulative arc length at each vertex (first entry is 0)."""
    pts = as_points(points)
    if len(pts) == 0:
        return np.zeros(0)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def total_length(points: Array) -> float:
    cum = cumulative_length(points)
    return float(cum[-1]) if len(cum) else 0.0


def point_at_length(points: Array, s: float, cum: Array | None = None) -> Array:
    pts = as_points(points)
    if cum is None:
        cum = cumulative_length(pts)
    if len(pts) == 1 or s <= 0:
        return pts[0].copy()
    if s >= cum[-1]:
        return pts[-1].copy()
    i = int(np.searchsorted(cum, s, side="right") - 1)
    i = min(max(i, 0), len(pts) - 2)
    seg = cum[i + 1] - cum[i]
    t = 0.0 if seg <= 0 else (s - cum[i]) / seg
    return pts[i] + (pts[i + 1] - pts[i]) * t


def sub_path(points: Array, s0: float, s1: float, cum: Array | None = None) -> Array:
    """Exact portion of the polyline between arc lengths s0 and s1.

    Interior vertices are preserved, the end points are interpolated, so a
    trimmed path lies exactly on the original geometry.
    """
    pts = as_points(points)
    if cum is None:
        cum = cumulative_length(pts)
    L = cum[-1] if len(cum) else 0.0
    s0 = float(np.clip(s0, 0.0, L))
    s1 = float(np.clip(s1, 0.0, L))
    if s1 <= s0:
        p = point_at_length(pts, s0, cum)
        return np.array([p, p])
    inner = pts[(cum > s0) & (cum < s1)]
    start = point_at_length(pts, s0, cum)
    end = point_at_length(pts, s1, cum)
    return np.vstack([start, inner, end]) if len(inner) else np.vstack([start, end])


def trim_fraction(points: Array, start: float, end: float) -> Array:
    """Trim the path to [start, end] expressed as fractions of total length."""
    cum = cumulative_length(points)
    L = cum[-1]
    start = float(np.clip(start, 0.0, 1.0))
    end = float(np.clip(end, 0.0, 1.0))
    if end < start:
        start, end = end, start
    return sub_path(points, start * L, end * L, cum)


def _perp_dist(pts: Array, a: Array, b: Array) -> Array:
    ab = b - a
    n = np.hypot(ab[0], ab[1])
    if n < 1e-12:
        return np.hypot(pts[:, 0] - a[0], pts[:, 1] - a[1])
    return np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / n


def rdp_indices(points: Array, epsilon: float) -> Array:
    """Ramer-Douglas-Peucker; returns indices of the kept vertices (iterative)."""
    pts = as_points(points)
    n = len(pts)
    if n <= 2:
        return np.arange(n)
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        d = _perp_dist(pts[i + 1 : j], pts[i], pts[j])
        k = int(np.argmax(d))
        if d[k] > epsilon:
            m = i + 1 + k
            keep[m] = True
            stack.append((i, m))
            stack.append((m, j))
    return np.nonzero(keep)[0]


def rdp(points: Array, epsilon: float) -> Array:
    pts = as_points(points)
    return pts[rdp_indices(pts, epsilon)]


def _fit_line(pts: Array) -> tuple[Array, Array] | None:
    """Total-least-squares line fit: returns (centroid, unit direction)."""
    if len(pts) < 2:
        return None
    c = pts.mean(axis=0)
    u, s, vt = np.linalg.svd(pts - c, full_matrices=False)
    d = vt[0]
    return c, d / (np.linalg.norm(d) + 1e-12)


def _intersect(c1: Array, d1: Array, c2: Array, d2: Array) -> Array | None:
    m = np.array([[d1[0], -d2[0]], [d1[1], -d2[1]]])
    det = np.linalg.det(m)
    if abs(det) < 1e-9:
        return None
    t = np.linalg.solve(m, c2 - c1)
    return c1 + d1 * t[0]


def turn_angle_deg(a: Array, b: Array, c: Array) -> float:
    """Direction change at b in degrees (0 = straight, 180 = full reversal)."""
    v1 = b - a
    v2 = c - b
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    cosv = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
    return float(np.degrees(np.arccos(cosv)))


def refine_corners(
    dense: Array,
    keep_idx: Array,
    stroke_width: float,
    min_turn_deg: float = 25.0,
    max_shift: float | None = None,
) -> Array:
    """Recover sharp vertices that a thick source line rounds off.

    For each simplified vertex with a significant direction change, straight
    lines are fitted to the dense centre-line samples on both adjacent
    segments (excluding samples close to the corner, which are biased by the
    stroke thickness) and the vertex is moved to their intersection.
    """
    dense = as_points(dense)
    out = dense[keep_idx].copy()
    if len(keep_idx) < 3:
        return out
    t = max(1.0, float(stroke_width))
    guard = 0.9 * t
    # Samples within this many dense indices of a corner are biased: near a
    # sharp apex one column cross-section contains both arms of the stroke.
    idx_guard = int(np.ceil(t)) + 1
    for k in range(1, len(keep_idx) - 1):
        i0, i1, i2 = int(keep_idx[k - 1]), int(keep_idx[k]), int(keep_idx[k + 1])
        turn = turn_angle_deg(dense[i0], dense[i1], dense[i2])
        if turn < min_turn_deg:
            continue
        vtx = dense[i1]
        interior = np.radians(max(1.0, 180.0 - turn))
        reach = t / (2.0 * np.sin(interior / 2.0))  # extent of the arm overlap zone
        lo_i = max(i0 + 1, i1 - idx_guard)
        hi_i = min(i2 - 1, i1 + idx_guard)
        left = dense[i0:lo_i]
        right = dense[hi_i + 1 : i2 + 1]
        if len(left) < 3 or len(right) < 3:
            continue
        lsel = left[np.linalg.norm(left - vtx, axis=1) > guard]
        rsel = right[np.linalg.norm(right - vtx, axis=1) > guard]
        # Drop the sample at the far vertex (it belongs to the next corner zone).
        if len(lsel) > 4:
            lsel = lsel[1:]
        if len(rsel) > 4:
            rsel = rsel[:-1]
        if len(lsel) < 2 or len(rsel) < 2:
            continue
        fl = _fit_line(lsel)
        fr = _fit_line(rsel)
        if fl is None or fr is None:
            continue
        p = _intersect(fl[0], fl[1], fr[0], fr[1])
        if p is None or not np.all(np.isfinite(p)):
            continue
        limit = max_shift if max_shift is not None else max(2.0, 1.5 * t, 1.3 * reach + t)
        # The true apex must stay between the arms horizontally/vertically.
        span_lo = np.minimum(dense[lo_i - 1], dense[hi_i + 1]) - (t + 1.0)
        span_hi = np.maximum(dense[lo_i - 1], dense[hi_i + 1]) + (t + 1.0)
        inside = bool(np.all(p >= np.minimum(span_lo, vtx - limit)) and np.all(p <= np.maximum(span_hi, vtx + limit)))
        if np.linalg.norm(p - vtx) <= limit and inside:
            out[k] = p
    return out


def recover_corners(
    dense: Array,
    keep_idx: Array,
    stroke_width: float,
    accept=None,
    min_turn_deg: float = 25.0,
    return_exact: bool = False,
):
    """Collapse rounded/biased corner zones into their true sharp vertex.

    ``keep_idx`` are simplified (RDP) vertex indices into ``dense``. Segments
    long enough to be reliable are fitted with straight lines; the run of
    short segments between two long ones is a "corner zone". When the zone is
    compact relative to the overlap extent of a stroke of this width at this
    angle, the zone is replaced by the intersection of the two fitted lines.
    ``accept(point) -> bool`` can veto a vertex (e.g. it must land on ink).
    With ``return_exact`` a boolean array marks vertices obtained from a line
    intersection (geometrically exact) as opposed to raw samples.
    """
    dense = as_points(dense)
    verts = [int(i) for i in keep_idx]
    if len(verts) < 3:
        pts = dense[verts].copy()
        return (pts, np.zeros(len(pts), bool)) if return_exact else pts
    t = max(1.0, float(stroke_width))
    idx_guard = int(np.ceil(t)) + 1
    seg_len = [float(np.linalg.norm(dense[b] - dense[a])) for a, b in zip(verts[:-1], verts[1:])]
    seg_n = [b - a for a, b in zip(verts[:-1], verts[1:])]
    long_seg = [L >= max(4.0 * t, 6.0) and n >= 4 for L, n in zip(seg_len, seg_n)]
    cum = cumulative_length(dense)

    def fit(seg: int) -> tuple[Array, Array] | None:
        a, b = verts[seg], verts[seg + 1]
        lo, hi = a + idx_guard, b - idx_guard
        if hi - lo + 1 < 2:
            lo, hi = a + 1, b - 1
        if hi - lo + 1 < 2:
            return None
        return _fit_line(dense[lo : hi + 1])

    out: list[Array] = [dense[verts[0]]]
    exact: list[bool] = [False]
    k = 0
    nseg = len(verts) - 1
    while k < nseg:
        if not long_seg[k]:
            out.append(dense[verts[k + 1]])
            exact.append(False)
            k += 1
            continue
        # Next long segment after k.
        j = k + 1
        while j < nseg and not long_seg[j]:
            j += 1
        if j >= nseg:
            out.extend(dense[verts[m + 1]] for m in range(k, nseg))
            exact.extend(False for _ in range(k, nseg))
            break
        zone = verts[k + 1 : j + 1]  # vertices between the two long segments
        da = dense[verts[k + 1]] - dense[verts[k]]
        db = dense[verts[j + 1]] - dense[verts[j]]
        replaced = False
        cosv = float(np.dot(da, db) / (np.linalg.norm(da) * np.linalg.norm(db) + 1e-12))
        turn = float(np.degrees(np.arccos(np.clip(cosv, -1.0, 1.0))))
        if turn >= min_turn_deg:
            fa, fb = fit(k), fit(j)
            if fa is not None and fb is not None:
                p = _intersect(fa[0], fa[1], fb[0], fb[1])
                if p is not None and np.all(np.isfinite(p)):
                    interior = np.radians(max(1.0, 180.0 - turn))
                    reach = t / (2.0 * np.sin(interior / 2.0))
                    zone_len = float(cum[zone[-1]] - cum[zone[0]])
                    centre = dense[zone].mean(axis=0)
                    if (
                        zone_len <= 2.0 * reach + 3.0 * t
                        and np.linalg.norm(p - centre) <= 1.5 * reach + 2.0 * t + 0.5 * zone_len
                        and (accept is None or accept(p))
                    ):
                        out.append(p)
                        exact.append(True)
                        replaced = True
        if not replaced:
            out.extend(dense[v] for v in zone)
            exact.extend(False for _ in zone)
        k = j
    pts = np.asarray(out)
    ex = np.asarray(exact, bool)
    if len(pts) > 1:
        keep = np.ones(len(pts), bool)
        keep[1:] = np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-6
        pts, ex = pts[keep], ex[keep]
    return (pts, ex) if return_exact else pts


def resample_preserving_vertices(points: Array, max_seg: float) -> Array:
    """Subdivide long segments so no segment exceeds ``max_seg``.

    All original vertices (and therefore every sharp corner) are kept; the
    added points lie exactly on the original segments. This keeps the point
    density roughly proportional to arc length, which makes a write-on that
    is parameterised per point behave like an arc-length reveal.
    """
    pts = dedupe(points)
    if len(pts) < 2 or max_seg <= 0:
        return pts
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        seg = float(np.linalg.norm(b - a))
        n = max(1, int(np.ceil(seg / max_seg)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * (k / n))
    return np.asarray(out)


def distance_to_polyline(query: Array, poly: Array) -> Array:
    """Minimum Euclidean distance from each query point to the polyline."""
    q = as_points(query)
    p = as_points(poly)
    if len(p) == 1:
        return np.linalg.norm(q - p[0], axis=1)
    best = np.full(len(q), np.inf)
    a = p[:-1]
    b = p[1:]
    ab = b - a
    ab2 = np.maximum((ab ** 2).sum(axis=1), 1e-12)
    # Chunk over segments to bound memory.
    chunk = max(1, 2_000_000 // max(1, len(q)))
    for s in range(0, len(a), chunk):
        aa = a[s : s + chunk]
        abb = ab[s : s + chunk]
        t = ((q[:, None, :] - aa[None]) * abb[None]).sum(axis=2) / ab2[None, s : s + chunk]
        t = np.clip(t, 0.0, 1.0)
        proj = aa[None] + t[..., None] * abb[None]
        d = np.linalg.norm(q[:, None, :] - proj, axis=2).min(axis=1)
        best = np.minimum(best, d)
    return best


def path_y_at_x(path: Array, xs: Array) -> Array:
    """For x-monotonic paths: interpolated y at given x (NaN outside span)."""
    p = as_points(path)
    order = np.argsort(p[:, 0], kind="stable")
    px = p[order, 0]
    py = p[order, 1]
    ys = np.interp(xs, px, py, left=np.nan, right=np.nan)
    return ys
