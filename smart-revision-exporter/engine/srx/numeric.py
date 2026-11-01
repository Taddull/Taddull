"""Numeric helpers.  Uses numpy when available, otherwise pure Python.

The pure-Python paths are exact but slow, so callers only use them on small
windows (a few thousand samples / one video plane at a time).
"""

from __future__ import annotations

import array
import math
from typing import List, Optional, Sequence, Tuple

try:  # pragma: no cover - environment dependent
    import numpy as np  # type: ignore
    HAVE_NUMPY = True
except Exception:  # pragma: no cover
    np = None
    HAVE_NUMPY = False


def floats_from_bytes(b: bytes):
    if HAVE_NUMPY:
        return np.frombuffer(b, dtype="<f4").astype(np.float64)
    a = array.array("f")
    a.frombytes(b)
    return a


def to_list(x) -> List[float]:
    return list(x)


def energy(x) -> float:
    if HAVE_NUMPY:
        x = np.asarray(x, dtype=np.float64)
        return float(np.dot(x, x))
    return float(sum(v * v for v in x))


def sse(a, b) -> float:
    if HAVE_NUMPY:
        d = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
        return float(np.dot(d, d))
    return float(sum((x - y) ** 2 for x, y in zip(a, b)))


def max_abs_diff(a, b) -> float:
    if HAVE_NUMPY:
        if len(a) == 0:
            return 0.0
        return float(np.max(np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64))))
    return max((abs(x - y) for x, y in zip(a, b)), default=0.0)


def snr_db(ref, test) -> Optional[float]:
    e = energy(ref)
    n = sse(ref, test)
    if e <= 1e-12:
        return None
    if n <= 1e-20:
        return float("inf")
    return 10.0 * math.log10(e / n)


def best_lag(ref, sig, maxlag: int) -> Tuple[int, float]:
    """Integer lag L maximising the correlation of ref[i] with sig[i+L].

    Both signals are pre-emphasised (first difference) so tonal content gives a
    sharp peak.  `sig` must be longer than `ref` by 2*maxlag and centred: sig
    index maxlag corresponds to ref index 0.  See `subsample_lag` for the
    interpolated estimate.
    """
    lag, corr, _ = subsample_lag(ref, sig, maxlag)
    return lag, corr


def _diff(x):
    if HAVE_NUMPY:
        a = np.asarray(x, dtype=np.float64)
        return np.diff(a)
    return [x[i + 1] - x[i] for i in range(len(x) - 1)]


def subsample_lag(ref, sig, maxlag: int) -> Tuple[int, float, float]:
    """Return (integer lag, correlation at that lag, parabolic sub-sample lag)."""
    ref = _diff(ref)
    sig = _diff(sig)
    corrs = _corr_curve(ref, sig, maxlag)
    i = max(range(len(corrs)), key=lambda k: corrs[k])
    frac = float(i - maxlag)
    if 0 < i < len(corrs) - 1:
        y0, y1, y2 = corrs[i - 1], corrs[i], corrs[i + 1]
        den = y0 - 2 * y1 + y2
        if den != 0:
            frac += 0.5 * (y0 - y2) / den
    return i - maxlag, corrs[i], frac


def _corr_curve(ref, sig, maxlag: int) -> List[float]:
    n = len(ref)
    out = []
    if HAVE_NUMPY:
        r = np.asarray(ref, dtype=np.float64)
        s = np.asarray(sig, dtype=np.float64)
        rn = math.sqrt(float(np.dot(r, r))) or 1e-12
        for lag in range(-maxlag, maxlag + 1):
            seg = s[maxlag + lag: maxlag + lag + n]
            sn = math.sqrt(float(np.dot(seg, seg))) or 1e-12
            out.append(float(np.dot(r, seg)) / (rn * sn))
        return out
    rn = math.sqrt(sum(v * v for v in ref)) or 1e-12
    for lag in range(-maxlag, maxlag + 1):
        seg = sig[maxlag + lag: maxlag + lag + n]
        sn = math.sqrt(sum(v * v for v in seg)) or 1e-12
        out.append(sum(x * y for x, y in zip(ref, seg)) / (rn * sn))
    return out


def deinterleave_channel(x, channels: int, ch: int):
    if HAVE_NUMPY:
        return np.asarray(x)[ch::channels]
    return x[ch::channels]


def mixdown(x, channels: int):
    if channels == 1:
        return x
    if HAVE_NUMPY:
        a = np.asarray(x, dtype=np.float64).reshape(-1, channels)
        return a.mean(axis=1)
    out = []
    for i in range(0, len(x) - channels + 1, channels):
        out.append(sum(x[i:i + channels]) / channels)
    return out


def plane_sse(a: bytes, b: bytes, offset: int, width: int, height: int, bps: int,
              row_step: int = 1) -> Tuple[float, int]:
    """Sum of squared differences of one plane; returns (sse, samples)."""
    size = width * height * bps
    pa = a[offset:offset + size]
    pb = b[offset:offset + size]
    if HAVE_NUMPY:
        dt = "<u2" if bps == 2 else "u1"
        xa = np.frombuffer(pa, dtype=dt).reshape(height, width)[::row_step].astype(np.int64)
        xb = np.frombuffer(pb, dtype=dt).reshape(height, width)[::row_step].astype(np.int64)
        d = xa - xb
        return float(np.sum(d * d)), int(d.size)
    if bps == 2:
        xa = array.array("H")
        xa.frombytes(pa)
        xb = array.array("H")
        xb.frombytes(pb)
    else:
        xa, xb = pa, pb
    total = 0
    count = 0
    for row in range(0, height, max(1, row_step)):
        s = row * width
        ra = xa[s:s + width]
        rb = xb[s:s + width]
        total += sum((p - q) * (p - q) for p, q in zip(ra, rb))
        count += width
    return float(total), count


def plane_mean(a: bytes, offset: int, width: int, height: int, bps: int) -> float:
    size = width * height * bps
    p = a[offset:offset + size]
    if HAVE_NUMPY:
        dt = "<u2" if bps == 2 else "u1"
        return float(np.frombuffer(p, dtype=dt).mean())
    if bps == 2:
        x = array.array("H")
        x.frombytes(p)
        return sum(x) / max(1, len(x))
    return sum(p[:: max(1, len(p) // 65536)]) / max(1, len(p[:: max(1, len(p) // 65536)]))


def psnr_from_sse(total_sse: float, count: int, peak: int) -> float:
    if count == 0:
        return float("nan")
    mse = total_sse / count
    if mse <= 0:
        return float("inf")
    return 10.0 * math.log10(peak * peak / mse)
