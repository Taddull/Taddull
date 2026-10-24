"""Fusion composition fragments (".setting" text) for the generated highlight.

Everything here follows serialisations observed in real Fusion/Resolve
compositions and macros (see docs/FUSION_API_NOTES.md): Paint tools chain
strokes through their ``Paint`` input/``Out`` output, a ``PolylineStroke``
carries ``Brushes``/``ApplyModes`` tables plus ``SoftBrush.*`` and
``PaintApplyColor.*`` inputs, ``WriteOnEnd`` is driven by a ``BezierSpline``
whose keyframes carry absolute ``LH``/``RH`` handles, polyline points are
``{ Linear = true, X, Y, LX, LY, RX, RY }`` with handle offsets relative to the
point, and Loader clips use a ``Clips = { Clip { ... } }`` block with
``["Clip1.PNGFormat.PostMultiply"]``.

The two numbers that cannot be read from samples - the vertical scale of
polyline coordinates and the unit of ``SoftBrush.Size`` - are parameters
(:class:`Calibration`). The Fusion launcher renders the generated stroke,
measures it and refines the calibration automatically (see verify.py).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .easing import Curve
from .luaser import lua_number as N
from .luaser import lua_string as S

OWNER = "MaxTrace+"


@dataclass
class Calibration:
    # "width": Y normalised by image width (Y range +-0.5*H/W) - Fusion's
    #          resolution-independent convention for shapes/masks.
    # "height": Y normalised by image height (Y range +-0.5).
    y_mode: str = "width"
    y_scale: float = 1.0  # extra multiplicative correction (measured)
    x_offset_px: float = 0.0
    y_offset_px: float = 0.0
    size_scale: float = 1.0  # SoftBrush.Size = diameter_px / width * size_scale
    verified: bool = False
    source: str = "default"

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> "Calibration":
        c = Calibration()
        for k, v in (d or {}).items():
            if hasattr(c, k) and v is not None:
                setattr(c, k, type(getattr(c, k))(v))
        if c.y_mode not in ("width", "height"):
            c.y_mode = "width"
        c.size_scale = float(min(max(c.size_scale, 0.05), 20.0))
        c.y_scale = float(min(max(c.y_scale, 0.2), 5.0))
        return c

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def to_fusion_xy(points_px: np.ndarray, width: int, height: int, cal: Calibration) -> np.ndarray:
    """Source pixel coordinates -> polyline coordinates relative to Center (0.5, 0.5)."""
    p = np.asarray(points_px, np.float64)
    x = (p[:, 0] + cal.x_offset_px) / width - 0.5
    yn = 0.5 - (p[:, 1] + cal.y_offset_px) / height
    if cal.y_mode == "width":
        yn = yn * (height / float(width))
    return np.column_stack([x, yn * cal.y_scale])


def from_fusion_xy(points_f: np.ndarray, width: int, height: int, cal: Calibration) -> np.ndarray:
    p = np.asarray(points_f, np.float64)
    yn = p[:, 1] / cal.y_scale
    if cal.y_mode == "width":
        yn = yn * (width / float(height))
    x = (p[:, 0] + 0.5) * width - cal.x_offset_px
    y = (0.5 - yn) * height - cal.y_offset_px
    return np.column_stack([x, y])


def polyline_text(points_f: np.ndarray, indent: str) -> str:
    """Open, linear polyline in Fusion's serialisation."""
    pts = np.asarray(points_f, np.float64)
    n = len(pts)
    lines = []
    for i in range(n):
        x, y = pts[i]
        fields = ["Linear = true", f"X = {N(x)}", f"Y = {N(y)}"]
        if i > 0:
            d = (pts[i - 1] - pts[i]) / 3.0
            fields += [f"LX = {N(d[0])}", f"LY = {N(d[1])}"]
        if i < n - 1:
            d = (pts[i + 1] - pts[i]) / 3.0
            fields += [f"RX = {N(d[0])}", f"RY = {N(d[1])}"]
        lines.append(indent + "\t{ " + ", ".join(fields) + " },")
    return "Polyline {\n" + indent + "Points = {\n" + "\n".join(lines) + "\n" + indent + "}\n" + indent[:-1] + "}"


def _custom(gen_id: str, role: str, extra: dict[str, Any] | None = None) -> str:
    fields = [f"Owner = {S(OWNER)}", f"GenID = {S(gen_id)}", f"Role = {S(role)}"]
    for k, v in (extra or {}).items():
        if isinstance(v, str):
            fields.append(f"{k} = {S(v)}")
        elif isinstance(v, bool):
            fields.append(f"{k} = {'true' if v else 'false'}")
        else:
            fields.append(f"{k} = {N(float(v))}")
    return "CustomData = { MaxTrace = { " + ", ".join(fields) + " } },"


