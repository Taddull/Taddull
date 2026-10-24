"""Graph-line detection.

Pipeline
--------
1. Background estimation (dominant colour, works for light and dark charts).
2. Plot-region estimation from long axis/frame lines (used to discard titles,
   tick labels and legends that sit completely outside the plot).
3. Line-colour candidates: hue peaks for chromatic lines, lightness peaks for
   achromatic (black/white/grey) lines, or a user-picked colour.
4. Soft colour membership: every pixel is projected onto the
   background -> line-colour axis in CIE Lab. Antialiased and JPEG-blurred
   edge pixels lie on that axis and keep a proportional weight; gridlines,
   text in other colours and other series lie off-axis and are rejected.
5. Removal of long perfectly straight horizontal/vertical structures
   (axes, gridlines and frames drawn in the same colour as the line).
6. Centre-line extraction by dynamic programming over per-column runs of the
   membership mask. Every non-vertical thick line has a vertical
   cross-section centred on its centre line, so a weighted run centroid is a
   sub-pixel centre-line sample. The DP picks the most continuous
   left-to-right track, bridges short gaps (labels, annotations) only when
   the vertical jump is plausible, and ignores disconnected clutter.
7. Fallback for graphs that are not x-monotonic: skeleton (thinning) graph
   and longest-path extraction.
8. Ramer-Douglas-Peucker simplification + corner recovery (line fits on each
   arm, intersected) so sharp peaks and valleys are preserved exactly.
9. Confidence scoring with ambiguous-region reporting.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from . import geometry as geo
from .imageio import hex_to_rgb, lab_to_rgb, rgb_to_hex, rgb_to_lab


class DetectionError(RuntimeError):
    """Raised with a user-presentable reason when no line can be traced."""

    def __init__(self, message: str, code: str = "no_line"):
        super().__init__(message)
        self.code = code


@dataclass
class DetectParams:
    mode: str = "auto"  # "auto" | "color"
    color_hex: str | None = None  # used when mode == "color"
    candidate: int | None = None  # candidate id from a previous analysis
    candidate_hex: str | None = None  # colour of that candidate (stable match)
    region: tuple[float, float, float, float] | None = None  # normalised x0,y0,x1,y1
    sensitivity: float = 0.5  # 0..1, colour tolerance
    gap: float = 0.5  # 0..1, maximum bridged gap (0 = none, 1 = ~6.5% width)
    simplify_px: float = 0.6  # RDP tolerance in source pixels
    join_split_colors: bool = True
    max_candidates: int = 6

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> "DetectParams":
        d = dict(d or {})
        p = DetectParams()
        for k in list(d.keys()):
            if hasattr(p, k) and d[k] is not None:
                setattr(p, k, d[k])
        if p.region is not None:
            r = [float(v) for v in p.region]
            if len(r) != 4:
                raise ValueError("region must be [x0, y0, x1, y1]")
            x0, y0, x1, y1 = r
            x0, x1 = sorted((min(max(x0, 0.0), 1.0), min(max(x1, 0.0), 1.0)))
            y0, y1 = sorted((min(max(y0, 0.0), 1.0), min(max(y1, 0.0), 1.0)))
            p.region = None if (x1 - x0 < 0.02 or y1 - y0 < 0.02) else (x0, y0, x1, y1)
        p.sensitivity = float(min(max(float(p.sensitivity), 0.0), 1.0))
        p.gap = float(min(max(float(p.gap), 0.0), 1.0))
        p.simplify_px = float(min(max(float(p.simplify_px), 0.1), 10.0))
        p.max_candidates = int(min(max(int(p.max_candidates), 1), 12))
        if p.mode not in ("auto", "color"):
            raise ValueError("mode must be 'auto' or 'color'")
        if p.mode == "color" and not p.color_hex:
            raise ValueError("Pick Color mode needs a line colour")
        if p.candidate is not None:
            p.candidate = int(p.candidate)
        return p

    def cache_key(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "color_hex": (self.color_hex or "").upper() if self.mode == "color" else None,
            "region": [round(v, 4) for v in self.region] if self.region else None,
            "sensitivity": round(self.sensitivity, 3),
            "gap": round(self.gap, 3),
            "simplify_px": round(self.simplify_px, 3),
            "join": bool(self.join_split_colors),
        }


@dataclass
class TracedLine:
    id: int
    kind: str  # chromatic | achromatic | picked | joined
    color_rgb: tuple[float, float, float]
    dense: np.ndarray  # (N,2) centre-line samples, source px
    path: np.ndarray  # (M,2) simplified, corner-refined path
    thickness: float
    coverage: float
    span: float
    max_gap: float
    ambiguity: float
    residual: float
    confidence: float
    score: float
    method: str  # "columns" | "skeleton"
    ambiguous_ranges: list[tuple[float, float]] = field(default_factory=list)
    parts: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def summary(self, width: int, height: int) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "color": rgb_to_hex(self.color_rgb),
            "points": int(len(self.path)),
            "thickness_px": round(float(self.thickness), 2),
            "coverage": round(float(self.coverage), 3),
            "span": round(float(self.span), 3),
            "max_gap_px": round(float(self.max_gap), 1),
            "ambiguity": round(float(self.ambiguity), 3),
            "residual_px": round(float(self.residual), 3),
            "confidence": round(float(self.confidence), 3),
            "score": round(float(self.score), 4),
            "method": self.method,
            "length_px": round(geo.total_length(self.path), 1),
            "start": [round(float(v), 2) for v in self.path[0]],
            "end": [round(float(v), 2) for v in self.path[-1]],
            "ambiguous_ranges": [[round(a / width, 4), round(b / width, 4)] for a, b in self.ambiguous_ranges],
            "parts": self.parts,
            "notes": self.notes,
        }


# --------------------------------------------------------------------------
# Colour analysis
# --------------------------------------------------------------------------


def _subsample(lab: np.ndarray, target: int = 400_000) -> np.ndarray:
    h, w = lab.shape[:2]
    step = max(1, int(math.sqrt(h * w / target)))
    return lab[::step, ::step].reshape(-1, 3)


def estimate_background(lab: np.ndarray) -> np.ndarray:
    px = _subsample(lab)
    q = np.floor(px / np.array([4.0, 4.0, 4.0])).astype(np.int32)
    q -= q.min(axis=0)
    dims = q.max(axis=0) + 1
    keys = (q[:, 0] * dims[1] + q[:, 1]) * dims[2] + q[:, 2]
    counts = np.bincount(keys)
    top = int(np.argmax(counts))
    sel = keys == top
    return px[sel].mean(axis=0)


def delta_e(lab: np.ndarray, ref: np.ndarray) -> np.ndarray:
    ref = np.asarray(ref, np.float32)
    if lab.ndim == 3:
        d = cv2.subtract(np.ascontiguousarray(lab, np.float32), np.full(lab.shape, ref, np.float32))
        # cv2.transform sums the three squared channels in one fast pass.
        return np.sqrt(cv2.transform(d * d, np.ones((1, 3), np.float32)))
    d = lab - ref
    return np.sqrt(np.einsum("ij,ij->i", d, d))


def _circular_smooth(h: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    k = len(kernel) // 2
    padded = np.concatenate([h[-k:], h, h[:k]])
    return np.convolve(padded, kernel, mode="valid")


def find_color_candidates(lab: np.ndarray, bg: np.ndarray, region_mask: np.ndarray | None, max_n: int) -> list[dict[str, Any]]:
    px = lab if region_mask is None else lab[region_mask]
    px = px.reshape(-1, 3)
    if len(px) > 600_000:
        px = px[:: int(math.ceil(len(px) / 600_000))]
    de = delta_e(px, bg)
    ink = px[de > 18.0]
    cands: list[dict[str, Any]] = []
    if len(ink) < 20:
        return cands
    chroma = np.hypot(ink[:, 1], ink[:, 2])
    bg_chroma = float(np.hypot(bg[1], bg[2]))

    # Chromatic candidates: hue peaks.
    chrom = ink[chroma > max(16.0, bg_chroma + 10.0)]
    if len(chrom) >= 15:
        c_ch = np.hypot(chrom[:, 1], chrom[:, 2])
        hue = (np.degrees(np.arctan2(chrom[:, 2], chrom[:, 1])) + 360.0) % 360.0
        bins = 72
        hist = np.bincount((hue / 5.0).astype(int) % bins, weights=c_ch, minlength=bins)
        sm = _circular_smooth(hist, np.array([1, 2, 3, 2, 1], float))
        total = sm.sum()
        order = np.argsort(-sm)
        peaks: list[int] = []
        for b in order:
            if sm[b] < 0.03 * total:
                break
            left, right = sm[(b - 1) % bins], sm[(b + 1) % bins]
            if sm[b] < left or sm[b] < right:
                continue
            if any(min(abs(b - p), bins - abs(b - p)) < 3 for p in peaks):
                continue
            peaks.append(int(b))
        for b in peaks:
            centre = b * 5.0 + 2.5
            dh = np.abs(((hue - centre) + 180.0) % 360.0 - 180.0)
            sel = chrom[dh <= 12.0]
            if len(sel) < 10:
                continue
            d_sel = delta_e(sel, bg)
            core = sel[d_sel >= np.percentile(d_sel, 60)]
            cands.append({"lab": np.median(core, axis=0), "kind": "chromatic", "weight": float(len(sel))})

    # Achromatic candidates: lightness peaks among low-chroma ink.
    achro = ink[chroma <= max(12.0, bg_chroma + 6.0)]
    if len(achro) >= 15:
        L = achro[:, 0]
        hist = np.bincount(np.clip((L / 2.0).astype(int), 0, 50), minlength=51).astype(float)
        sm = np.convolve(hist, np.array([1, 2, 3, 2, 1], float), mode="same")
        total = sm.sum()
        order = np.argsort(-sm)
        peaks = []
        for b in order:
            if sm[b] < 0.05 * total:
                break
            if (b > 0 and sm[b] < sm[b - 1]) or (b < 50 and sm[b] < sm[b + 1]):
                continue
            if any(abs(b - p) < 6 for p in peaks):
                continue
            peaks.append(int(b))
        for b in peaks:
            sel = achro[np.abs(L - (b * 2.0 + 1.0)) <= 6.0]
            if len(sel) < 10:
                continue
            cands.append({"lab": np.median(sel, axis=0), "kind": "achromatic", "weight": float(len(sel))})

    # Merge near-duplicates.
    merged: list[dict[str, Any]] = []
    for c in sorted(cands, key=lambda c: -c["weight"]):
        if any(np.linalg.norm(c["lab"] - m["lab"]) < 10.0 for m in merged):
            continue
        merged.append(c)
    return merged[: max(max_n * 2, 6)]


def membership(
    lab: np.ndarray, bg: np.ndarray, color: np.ndarray, sensitivity: float, with_coverage: bool = False
):
    """Soft per-pixel membership (0..1) to the line colour.

    Pixels are projected onto the segment bg -> colour: ``t`` is the mixing
    fraction (0 at background, 1 at the pure line colour) and ``perp`` the
    off-axis distance. Antialiased edges have intermediate ``t`` and tiny
    ``perp``; other colours have large ``perp``.
    """
    v = (color - bg).astype(np.float32)
    vv = float(np.dot(v, v))
    if vv < 25.0:
        z = np.zeros(lab.shape[:-1], np.float32)
        return (z, z) if with_coverage else z
    d = lab - bg.astype(np.float32)
    t = (d @ v) / vv
    dd = np.einsum("...k,...k->...", d, d)
    perp = np.sqrt(np.maximum(dd - t * t * vv, 0.0))
    tol = 6.0 + 20.0 * sensitivity + 0.05 * math.sqrt(vv)
    w_t = np.clip((t - 0.10) / 0.45, 0.0, 1.0)
    w_t *= np.clip((2.4 - t) / 0.8, 0.0, 1.0)
    w_p = np.clip(1.6 - perp / tol, 0.0, 1.0)
    w = (w_t * w_p).astype(np.float32)
    if not with_coverage:
        return w
    # Coverage estimate: the mixing fraction itself (an antialiased pixel
    # half covered by the line has t ~ 0.5). Used for centroids and widths.
    cov = (np.clip(t, 0.0, 1.0) * w_p).astype(np.float32)
    return w, cov


# --------------------------------------------------------------------------
# Structure analysis
# --------------------------------------------------------------------------


def long_straight_structures(mask: np.ndarray, min_h: int, min_v: int, bridge: int = 6) -> tuple[np.ndarray, np.ndarray]:
    """Long perfectly horizontal / vertical structures (axes, gridlines, frames).

    Small interruptions (e.g. gridlines painted across an axis, tick gaps)
    are bridged along the structure direction before the long opening.
    """
    m8 = mask.astype(np.uint8)
    ch = cv2.getStructuringElement(cv2.MORPH_RECT, (bridge, 1))
    cv_ = cv2.getStructuringElement(cv2.MORPH_RECT, (1, bridge))
    kh = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, min_h), 1))
    kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(3, min_v)))
    horiz = (cv2.morphologyEx(cv2.morphologyEx(m8, cv2.MORPH_CLOSE, ch), cv2.MORPH_OPEN, kh) > 0) & mask
    vert = (cv2.morphologyEx(cv2.morphologyEx(m8, cv2.MORPH_CLOSE, cv_), cv2.MORPH_OPEN, kv) > 0) & mask
    return horiz, vert


def estimate_plot_region(de_bg: np.ndarray) -> tuple[int, int, int, int] | None:
    """Find axis/frame lines; returns (x0, y0, x1, y1) inclusive-exclusive or None."""
    H, W = de_bg.shape
    f = max(1, int(math.ceil(max(H, W) / 1600.0)))
    small = cv2.resize(de_bg, (W // f, H // f), interpolation=cv2.INTER_AREA) if f > 1 else de_bg
    h, w = small.shape
    ink = small > (35.0 if f == 1 else 22.0)
    horiz, vert = long_straight_structures(ink, int(0.45 * w), int(0.45 * h))
    x0, y0, x1, y1 = 0, 0, w, h
    found = False
    cols = np.nonzero(vert.sum(axis=0) >= 0.45 * h)[0]
    rows = np.nonzero(horiz.sum(axis=1) >= 0.45 * w)[0]
    left = cols[cols < 0.35 * w]
    right = cols[cols > 0.65 * w]
    bottom = rows[rows > 0.5 * h]
    top = rows[rows < 0.3 * h]
    if len(left):
        x0 = int(left.max()) - 1
        found = True
    if len(right):
        x1 = int(right.min()) + 2
        found = True
    if len(bottom):
        y1 = int(bottom.min()) + 2 if len(bottom) and (bottom.max() - bottom.min()) < 6 else int(bottom.max()) + 2
        found = True
    if len(top) and len(left) and len(right):
        y0 = int(top.min()) - 1
    if not found:
        return None
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if (x1 - x0) < 0.3 * w or (y1 - y0) < 0.3 * h:
        return None
    return max(0, x0 * f - f), max(0, y0 * f - f), min(W, x1 * f + f), min(H, y1 * f + f)


@dataclass
class Runs:
    col: np.ndarray
    y0: np.ndarray  # inclusive
    y1: np.ndarray  # exclusive
    cy: np.ndarray  # weighted centroid (continuous coordinates)
    mass: np.ndarray  # sum of soft weights over the run (+fringe)
    label: np.ndarray
    col_start: np.ndarray  # index of first run per column (len W+1)


def column_runs(mask: np.ndarray, weights: np.ndarray, labels: np.ndarray) -> Runs:
    """Vertical runs of the mask per column, with weighted centroids.

    Sums cover the run plus a 1-pixel fringe on each side (antialiased edge
    pixels below the mask threshold), computed with ``np.add.reduceat`` on the
    column-major weight array so cost is proportional to run pixels.
    """
    h, w = mask.shape
    mt = np.ascontiguousarray(mask.T)
    pad = np.zeros((w, h + 2), np.int8)
    pad[:, 1:-1] = mt
    d = np.diff(pad, axis=1)  # (w, h+1)
    sc, sr = np.nonzero(d == 1)  # sorted by column then row
    ec, er = np.nonzero(d == -1)
    if len(sc) != len(ec):
        raise RuntimeError("run extraction mismatch")
    n = len(sc)
    col_start = np.searchsorted(sc, np.arange(w + 1))
    if n == 0:
        z = np.zeros(0)
        return Runs(sc.astype(np.int32), sr.astype(np.int32), er.astype(np.int32), z, z, np.zeros(0, np.int32), col_start)
    a = np.maximum(sr - 1, 0)
    b = np.minimum(er + 1, h)
    # Avoid overlapping fringes between neighbouring runs in the same column.
    same = np.zeros(n, bool)
    same[1:] = sc[1:] == sc[:-1]
    prev_end = np.concatenate([[0], er[:-1]])
    a = np.where(same, np.maximum(a, prev_end), a)
    nxt_start = np.concatenate([sr[1:], [h]])
    same_next = np.concatenate([sc[1:] == sc[:-1], [False]])
    b = np.where(same_next, np.minimum(b, nxt_start), b)
    wt = np.zeros(w * h + 1, np.float32)
    wt[:-1] = weights.T.ravel()
    wy = np.zeros(w * h + 1, np.float32)
    wy[:-1] = (weights * (np.arange(h, dtype=np.float32)[:, None] + 0.5)).T.ravel()
    base = sc.astype(np.int64) * h
    idx = np.empty(2 * n, np.int64)
    idx[0::2] = base + a
    idx[1::2] = base + b
    mass = np.add.reduceat(wt, idx)[0::2].astype(np.float64)
    sy = np.add.reduceat(wy, idx)[0::2].astype(np.float64)
    cy = np.where(mass > 1e-6, sy / np.maximum(mass, 1e-6), (sr + er) * 0.5)
    lab = labels[sr, sc]
    return Runs(sc.astype(np.int32), sr.astype(np.int32), er.astype(np.int32), cy, mass, lab, col_start)


@dataclass
class TrackResult:
    run_idx: np.ndarray
    gaps: list[tuple[int, int]]  # (x_from, x_to) bridged gaps in columns


def dp_track(runs: Runs, thickness: float, max_gap: int, width: int) -> TrackResult | None:
    """Most continuous left-to-right track through column runs."""
    n = len(runs.col)
    if n == 0:
        return None
    score = np.zeros(n, np.float64)
    back = np.full(n, -1, np.int64)
    col = runs.col
    y0 = runs.y0
    y1 = runs.y1
    cy = runs.cy
    cs = runs.col_start
    jump_base = max(4.0 * thickness, 6.0)
    for x in range(width):
        a, b = cs[x], cs[x + 1]
        if a == b:
            continue
        pa, pb = (cs[x - 1], cs[x]) if x > 0 else (0, 0)
        for s in range(a, b):
            best = 1.0
            bi = -1
            connected = False
            if pb > pa:
                # Connected predecessors (8-connected overlap).
                r = np.arange(pa, pb)
                ok = (y0[r] <= y1[s]) & (y0[s] <= y1[r])
                if ok.any():
                    rr = r[ok]
                    cand = score[rr] + 1.0 - 0.002 * np.abs(cy[rr] - cy[s])
                    k = int(np.argmax(cand))
                    best, bi, connected = float(cand[k]), int(rr[k]), True
            if not connected and max_gap > 0 and x > 1:
                ga = cs[max(0, x - 1 - max_gap)]
                gb = cs[x - 1]
                if gb > ga:
                    r = np.arange(ga, gb)
                    g = (x - col[r] - 1).astype(np.float64)
                    dy = np.maximum(0.0, np.maximum(y0[s] - y1[r], y0[r] - y1[s])).astype(np.float64)
                    allow = jump_base + 2.5 * g
                    ok = dy <= allow
                    if ok.any():
                        rr = r[ok]
                        cand = score[rr] + 1.0 - 0.35 * g[ok] - 0.08 * dy[ok]
                        k = int(np.argmax(cand))
                        if cand[k] > best:
                            best, bi = float(cand[k]), int(rr[k])
            score[s] = best
            back[s] = bi
    end = int(np.argmax(score))
    idx = []
    gaps = []
    cur = end
    while cur >= 0:
        idx.append(cur)
        prv = int(back[cur])
        if prv >= 0 and col[cur] - col[prv] > 1:
            gaps.append((int(col[prv]), int(col[cur])))
        cur = prv
    idx.reverse()
    gaps.reverse()
    return TrackResult(np.asarray(idx, np.int64), gaps)


# --------------------------------------------------------------------------
# Skeleton fallback (non x-monotonic curves)
# --------------------------------------------------------------------------


def zhang_suen_thin(mask: np.ndarray, max_iter: int = 200) -> np.ndarray:
    img = mask.astype(np.uint8).copy()
    img = np.pad(img, 1)
    for _ in range(max_iter):
        changed = False
        for step in (0, 1):
            p2 = img[:-2, 1:-1]
            p3 = img[:-2, 2:]
            p4 = img[1:-1, 2:]
            p5 = img[2:, 2:]
            p6 = img[2:, 1:-1]
            p7 = img[2:, :-2]
            p8 = img[1:-1, :-2]
            p9 = img[:-2, :-2]
            c = img[1:-1, 1:-1]
            nb = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            trans = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                cond = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                cond = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            rem = (c == 1) & (nb >= 2) & (nb <= 6) & (trans == 1) & cond
            if rem.any():
                c[rem] = 0
                changed = True
        if not changed:
            break
    return img[1:-1, 1:-1].astype(bool)


_NB8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _bfs_far(start: tuple[int, int], pix: set) -> tuple[tuple[int, int], dict]:
    prev = {start: None}
    q = deque([start])
    last = start
    while q:
        p = q.popleft()
        last = p
        for dy, dx in _NB8:
            n = (p[0] + dy, p[1] + dx)
            if n in pix and n not in prev:
                prev[n] = p
                q.append(n)
    return last, prev


def skeleton_longest_path(mask: np.ndarray) -> np.ndarray | None:
    sk = zhang_suen_thin(mask)
    ys, xs = np.nonzero(sk)
    if len(ys) < 3:
        return None
    pix = set(zip(ys.tolist(), xs.tolist()))
    # Largest connected skeleton piece.
    seen: set = set()
    best: list = []
    for p in list(pix):
        if p in seen:
            continue
        comp = []
        q = deque([p])
        seen.add(p)
        while q:
            c = q.popleft()
            comp.append(c)
            for dy, dx in _NB8:
                n = (c[0] + dy, c[1] + dx)
                if n in pix and n not in seen:
                    seen.add(n)
                    q.append(n)
        if len(comp) > len(best):
            best = comp
    piece = set(best)
    a, _ = _bfs_far(min(piece, key=lambda t: (t[1], t[0])), piece)
    b, prev = _bfs_far(a, piece)
    path = []
    cur = b
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    pts = np.array([[c[1] + 0.5, c[0] + 0.5] for c in path], np.float64)
    if pts[0, 0] > pts[-1, 0]:
        pts = pts[::-1]
    # Light smoothing to remove the 8-connected staircase.
    if len(pts) > 5:
        k = np.array([1, 2, 3, 2, 1], float)
        k /= k.sum()
        sm = np.vstack([np.convolve(np.pad(pts[:, i], 2, mode="edge"), k, mode="valid") for i in range(2)]).T
        sm[0], sm[-1] = pts[0], pts[-1]
        pts = sm
    return pts


# --------------------------------------------------------------------------
# Main analysis
# --------------------------------------------------------------------------


@dataclass
class Analysis:
    width: int
    height: int
    background_rgb: tuple[float, float, float]
    region_px: tuple[int, int, int, int]
    region_source: str  # "auto" | "manual" | "full"
    lines: list[TracedLine]
    selected: int
    warnings: list[str]

    def selected_line(self) -> TracedLine:
        for ln in self.lines:
            if ln.id == self.selected:
                return ln
        raise DetectionError("Selected line is no longer available; re-run detection.", "stale_candidate")

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "background": rgb_to_hex(self.background_rgb),
            "region_px": list(self.region_px),
            "region": [
                round(self.region_px[0] / self.width, 4),
                round(self.region_px[1] / self.height, 4),
                round(self.region_px[2] / self.width, 4),
                round(self.region_px[3] / self.height, 4),
            ],
            "region_source": self.region_source,
            "selected": self.selected,
            "candidates": [ln.summary(self.width, self.height) for ln in self.lines],
            "warnings": self.warnings,
        }


def _thickness_from_track(runs: Runs, idx: np.ndarray) -> float:
    """Perpendicular stroke width.

    The soft mass of a 1-px column strip through a straight thick line equals
    width * sqrt(1 + slope^2), so mass * cos(atan(slope)) is the width for
    every straight part; corners are outliers and the median ignores them.
    """
    if len(idx) < 3:
        return float(np.median(runs.mass[idx])) if len(idx) else 1.0
    cy = runs.cy[idx]
    xs = runs.col[idx].astype(np.float64)
    slope = np.gradient(cy, xs)
    vals = runs.mass[idx] * np.cos(np.arctan(slope))
    return float(max(0.8, np.median(vals)))


def _sparse_membership(
    lab_ink: np.ndarray, ink_idx: tuple[np.ndarray, np.ndarray], shape: tuple[int, int], bg: np.ndarray, color_lab: np.ndarray, sensitivity: float
) -> tuple[np.ndarray, np.ndarray]:
    """Membership/coverage evaluated only on "ink" pixels (differ from bg)."""
    w_s, c_s = membership(lab_ink, bg, color_lab, sensitivity, with_coverage=True)
    W = np.zeros(shape, np.float32)
    C = np.zeros(shape, np.float32)
    W[ink_idx] = w_s
    C[ink_idx] = c_s
    return W, C


def _trace_color(
    W: np.ndarray,
    COV: np.ndarray,
    params: DetectParams,
    region: tuple[int, int, int, int],
    auto_region: tuple[int, int, int, int] | None,
    global_straight: np.ndarray | None = None,
) -> dict[str, Any] | None:
    h, w = W.shape
    x0, y0, x1, y1 = region
    if (x0, y0, x1, y1) != (0, 0, w, h):
        outside = np.ones((h, w), bool)
        outside[y0:y1, x0:x1] = False
        W[outside] = 0.0
        COV[outside] = 0.0
    mask = W > 0.4
    if mask.sum() < 8:
        return None
    rw, rh = x1 - x0, y1 - y0
    horiz, vert = long_straight_structures(mask, int(0.55 * rw), int(0.55 * rh))
    straight = horiz | vert
    if global_straight is not None:
        straight |= global_straight
    # Coverage used for end/tip searches: everything of this colour except
    # the cores of axes/gridlines (so ends never run along an axis).
    cov_ends = COV.copy()
    if straight.any():
        cov_ends[straight] = 0.0
        # Include the structures' antialiased fringe so no residue survives.
        straight = cv2.dilate(straight.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        mask &= ~straight
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    if n <= 1:
        return None
    keep = np.zeros(n, bool)
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 6:
            continue
        if auto_region is not None:
            bx, by, bw, bh = stats[i, :4]
            ax0, ay0, ax1, ay1 = auto_region
            if bx + bw <= ax0 or bx >= ax1 or by + bh <= ay0 or by >= ay1:
                continue  # entirely outside the plot frame (titles, tick labels)
        keep[i] = True
    if not keep.any():
        return None
    mask &= keep[labels]
    fringe = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    if straight.any():
        fringe &= ~straight
    Wf = COV * fringe
    runs = column_runs(mask, Wf, labels)
    if len(runs.col) == 0:
        return None
    big = int(np.argmax(np.where(keep, stats[:, cv2.CC_STAT_AREA], 0)))
    sel_big = runs.label == big
    t0 = float(np.percentile(runs.y1[sel_big] - runs.y0[sel_big], 10)) if sel_big.any() else 2.0
    max_gap = int(round(w * (0.002 + 0.063 * params.gap))) if params.gap > 0 else 0
    track = dp_track(runs, max(1.0, t0), max_gap, w)
    if track is None or len(track.run_idx) < 3:
        return None
    idx = track.run_idx
    dense = np.column_stack([runs.col[idx] + 0.5, runs.cy[idx]])
    thickness = _thickness_from_track(runs, idx)
    dense = _trim_stubs(dense, thickness)
    method = "columns"

    # Explained-mass check: how much of the traced components does the track cover?
    comp_ids = np.unique(runs.label[idx])
    in_comps = np.isin(runs.label, comp_ids)
    total_mass = float(runs.mass[in_comps].sum())
    track_mass = float(runs.mass[idx].sum())
    explained = track_mass / max(total_mass, 1e-6)
    # Curves that double back in x cannot be followed column by column; the
    # untracked mass of the traced components reveals them. Only then is the
    # (slower) skeleton tracer run, and its path is used only when it is
    # clearly longer, i.e. it follows geometry the column track skipped.
    span_frac = float(dense[:, 0].max() - dense[:, 0].min()) / max(1.0, float(rw))
    if explained < 0.995 and span_frac > 0.2:
        comp_mask = mask & np.isin(labels, comp_ids)
        ys_, xs_ = np.nonzero(comp_mask)
        oy, ox = max(0, int(ys_.min()) - 2), max(0, int(xs_.min()) - 2)
        sk = skeleton_longest_path(comp_mask[oy : int(ys_.max()) + 3, ox : int(xs_.max()) + 3])
        if sk is not None:
            sk = sk + np.array([ox, oy], float)
            if geo.total_length(sk) > 1.03 * geo.total_length(dense) + 2.0 * thickness:
                dense = sk
                method = "skeleton"

    # Competing structure per path column (ambiguity).
    span_cols = np.unique(runs.col[idx])
    counts = runs.col_start[span_cols + 1] - runs.col_start[span_cols]
    ambiguous_cols = span_cols[counts > 1]
    ambiguity = float(len(ambiguous_cols)) / max(1, len(span_cols))

    xs_span = float(dense[:, 0].max() - dense[:, 0].min())
    covered = len(span_cols)
    coverage = covered / max(1.0, xs_span) if method == "columns" else 1.0
    coverage = float(min(1.0, coverage))
    max_gap_px = float(max([b - a - 1 for a, b in track.gaps], default=0))

    # Ambiguous ranges: bridged gaps + clusters of competing columns.
    ranges: list[tuple[float, float]] = [(float(a), float(b)) for a, b in track.gaps if b - a - 1 > max(3, 2 * thickness)]
    if len(ambiguous_cols):
        start = prev = int(ambiguous_cols[0])
        for c in ambiguous_cols[1:]:
            c = int(c)
            if c - prev > 3:
                if prev - start >= max(4, thickness * 2):
                    ranges.append((float(start), float(prev)))
                start = c
            prev = c
        if prev - start >= max(4, thickness * 2):
            ranges.append((float(start), float(prev)))
    ranges.sort()

    return {
        "dense": dense,
        "thickness": thickness,
        "coverage": coverage,
        "span": xs_span / max(1.0, float(rw)),
        "max_gap": max_gap_px,
        "ambiguity": ambiguity,
        "method": method,
        "ranges": ranges,
        "mass": track_mass,
        "ink": Wf,
        "cov": cov_ends,
    }


def _trim_stubs(dense: np.ndarray, t: float) -> np.ndarray:
    """Drop a few leading/trailing samples that are not part of the line.

    Residue of axes or labels touching a line end can attach a short stub
    to the track. A prefix of up to ``m`` samples is a stub when every one
    of its samples is far from the line fitted to the samples right after it.
    """
    m = min(int(math.ceil(2 * t)) + 3, 12)
    win = 6
    if len(dense) < m + win + 4:
        return dense
    lo, hi = 0, len(dense)
    for side in (0, 1):
        seq = dense if side == 0 else dense[::-1]
        cut = 0
        for k in range(m - 1, -1, -1):
            fit = geo._fit_line(seq[k + 1 : k + 1 + win])
            if fit is None:
                continue
            c, d = fit
            nrm = np.array([-d[1], d[0]])
            dist = np.abs((seq[: k + 1] - c) @ nrm)
            if np.all(dist > 2.0 * t + 2.0):
                cut = k + 1
                break
        if cut:
            if side == 0:
                lo = cut
            else:
                hi = len(dense) - cut
    return dense[lo:hi]


def _sample(cov: np.ndarray, p: np.ndarray) -> float:
    h, w = cov.shape
    x, y = float(p[0]) - 0.5, float(p[1]) - 0.5
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    if x0 < 0 or y0 < 0 or x0 + 1 >= w or y0 + 1 >= h:
        return 0.0
    fx, fy = x - x0, y - y0
    a = cov[y0, x0] * (1 - fx) + cov[y0, x0 + 1] * fx
    b = cov[y0 + 1, x0] * (1 - fx) + cov[y0 + 1, x0 + 1] * fx
    return float(a * (1 - fy) + b * fy)


def _edge_distance(cov: np.ndarray, p: np.ndarray, u: np.ndarray, max_d: float, level: float = 0.5) -> float | None:
    """Distance from p along unit u to where coverage falls below ``level``."""
    step = 0.25
    last_in = None
    d = 0.0
    while d <= max_d:
        if _sample(cov, p + u * d) >= level:
            last_in = d
        elif last_in is not None:
            break
        d += step
    return last_in


def _corridor_extent(
    cov: np.ndarray, origin: np.ndarray, u: np.ndarray, half_width: float, max_d: float, level: float = 0.5
) -> tuple[float, float] | None:
    """Continuous ink extent from ``origin`` along ``u`` inside a corridor.

    Returns (extent, mean signed across-offset of the last stroke-width of
    ink) or None. Using a corridor instead of a single ray tolerates small
    direction/offset errors of the end segment estimate.
    """
    h, w = cov.shape
    nrm = np.array([-u[1], u[0]])
    end = origin + u * max_d
    pad = half_width + 2
    x0 = int(max(0, math.floor(min(origin[0], end[0]) - pad)))
    x1 = int(min(w, math.ceil(max(origin[0], end[0]) + pad)))
    y0 = int(max(0, math.floor(min(origin[1], end[1]) - pad)))
    y1 = int(min(h, math.ceil(max(origin[1], end[1]) + pad)))
    if x1 <= x0 or y1 <= y0:
        return None
    ys, xs = np.mgrid[y0:y1, x0:x1]
    px = np.column_stack([xs.ravel() + 0.5, ys.ravel() + 0.5])
    c = cov[y0:y1, x0:x1].ravel()
    rel = px - origin
    along = rel @ u
    across = rel @ nrm
    sel = (c >= level) & (np.abs(across) <= half_width) & (along >= -1.0) & (along <= max_d)
    if not sel.any():
        return None
    al = np.sort(along[sel])
    if al[0] > 1.5:
        return None
    gaps = np.nonzero(np.diff(al) > 1.6)[0]
    ext = float(al[gaps[0]] if len(gaps) else al[-1]) + 0.5
    tip = sel & (along >= ext - 1.5 * half_width) & (along <= ext)
    off = float(np.average(across[tip], weights=c[tip])) if tip.any() else 0.0
    return ext, off


def _refine_endpoints(path: np.ndarray, dense: np.ndarray, cov: np.ndarray, t: float) -> np.ndarray:
    """Place each end at the centre of the source line's end cap.

    From the second vertex (inside the line) the ink is followed back along
    the end segment within a corridor one stroke radius wide; the end point
    is set one radius inside the ink extent and re-centred across the line.
    Leading vertices biased by the cap itself are dropped when they are
    collinear with the end segment.
    """
    out = [np.asarray(p, float) for p in path]
    r = 0.5 * t
    hw = r + 1.5
    for at_start in (True, False):
        P = out if at_start else out[::-1]
        if len(P) < 2:
            break
        # Skip cap-biased vertices: short, collinear first segments.
        j = 1
        while j < len(P) - 1 and j <= 3 and np.linalg.norm(P[j] - P[0]) < 3.0 * t:
            a, b = P[0], P[j + 1]
            ab = b - a
            dist = abs(ab[0] * (P[j][1] - a[1]) - ab[1] * (P[j][0] - a[0])) / (np.linalg.norm(ab) + 1e-9)
            if dist > max(1.5, 0.6 * t):
                break
            j += 1
        origin = P[j]
        v = P[0] - origin
        L = float(np.linalg.norm(v))
        if L < 1e-6:
            continue
        u = v / L
        # Generous reach: the walk stops at the first gap anyway, and steep
        # ends next to a removed axis can be missing many pixels of length.
        res = _corridor_extent(cov, origin, u, hw, L + 8.0 * t + 24.0)
        if res is None:
            continue
        ext, off = res
        if ext <= r:
            continue
        nrm = np.array([-u[1], u[0]])
        new = origin + u * (ext - r) + nrm * off
        P = [new] + P[j:]
        out = P if at_start else P[::-1]
    return np.asarray(out)


def _snap_spikes(path: np.ndarray, exact: np.ndarray, cov: np.ndarray, t: float) -> np.ndarray:
    """Extend sharp vertices (peaks, valleys, needle spikes) to the ink tip.

    The vertex moves outward along the corner bisector until it sits one
    stroke radius inside the source tip. For round joins this is exactly
    the centre-line apex; for mitred joins it keeps the highlight's margin
    around the tip identical to its margin along the rest of the line.
    Vertices are only ever moved outward and only within the ink.
    """
    # A biased apex is often split into two or three very close vertices;
    # collapse such clusters first so the corner is evaluated as one.
    pts = [np.asarray(path[0], float)]
    ex = [bool(exact[0])]
    for k in range(1, len(path)):
        p = np.asarray(path[k], float)
        if k < len(path) - 1 and np.linalg.norm(p - pts[-1]) < max(1.0, 0.6 * t) and len(pts) > 1:
            pts[-1] = (pts[-1] + p) * 0.5
            ex[-1] = ex[-1] and bool(exact[k])
            continue
        pts.append(p)
        ex.append(bool(exact[k]))
    out = np.asarray(pts)
    r = 0.5 * t
    for k in range(1, len(out) - 1):
        a, v, b = out[k - 1], out[k], out[k + 1]
        if geo.turn_angle_deg(a, v, b) < 55.0:
            continue
        uin = (v - a) / (np.linalg.norm(v - a) + 1e-12)
        uout = (b - v) / (np.linalg.norm(b - v) + 1e-12)
        bis = uin - uout
        n = np.linalg.norm(bis)
        if n < 1e-6:
            continue
        bis /= n
        e = _edge_distance(cov, v, bis, 12.0 * t + 40.0)
        if e is None:
            continue
        shift = e - r
        if shift > max(1.0, 0.2 * t):
            out[k] = v + bis * shift
    return out


def _fit_vertices_to_ink(path: np.ndarray, cov: np.ndarray, t: float, min_turn: float = 20.0) -> np.ndarray:
    """Model-fit corner vertices to the ink.

    For each corner, a stroke of the measured source width through the
    vertex and its two neighbouring segments is rendered in a small window
    and compared (squared error) with the observed coverage; a pattern search
    moves the vertex (at most one stroke width) to the best match. This
    resolves corners whose arms are too short for line fitting.
    """
    out = path.copy()
    h, w = cov.shape
    ss = 4
    thick = max(1, int(round(t * ss)))
    reach = 3.0 * t + 2.0
    pad = int(math.ceil(t + 3))
    limit = max(1.0, t)

    def local_err(k: int, v: np.ndarray) -> float:
        a, b = out[k - 1], out[k + 1]
        da, db = a - v, b - v
        la, lb = np.linalg.norm(da), np.linalg.norm(db)
        pa = v + da * min(1.0, reach / max(la, 1e-9))
        pb = v + db * min(1.0, reach / max(lb, 1e-9))
        pts = np.array([pa, v, pb])
        x0 = int(max(0, math.floor(pts[:, 0].min()) - pad))
        y0 = int(max(0, math.floor(pts[:, 1].min()) - pad))
        x1 = int(min(w, math.ceil(pts[:, 0].max()) + pad))
        y1 = int(min(h, math.ceil(pts[:, 1].max()) + pad))
        if x1 - x0 < 2 or y1 - y0 < 2:
            return float("inf")
        canvas = np.zeros(((y1 - y0) * ss, (x1 - x0) * ss), np.uint8)
        q = np.round(((pts - np.array([x0, y0])) * ss - 0.5) * 16).astype(np.int32)
        cv2.polylines(canvas, [q], False, 255, thick, cv2.LINE_8, 4)
        model = cv2.resize(canvas, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        obs = cov[y0:y1, x0:x1]
        # Only judge pixels the local model could explain (ignore far ink).
        m = (model > 0.01) | (obs > 0.05)
        return float(((model - obs) ** 2 * m).sum())

    for k in range(1, len(out) - 1):
        if geo.turn_angle_deg(out[k - 1], out[k], out[k + 1]) < min_turn:
            continue
        v0 = out[k].copy()
        best = local_err(k, v0)
        cur = v0.copy()
        step = max(0.5, min(2.0, t / 2.0))
        while step >= 0.24:
            improved = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                cand = cur + np.array([dx, dy]) * step
                if np.linalg.norm(cand - v0) > limit:
                    continue
                e = local_err(k, cand)
                if e < best - 1e-6:
                    best, cur, improved = e, cand, True
            if not improved:
                step *= 0.5
        out[k] = cur
    return out


def _band(path: np.ndarray, shape: tuple[int, int], origin: tuple[int, int], width: float) -> np.ndarray:
    h, w = shape
    q = np.round((path - np.array(origin) - 0.5) * 16).astype(np.int32)
    m = np.zeros((h, w), np.uint8)
    cv2.polylines(m, [q], False, 1, max(1, int(round(width))), cv2.LINE_8, 4)
    return m.astype(bool)


def _model_error(path: np.ndarray, cov: np.ndarray, origin: tuple[int, int], t: float) -> float:
    h, w = cov.shape
    ss = 4
    canvas = np.zeros((h * ss, w * ss), np.uint8)
    q = np.round(((path - np.array(origin)) * ss - 0.5) * 16).astype(np.int32)
    cv2.polylines(canvas, [q], False, 255, max(1, int(round(t * ss))), cv2.LINE_8, 4)
    model = cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    return float(((model - cov) ** 2).sum())


def _insert_missing_corners(path: np.ndarray, cov: np.ndarray, t: float, passes: int = 2) -> np.ndarray:
    """Add vertices where connected line ink lies beyond the traced stroke.

    Two sharp corners closer together than about two stroke widths are
    averaged by column centroids into one vertex. Ink of the line that the
    traced stroke does not explain, connected to it and within a few widths,
    marks such a missing corner; a vertex is inserted there only when a local
    stroke-model fit confirms the improvement.
    """
    H, W = cov.shape
    r = 0.5 * t
    out = path.copy()
    pad = int(math.ceil(4 * t + 4))
    x0 = int(max(0, math.floor(out[:, 0].min()) - pad))
    y0 = int(max(0, math.floor(out[:, 1].min()) - pad))
    x1 = int(min(W, math.ceil(out[:, 0].max()) + pad))
    y1 = int(min(H, math.ceil(out[:, 1].max()) + pad))
    crop = cov[y0:y1, x0:x1]
    ink = crop >= 0.5
    for _ in range(passes):
        explained = _band(out, crop.shape, (x0, y0), 2 * r + 2.0)
        near = _band(out, crop.shape, (x0, y0), 2 * r + 6.0 * t)
        resid = ink & ~explained & near
        n, lab, st, _ = cv2.connectedComponentsWithStats(resid.astype(np.uint8), connectivity=8)
        if n <= 1:
            break
        touch = cv2.dilate(explained.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        inserted = 0
        min_area = max(4.0, 0.35 * t * t)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < min_area:
                continue
            comp = lab == i
            if not (comp & touch).any():
                continue  # not connected to the line: text/label, ignore
            ys, xs = np.nonzero(comp)
            pts = np.column_stack([xs + 0.5 + x0, ys + 0.5 + y0])
            # nearest segment of the current path
            a, b = out[:-1], out[1:]
            c = pts.mean(axis=0)
            ab = b - a
            tt = np.clip(((c - a) * ab).sum(axis=1) / np.maximum((ab ** 2).sum(axis=1), 1e-9), 0, 1)
            proj = a + ab * tt[:, None]
            k = int(np.argmin(np.linalg.norm(proj - c, axis=1)))
            seg_a, seg_b = out[k], out[k + 1]
            d = seg_b - seg_a
            L = float(np.linalg.norm(d))
            if L < 1e-6:
                continue
            u = d / L
            nrm = np.array([-u[1], u[0]])
            off = (pts - seg_a) @ nrm
            side = np.sign(np.median(off))
            far = pts[np.argmax(off * side)]
            vtx = far - nrm * side * r
            # A missing corner sits close to the traced stroke and away from
            # the line ends (whose caps are handled separately).
            if abs(float((vtx - seg_a) @ nrm)) > 2.5 * t:
                continue
            along = float((vtx - seg_a) @ u)
            if along < 0.5 * t or along > L - 0.5 * t:
                continue
            total = geo.cumulative_length(out)
            pos = total[k] + along
            if pos < 3.0 * t or pos > total[-1] - 3.0 * t:
                continue
            cand = np.vstack([out[: k + 1], vtx, out[k + 1 :]])
            # local acceptance test on the component's neighbourhood
            bx0 = int(max(0, xs.min() - 2 * t - 2))
            by0 = int(max(0, ys.min() - 2 * t - 2))
            bx1 = int(min(crop.shape[1], xs.max() + 2 * t + 3))
            by1 = int(min(crop.shape[0], ys.max() + 2 * t + 3))
            win = crop[by0:by1, bx0:bx1]
            org = (x0 + bx0, y0 + by0)
            e_old = _model_error(out, win, org, t)
            e_new = _model_error(cand, win, org, t)
            if e_new < 0.6 * e_old:
                out = cand
                inserted += 1
        if not inserted:
            break
        out = _fit_vertices_to_ink(out, cov, t)
    return out


def _finalise_path(
    dense: np.ndarray, thickness: float, simplify_px: float, ink: np.ndarray | None = None, cov: np.ndarray | None = None
) -> tuple[np.ndarray, float]:
    dense = geo.dedupe(dense)
    if len(dense) < 2:
        return dense, 0.0
    keep = geo.rdp_indices(dense, simplify_px)

    def on_ink(p: np.ndarray) -> bool:
        if ink is None:
            return True
        x, y = int(np.floor(p[0])), int(np.floor(p[1]))
        h, w = ink.shape
        win = ink[max(0, y - 1) : min(h, y + 2), max(0, x - 1) : min(w, x + 2)]
        return bool(win.size and win.max() > 0.2)

    path, exact = geo.recover_corners(dense, keep, thickness, accept=on_ink, return_exact=True)
    if ink is not None and len(path) >= 2:
        full = cov if cov is not None else ink
        path = _snap_spikes(path, exact, full, thickness)
        path = _fit_vertices_to_ink(path, full, thickness)
        path = _insert_missing_corners(path, full, thickness)
        path = _refine_endpoints(path, dense, full, thickness)
    else:
        r = 0.5 * thickness
        L = geo.total_length(path)
        if L > 8 * r and r > 0.5:
            path = geo.sub_path(path, r, L - r)
    path = geo.dedupe(path)
    # Residual: dense samples vs final path.
    sample = dense[:: max(1, len(dense) // 4000)]
    res = float(np.sqrt(np.mean(geo.distance_to_polyline(sample, path) ** 2))) if len(path) > 1 else 0.0
    return path, res


def _confidence(coverage: float, max_gap_frac: float, ambiguity: float, span: float, residual: float, thickness: float) -> float:
    f_cov = float(np.clip((coverage - 0.5) / 0.45, 0.0, 1.0)) ** 0.5
    f_gap = 1.0 - 0.5 * float(np.clip(max_gap_frac / 0.06, 0.0, 1.0))
    f_amb = 1.0 - 0.6 * float(np.clip(ambiguity / 0.35, 0.0, 1.0))
    f_span = float(np.clip(span / 0.30, 0.0, 1.0))
    f_res = 1.0 - 0.5 * float(np.clip((residual - 0.5 - 0.1 * thickness) / 2.0, 0.0, 1.0))
    return float(f_cov * f_gap * f_amb * f_span * f_res)


def _straight_axis_like(path: np.ndarray, width: int) -> bool:
    simp = geo.rdp(path, 2.0)
    if len(simp) > 2:
        return False
    d = simp[-1] - simp[0]
    ang = abs(math.degrees(math.atan2(d[1], d[0]))) % 180
    return ang < 2 or abs(ang - 90) < 2 or ang > 178


def analyze(rgb: np.ndarray, params: DetectParams) -> Analysis:
    h, w = rgb.shape[:2]
    lab = rgb_to_lab(rgb)
    bg = estimate_background(lab).astype(np.float32)
    warnings: list[str] = []
    de_bg = delta_e(lab, bg).astype(np.float32)

    auto_region = estimate_plot_region(de_bg)
    if params.region is not None:
        rx0, ry0, rx1, ry1 = params.region
        region = (int(rx0 * w), int(ry0 * h), int(math.ceil(rx1 * w)), int(math.ceil(ry1 * h)))
        region_source = "manual"
        auto_for_filter = None
    else:
        region = (0, 0, w, h)
        region_source = "auto" if auto_region else "full"
        auto_for_filter = auto_region
    x0, y0, x1, y1 = region
    if (x1 - x0) < 24 or (y1 - y0) < 24:
        raise DetectionError("The graph region is too small to analyse.", "region_too_small")
    region_mask = np.zeros((h, w), bool)
    region_mask[y0:y1, x0:x1] = True

    colors: list[dict[str, Any]]
    if params.mode == "color":
        target = np.asarray(hex_to_rgb(params.color_hex or "#FF0000"), np.float32)
        colors = [{"lab": rgb_to_lab(target.reshape(1, 1, 3)).reshape(3), "kind": "picked", "weight": 1.0}]
        if np.linalg.norm(colors[0]["lab"] - bg) < 12.0:
            raise DetectionError("The picked colour is almost identical to the chart background.", "color_is_background")
    else:
        colors = find_color_candidates(lab, bg, region_mask, params.max_candidates)
        if not colors:
            raise DetectionError("No line-like colours stand out from the background.", "no_colors")

    # Axes / gridlines / frames in any colour. JPEG chroma bleeding can tint
    # an axis right next to a line with the line's colour, so they are
    # removed from every candidate, not only same-coloured ones.
    rx0, ry0, rx1, ry1 = region
    strong = np.zeros((h, w), bool)
    strong[ry0:ry1, rx0:rx1] = de_bg[ry0:ry1, rx0:rx1] > 25.0
    gh, gv = long_straight_structures(strong, int(0.55 * (rx1 - rx0)), int(0.55 * (ry1 - ry0)))
    global_straight = gh | gv
    if not global_straight.any():
        global_straight = None

    ink_idx = np.nonzero(de_bg > 6.0)
    lab_ink = lab[ink_idx]
    traced: list[TracedLine] = []
    for c in colors:
        W, COV = _sparse_membership(lab_ink, ink_idx, (h, w), bg, np.asarray(c["lab"], np.float32), params.sensitivity)
        res = _trace_color(W, COV, params, region, auto_for_filter, global_straight)
        if res is None:
            continue
        path, residual = _finalise_path(res["dense"], res["thickness"], params.simplify_px, res["ink"], res["cov"])
        if len(path) < 2:
            continue
        rgb_c = tuple(float(v) for v in lab_to_rgb(c["lab"])[0])
        conf = _confidence(res["coverage"], res["max_gap"] / w, res["ambiguity"], res["span"], residual, res["thickness"])
        score = res["span"] * (0.4 + 0.6 * res["coverage"]) * (0.6 + 0.4 * conf)
        notes: list[str] = []
        if _straight_axis_like(path, w):
            score *= 0.15
            notes.append("Perfectly straight horizontal/vertical: probably an axis or gridline.")
        if c["kind"] == "achromatic":
            score *= 0.85
        if res["method"] == "skeleton":
            notes.append("Non left-to-right geometry: traced with general curve mode.")
        traced.append(
            TracedLine(
                id=-1,
                kind=c["kind"],
                color_rgb=rgb_c,  # type: ignore[arg-type]
                dense=res["dense"],
                path=path,
                thickness=res["thickness"],
                coverage=res["coverage"],
                span=res["span"],
                max_gap=res["max_gap"],
                ambiguity=res["ambiguity"],
                residual=residual,
                confidence=conf,
                score=score,
                method=res["method"],
                ambiguous_ranges=res["ranges"],
                notes=notes,
            )
        )
    if not traced:
        raise DetectionError(
            "No continuous graph line was found. Try Pick Color, raise Sensitivity, or restrict the Region.",
            "no_line",
        )

    # Lines split into two colours (e.g. a pre-existing highlight): join.
    if params.join_split_colors and params.mode == "auto" and len(traced) > 1:
        joined = _join_split(traced, w)
        traced.extend(joined)

    traced.sort(key=lambda t: -t.score)
    traced = traced[: params.max_candidates]
    for i, t in enumerate(traced):
        t.id = i

    selected = traced[0].id
    if params.candidate is not None:
        match = None
        if params.candidate_hex:
            want = np.asarray(hex_to_rgb(params.candidate_hex))
            dists = [np.linalg.norm(np.asarray(t.color_rgb) - want) + (0.0 if t.id == params.candidate else 0.05) for t in traced]
            k = int(np.argmin(dists))
            if dists[k] < 0.12:
                match = traced[k].id
        elif 0 <= params.candidate < len(traced):
            match = params.candidate
        if match is None:
            warnings.append("The previously chosen line was not found again; using the best match.")
        else:
            selected = match

    sel = next(t for t in traced if t.id == selected)
    if sel.confidence < 0.5:
        warnings.append("Low detection confidence: check the preview before using the result.")
    if sum(1 for t in traced if t.score > 0.5 * sel.score and t.id != sel.id and t.kind != "joined") >= 1:
        warnings.append("Several graph lines found: choose the line to trace if this is not the right one.")
    return Analysis(
        width=w,
        height=h,
        background_rgb=tuple(float(v) for v in lab_to_rgb(bg)[0]),  # type: ignore[arg-type]
        region_px=auto_region if (params.region is None and auto_region) else region,
        region_source=region_source,
        lines=traced,
        selected=selected,
        warnings=warnings,
    )


def _join_split(traced: list[TracedLine], width: int) -> list[TracedLine]:
    out: list[TracedLine] = []
    singles = [t for t in traced if t.kind != "joined" and t.score > 0.02]
    for i, a in enumerate(singles):
        for b in singles[i + 1 :]:
            first, second = (a, b) if a.path[0, 0] <= b.path[0, 0] else (b, a)
            gap = float(np.linalg.norm(second.path[0] - first.path[-1]))
            limit = max(6.0 * max(first.thickness, second.thickness), 0.02 * width)
            # Must be end-to-end, not overlapping in x.
            if gap > limit or second.path[0, 0] < first.path[-1, 0] - 2 * first.thickness:
                continue
            dense = np.vstack([first.dense, second.dense])
            path = np.vstack([first.path, second.path])
            L1 = geo.total_length(first.path)
            L = geo.total_length(path)
            score = (first.score + second.score) * 1.05
            out.append(
                TracedLine(
                    id=-1,
                    kind="joined",
                    color_rgb=second.color_rgb if L1 > 0.5 * L else first.color_rgb,
                    dense=dense,
                    path=path,
                    thickness=max(first.thickness, second.thickness),
                    coverage=min(first.coverage, second.coverage),
                    span=first.span + second.span,
                    max_gap=max(first.max_gap, second.max_gap, gap),
                    ambiguity=max(first.ambiguity, second.ambiguity),
                    residual=max(first.residual, second.residual),
                    confidence=min(first.confidence, second.confidence),
                    score=score,
                    method=first.method,
                    ambiguous_ranges=first.ambiguous_ranges + second.ambiguous_ranges,
                    parts=[
                        {"color": rgb_to_hex(first.color_rgb), "from": 0.0, "to": round(L1 / max(L, 1e-6), 4)},
                        {"color": rgb_to_hex(second.color_rgb), "from": round(L1 / max(L, 1e-6), 4), "to": 1.0},
                    ],
                    notes=[
                        "This line changes colour part-way ({} then {}); the source may already contain a highlight.".format(
                            rgb_to_hex(first.color_rgb), rgb_to_hex(second.color_rgb)
                        )
                    ],
                )
            )
    return out
