"""Strict JSON output: no NaN/Infinity (invalid JSON for most parsers).

Infinite values (e.g. PSNR of identical frames) become the string "inf",
NaN becomes null.
"""

from __future__ import annotations

import json
import math
from fractions import Fraction


def clean(obj):
    if isinstance(obj, float):
        if math.isnan(obj):
            return None
        if math.isinf(obj):
            return "inf" if obj > 0 else "-inf"
        return obj
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, Fraction):
        return f"{obj.numerator}/{obj.denominator}"
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    return str(obj)


def dumps(obj, **kw) -> str:
    return json.dumps(clean(obj), allow_nan=False, **kw)


def dump(obj, f, **kw) -> None:
    json.dump(clean(obj), f, allow_nan=False, **kw)