def _spline_keys(t0: int, frames: int, v0: float, v1: float, curve: Curve) -> str:
    """Two keyframes reproducing the cubic-bezier timing curve exactly."""
    t1 = t0 + frames
    d = float(frames)
    rh = (t0 + curve.x1 * d, v0 + curve.y1 * (v1 - v0))
    lh = (t0 + curve.x2 * d, v0 + curve.y2 * (v1 - v0))
    flags = " Flags = { Linear = true }," if curve.linear else ""
    return (
        f"\t\t\t\t[{t0}] = {{ {N(v0)}, RH = {{ {N(rh[0])}, {N(rh[1])} }},{flags} }},\n"
        f"\t\t\t\t[{t1}] = {{ {N(v1)}, LH = {{ {N(lh[0])}, {N(lh[1])} }},{flags} }},\n"
    )


def _step_keys(t0: int, v_before: float, v_after: float) -> str:
    return (
        f"\t\t\t\t[{t0}] = {{ {N(v_before)}, RH = {{ {N(t0 + 1 / 3)}, {N(v_before)} }}, Flags = {{ Linear = true }}, }},\n"
        f"\t\t\t\t[{t0 + 1}] = {{ {N(v_after)}, LH = {{ {N(t0 + 2 / 3)}, {N(v_after)} }}, Flags = {{ Linear = true }}, }},\n"
    )


@dataclass
class NativeStyle:
    color: tuple[float, float, float]
    thickness_px: float  # stroke diameter in source pixels
    opacity: float
    softness: float  # 0..1
    halo: float  # 0..1
    glow: float  # 0..1


