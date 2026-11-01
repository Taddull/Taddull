"""Rational frame rates and SMPTE timecode conversion (NDF and drop-frame)."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Union

# Resolve reports timeline frame rates as decimal strings.
_KNOWN = {
    "23.976": Fraction(24000, 1001),
    "23.98": Fraction(24000, 1001),
    "24": Fraction(24, 1),
    "25": Fraction(25, 1),
    "29.97": Fraction(30000, 1001),
    "30": Fraction(30, 1),
    "47.952": Fraction(48000, 1001),
    "48": Fraction(48, 1),
    "50": Fraction(50, 1),
    "59.94": Fraction(60000, 1001),
    "60": Fraction(60, 1),
    "95.904": Fraction(96000, 1001),
    "96": Fraction(96, 1),
    "100": Fraction(100, 1),
    "119.88": Fraction(120000, 1001),
    "120": Fraction(120, 1),
}


class TimecodeError(ValueError):
    pass


def parse_rate(value: Union[str, float, int, Fraction]) -> Fraction:
    """Parse '30000/1001', '29.97', 29.97, 24 ... into an exact rational."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    s = str(value).strip()
    if "/" in s:
        n, d = s.split("/", 1)
        return Fraction(int(n), int(d))
    try:
        f = float(s)
    except ValueError:
        raise TimecodeError(f"invalid frame rate '{value}'")
    key = f"{f:.3f}".rstrip("0").rstrip(".")
    if key in _KNOWN:
        return _KNOWN[key]
    for k, v in _KNOWN.items():
        if abs(float(v) - f) < 0.0015:
            return v
    if abs(f - round(f)) < 1e-6:
        return Fraction(int(round(f)), 1)
    raise TimecodeError(f"unrecognised frame rate {value}")


def nominal_fps(rate: Fraction) -> int:
    return int(round(float(rate)))


def is_drop_frame_capable(rate: Fraction) -> bool:
    return rate.denominator == 1001 and nominal_fps(rate) in (30, 60)


_TC_RE = re.compile(r"^(-)?(\d{1,2}):(\d{2}):(\d{2})([:;.,])(\d{2,3})$")


def tc_to_frames(tc: str, rate: Fraction, drop_frame: bool = None) -> int:
    """Convert timecode to a frame count (frames since 00:00:00:00)."""
    m = _TC_RE.match(tc.strip())
    if not m:
        raise TimecodeError(f"invalid timecode '{tc}' (expected HH:MM:SS:FF)")
    neg, hh, mm, ss, sep, ff = m.groups()
    hh, mm, ss, ff = int(hh), int(mm), int(ss), int(ff)
    fps = nominal_fps(rate)
    if drop_frame is None:
        drop_frame = sep in ";," and is_drop_frame_capable(rate)
    if mm > 59 or ss > 59 or ff >= fps:
        raise TimecodeError(f"timecode field out of range in '{tc}' at {fps} fps")
    if drop_frame:
        if not is_drop_frame_capable(rate):
            raise TimecodeError("drop-frame timecode only exists for 29.97 / 59.94 fps")
        drop = 2 * fps // 30
        if ss == 0 and ff < drop and mm % 10 != 0:
            raise TimecodeError(f"'{tc}' does not exist in drop-frame timecode")
        total_minutes = 60 * hh + mm
        frames = (hh * 3600 + mm * 60 + ss) * fps + ff
        frames -= drop * (total_minutes - total_minutes // 10)
    else:
        frames = (hh * 3600 + mm * 60 + ss) * fps + ff
    return -frames if neg else frames


def frames_to_tc(frames: int, rate: Fraction, drop_frame: bool = False) -> str:
    fps = nominal_fps(rate)
    neg = frames < 0
    frames = abs(frames)
    if drop_frame:
        if not is_drop_frame_capable(rate):
            raise TimecodeError("drop-frame timecode only exists for 29.97 / 59.94 fps")
        drop = 2 * fps // 30
        per_10min = fps * 600 - drop * 9
        per_min = fps * 60 - drop
        d, m = divmod(frames, per_10min)
        if m > drop:
            frames += drop * 9 * d + drop * ((m - drop) // per_min)
        else:
            frames += drop * 9 * d
    ff = frames % fps
    s_total = frames // fps
    ss = s_total % 60
    mm = (s_total // 60) % 60
    hh = s_total // 3600
    sep = ";" if drop_frame else ":"
    return f"{'-' if neg else ''}{hh:02d}:{mm:02d}:{ss:02d}{sep}{ff:02d}"


def frames_to_seconds(frames: int, rate: Fraction) -> Fraction:
    return Fraction(frames) / rate


def frame_to_audio_sample(frame: int, rate: Fraction, sample_rate: int) -> Fraction:
    """Exact (possibly fractional) audio sample position of a frame boundary."""
    return Fraction(frame) * sample_rate / rate