def native_setting(
    gen_id: str,
    path_px: np.ndarray,
    width: int,
    height: int,
    style: NativeStyle,
    anim_start: int,
    anim_frames: int,
    curve: Curve,
    cal: Calibration,
) -> dict[str, Any]:
    """Editable native highlight: transparent canvas + Paint with one PolylineStroke.

    Returns the setting text plus the names/roles of the tools it defines.
    """
    pts_f = to_fusion_xy(path_px, width, height, cal)
    size = style.thickness_px / float(width) * cal.size_scale
    softness = 0.02 + 0.55 * float(style.softness)
    r, g, b = (float(c) for c in style.color)
    tools: list[str] = []
    roles: dict[str, str] = {}

    def add(name: str, role: str, body: str) -> None:
        tools.append(f"\t\t{name} = {body}")
        roles[name] = role

    add(
        "MaxTrace_Canvas",
        "canvas",
        "Background {\n"
        "\t\t\tNameSet = true,\n"
        f"\t\t\t{_custom(gen_id, 'canvas')}\n"
        "\t\t\tInputs = {\n"
        "\t\t\t\tUseFrameFormatSettings = Input { Value = 0, },\n"
        f"\t\t\t\tWidth = Input {{ Value = {int(width)}, }},\n"
        f"\t\t\t\tHeight = Input {{ Value = {int(height)}, }},\n"
        '\t\t\t\t["Gamut.SLogVersion"] = Input { Value = FuID { "SLog2" }, },\n'
        "\t\t\t\tTopLeftRed = Input { Value = 0, },\n"
        "\t\t\t\tTopLeftGreen = Input { Value = 0, },\n"
        "\t\t\t\tTopLeftBlue = Input { Value = 0, },\n"
        "\t\t\t\tTopLeftAlpha = Input { Value = 0, },\n"
        "\t\t\t},\n"
        "\t\t\tViewInfo = OperatorInfo { Pos = { 0, -66 } },\n"
        "\t\t}",
    )
    poly = polyline_text(pts_f, "\t\t\t\t\t\t")
    add(
        "MaxTrace_Path",
        "stroke",
        "PolylineStroke {\n"
        "\t\t\tPoints = {\n\t\t\t},\n"
        "\t\t\tIsThreaded = false,\n"
        '\t\t\tBrushes = { "SoftBrush" },\n'
        '\t\t\tApplyModes = { "PaintApplyColor" },\n'
        "\t\t\tCtrlWZoom = false,\n"
        "\t\t\tNameSet = true,\n"
        f"\t\t\t{_custom(gen_id, 'stroke', {'Points': len(pts_f), 'SizePx': style.thickness_px})}\n"
        "\t\t\tInputs = {\n"
        "\t\t\t\tBrushControls = Input { Value = 1, },\n"
        f'\t\t\t\t["SoftBrush.Size"] = Input {{ Value = {N(size)}, }},\n'
        f'\t\t\t\t["SoftBrush.Softness"] = Input {{ Value = {N(softness)}, }},\n'
        '\t\t\t\tApplyMode = Input { Value = FuID { "PaintApplyColor" }, },\n'
        f'\t\t\t\t["PaintApplyColor.Red"] = Input {{ Value = {N(r)}, }},\n'
        f'\t\t\t\t["PaintApplyColor.Green"] = Input {{ Value = {N(g)}, }},\n'
        f'\t\t\t\t["PaintApplyColor.Blue"] = Input {{ Value = {N(b)}, }},\n'
        "\t\t\t\tStrokeControls = Input { Value = 1, },\n"
        "\t\t\t\tWriteOnStart = Input { Value = 0, },\n"
        '\t\t\t\tWriteOnEnd = Input { SourceOp = "MaxTrace_PathWriteOn", Source = "Value", },\n'
        "\t\t\t\tCenter = Input { Value = { 0.5, 0.5 }, },\n"
        f"\t\t\t\tPolyline = Input {{\n\t\t\t\t\tValue = {poly},\n\t\t\t\t}},\n"
        "\t\t\t},\n"
        "\t\t}",
    )
    add(
        "MaxTrace_PathWriteOn",
        "writeon",
        "BezierSpline {\n"
        "\t\t\tSplineColor = { Red = 255, Green = 64, Blue = 64 },\n"
        "\t\t\tNameSet = true,\n"
        "\t\t\tKeyFrames = {\n" + _spline_keys(anim_start, anim_frames, 0.0, 1.0, curve) + "\t\t\t}\n"
        "\t\t}",
    )
    add(
        "MaxTrace_Stroke",
        "paint",
        "Paint {\n"
        "\t\t\tNameSet = true,\n"
        f"\t\t\t{_custom(gen_id, 'paint')}\n"
        "\t\t\tInputs = {\n"
        '\t\t\t\tInput = Input { SourceOp = "MaxTrace_Canvas", Source = "Output", },\n'
        '\t\t\t\tPaint = Input { SourceOp = "MaxTrace_Path", Source = "Out", },\n'
        "\t\t\t},\n"
        "\t\t\tViewInfo = OperatorInfo { Pos = { 110, -66 } },\n"
        "\t\t}",
    )
    last = "MaxTrace_Stroke"
    x = 220
    if style.halo > 0:
        blur = max(1.0, style.thickness_px * 1.2)
        add(
            "MaxTrace_Soft",
            "soft",
            "Blur {\n"
            "\t\t\tNameSet = true,\n"
            f"\t\t\t{_custom(gen_id, 'soft')}\n"
            "\t\t\tInputs = {\n"
            f"\t\t\t\tXBlurSize = Input {{ Value = {N(blur)}, }},\n"
            '\t\t\t\tInput = Input { SourceOp = "MaxTrace_Stroke", Source = "Output", },\n'
            "\t\t\t},\n"
            f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, -99 }} }},\n"
            "\t\t}",
        )
        add(
            "MaxTrace_SoftMix",
            "softmix",
            "Merge {\n"
            "\t\t\tNameSet = true,\n"
            f"\t\t\t{_custom(gen_id, 'softmix')}\n"
            "\t\t\tInputs = {\n"
            '\t\t\t\tBackground = Input { SourceOp = "MaxTrace_Stroke", Source = "Output", },\n'
            '\t\t\t\tForeground = Input { SourceOp = "MaxTrace_Soft", Source = "Output", },\n'
            f"\t\t\t\tBlend = Input {{ Value = {N(0.25 + 0.6 * style.halo)}, }},\n"
            "\t\t\t\tPerformDepthMerge = Input { Value = 0, },\n"
            "\t\t\t},\n"
            f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, -66 }} }},\n"
            "\t\t}",
        )
        last = "MaxTrace_SoftMix"
        x += 110
    if style.glow > 0:
        add(
            "MaxTrace_Glow",
            "glow",
            "SoftGlow {\n"
            "\t\t\tNameSet = true,\n"
            f"\t\t\t{_custom(gen_id, 'glow')}\n"
            "\t\t\tInputs = {\n"
            "\t\t\t\tThreshold = Input { Value = 0, },\n"
            f"\t\t\t\tGain = Input {{ Value = {N(0.15 + 0.6 * style.glow)}, }},\n"
            f"\t\t\t\tXGlowSize = Input {{ Value = {N(max(2.0, style.thickness_px * 2.5))}, }},\n"
            f'\t\t\t\tInput = Input {{ SourceOp = "{last}", Source = "Output", }},\n'
            "\t\t\t},\n"
            f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, -66 }} }},\n"
            "\t\t}",
        )
        last = "MaxTrace_Glow"
        x += 110
    _merge(add, gen_id, last, anim_start, style.opacity, x, "native")
    return {
        "text": "{\n\tTools = ordered() {\n" + ",\n".join(tools) + "\n\t},\n}\n",
        "tools": roles,
        "layer_tool": last,
        "merge_tool": "MaxTrace_Merge",
        "brush_size": size,
        "points_fusion": pts_f.tolist(),
    }


def _merge(add, gen_id: str, fg: str, anim_start: int, opacity: float, x: int, mode: str) -> None:
    # Blend is 0 up to the first animation frame (guarantees nothing shows
    # before the reveal starts, whatever a zero-length stroke renders) and
    # equals the chosen opacity from the next frame on.
    add(
        "MaxTrace_MergeBlend",
        "blend",
        "BezierSpline {\n"
        "\t\t\tSplineColor = { Red = 255, Green = 128, Blue = 128 },\n"
        "\t\t\tNameSet = true,\n"
        "\t\t\tKeyFrames = {\n" + _step_keys(anim_start, 0.0, float(opacity)) + "\t\t\t}\n"
        "\t\t}",
    )
    add(
        "MaxTrace_Merge",
        "merge",
        "Merge {\n"
        "\t\t\tNameSet = true,\n"
        f"\t\t\t{_custom(gen_id, 'merge', {'Mode': mode})}\n"
        "\t\t\tInputs = {\n"
        f'\t\t\t\tForeground = Input {{ SourceOp = "{fg}", Source = "Output", }},\n'
        '\t\t\t\tBlend = Input { SourceOp = "MaxTrace_MergeBlend", Source = "Value", },\n'
        "\t\t\t\tPerformDepthMerge = Input { Value = 0, },\n"
        "\t\t\t},\n"
        f"\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 0 }} }},\n"
        "\t\t}",
    )


def raster_setting(
    gen_id: str,
    first_file: str,
    frames: int,
    global_start: int,
    anim_start: int,
    opacity_baked: bool = True,
) -> dict[str, Any]:
    """Rendered fallback: Loader for the PNG sequence + Merge."""
    tools: list[str] = []
    roles: dict[str, str] = {}

    def add(name: str, role: str, body: str) -> None:
        tools.append(f"\t\t{name} = {body}")
        roles[name] = role

    add(
        "MaxTrace_Render",
        "loader",
        "Loader {\n"
        "\t\t\tClips = {\n"
        "\t\t\t\tClip {\n"
        '\t\t\t\t\tID = "Clip1",\n'
        f"\t\t\t\t\tFilename = {S(first_file)},\n"
        '\t\t\t\t\tFormatID = "PNGFormat",\n'
        "\t\t\t\t\tStartFrame = 0,\n"
        f"\t\t\t\t\tLength = {int(frames)},\n"
        "\t\t\t\t\tLengthSetManually = true,\n"
        "\t\t\t\t\tTrimIn = 0,\n"
        f"\t\t\t\t\tTrimOut = {int(frames) - 1},\n"
        "\t\t\t\t\tExtendFirst = 0,\n"
        "\t\t\t\t\tExtendLast = 0,\n"
        "\t\t\t\t\tLoop = 0,\n"
        "\t\t\t\t\tAspectMode = 0,\n"
        "\t\t\t\t\tDepth = 0,\n"
        "\t\t\t\t\tTimeCode = 0,\n"
        f"\t\t\t\t\tGlobalStart = {int(global_start)},\n"
        f"\t\t\t\t\tGlobalEnd = {int(global_start) + int(frames) - 1}\n"
        "\t\t\t\t}\n"
        "\t\t\t},\n"
        "\t\t\tNameSet = true,\n"
        f"\t\t\t{_custom(gen_id, 'loader', {'Frames': frames, 'GlobalStart': global_start})}\n"
        "\t\t\tInputs = {\n"
        '\t\t\t\t["Gamut.SLogVersion"] = Input { Value = FuID { "SLog2" }, },\n'
        '\t\t\t\t["Clip1.PNGFormat.PostMultiply"] = Input { Value = 1, },\n'
        "\t\t\t},\n"
        "\t\t\tViewInfo = OperatorInfo { Pos = { 0, -66 } },\n"
        "\t\t}",
    )
    _merge(add, gen_id, "MaxTrace_Render", anim_start, 1.0, 110, "raster")
    return {
        "text": "{\n\tTools = ordered() {\n" + ",\n".join(tools) + "\n\t},\n}\n",
        "tools": roles,
        "layer_tool": "MaxTrace_Render",
        "merge_tool": "MaxTrace_Merge",
    }
