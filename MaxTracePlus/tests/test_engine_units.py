"""Unit tests: Fusion setting generation, coordinate mapping, worker jobs, Lua JSON."""

import json
import os

import cv2
import numpy as np
import pytest

import synth
from maxtrace import geometry as geo
from maxtrace.easing import Curve
from maxtrace.fusion_setting import Calibration, NativeStyle, from_fusion_xy, native_setting, raster_setting, to_fusion_xy
from maxtrace.luaser import to_lua
from maxtrace.verify import VerifyInput, verify
from maxtrace.render import StrokeStyle, render_still
from maxtrace import worker

lupa = pytest.importorskip("lupa")
from lupa import luajit21  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_setting(text):
    lua = luajit21.LuaRuntime(unpack_returned_tuples=True)
    env = lua.execute(
        """
        local function ctor(kind) return function(t) t = t or {}; t.__ctor = kind; return t end end
        local env = { FuID = function(t) return { __ctor = 'FuID', value = t[1] } end,
                      ordered = function() return function(t) return t end end }
        setmetatable(env, { __index = function(_, k) return ctor(k) end })
        return env
        """
    )
    fn = lua.execute("local text, env = ...; local f, e = loadstring('return ' .. text); assert(f, e); setfenv(f, env); return f()", text, env)
    return fn


PATH = np.array([[100.0, 800.0], [400.0, 200.0], [700.0, 650.0], [1800.0, 300.0]])


@pytest.mark.parametrize("mode", ["width", "height"])
def test_fusion_coordinate_round_trip(mode):
    cal = Calibration(y_mode=mode, y_scale=1.02, x_offset_px=0.3, y_offset_px=-0.4)
    f = to_fusion_xy(PATH, 1920, 1080, cal)
    back = from_fusion_xy(f, 1920, 1080, cal)
    assert np.allclose(back, PATH, atol=1e-9)
    if mode == "width":
        assert abs(to_fusion_xy(np.array([[960.0, 0.0]]), 1920, 1080, Calibration())[0, 1] - 0.28125) < 1e-12
    centre = to_fusion_xy(np.array([[960.0, 540.0]]), 1920, 1080, Calibration(y_mode=mode))
    assert np.allclose(centre, 0.0)


def test_native_setting_is_valid_fusion_syntax_and_complete():
    st = native_setting(
        "abc123",
        PATH,
        1920,
        1080,
        NativeStyle(color=(1.0, 0.125, 0.125), thickness_px=7.0, opacity=0.9, softness=0.2, halo=0.3, glow=0.2),
        24,
        60,
        Curve.from_settings("smooth"),
        Calibration(),
    )
    t = parse_setting(st["text"])
    tools = t.Tools
    for name in ("MaxTrace_Canvas", "MaxTrace_Path", "MaxTrace_PathWriteOn", "MaxTrace_Stroke", "MaxTrace_Soft", "MaxTrace_SoftMix", "MaxTrace_Glow", "MaxTrace_MergeBlend", "MaxTrace_Merge"):
        assert tools[name] is not None, name
    assert tools.MaxTrace_Path.__ctor == "PolylineStroke"
    assert tools.MaxTrace_Stroke.Inputs.Paint.SourceOp == "MaxTrace_Path"
    assert tools.MaxTrace_Stroke.Inputs.Paint.Source == "Out"
    assert tools.MaxTrace_Canvas.Inputs.TopLeftAlpha.Value == 0
    pts = tools.MaxTrace_Path.Inputs.Polyline.Value.Points
    assert pts[1].Linear is True and pts[1].LX is None and pts[1].RX is not None
    n = len(PATH)
    assert pts[n].RX is None and pts[n].LX is not None and pts[n + 1] is None
    keys = tools.MaxTrace_PathWriteOn.KeyFrames
    assert keys[24][1] == 0 and keys[84][1] == 1
    # Smooth handles: RH at t0 + 0.42*d with value 0; LH at t0 + 0.58*d with value 1
    assert keys[24].RH[1] == pytest.approx(24 + 0.42 * 60) and keys[24].RH[2] == pytest.approx(0)
    assert keys[84].LH[1] == pytest.approx(24 + 0.58 * 60) and keys[84].LH[2] == pytest.approx(1)
    blend = tools.MaxTrace_MergeBlend.KeyFrames
    assert blend[24][1] == 0 and blend[25][1] == pytest.approx(0.9)
    assert tools.MaxTrace_Merge.CustomData.MaxTrace.GenID == "abc123"
    assert tools.MaxTrace_Merge.Inputs.Background is None  # wired by the launcher


def test_raster_setting_loader_clip():
    st = raster_setting("g1", "/tmp/a b/MaxTrace_00000.png", 120, -10, 0)
    t = parse_setting(st["text"])
    clip = t.Tools.MaxTrace_Render.Clips[1]
    assert clip.Filename == "/tmp/a b/MaxTrace_00000.png"
    assert clip.Length == 120 and clip.TrimOut == 119 and clip.GlobalStart == -10 and clip.GlobalEnd == 109
    assert t.Tools.MaxTrace_Render.Inputs["Clip1.PNGFormat.PostMultiply"].Value == 1


def test_luaser_escapes_and_roundtrip():
    lua = luajit21.LuaRuntime()
    data = {"a": 'q"uote\\back\nline', "n": [1, 2.5, -3e-7], "nested": {"k-ey": True, "end": False}}
    text = to_lua(data)
    t = lua.execute("return " + text)
    assert t["a"] == data["a"] and t["n"][2] == 2.5 and t["nested"]["k-ey"] is True and t["nested"]["end"] is False


def test_lua_json_module_roundtrip():
    lua = luajit21.LuaRuntime(unpack_returned_tuples=True)
    js = lua.execute("return dofile(...)", os.path.join(ROOT, "lua", "maxtrace", "json.lua"))
    obj = {"name": "Clean Red ✓", "v": [1, 2, 3.25], "s": {"color": "#FF2020", "t": 7}, "e": [], "q": 'a"b'}
    text = js.encode(lua.table_from({"x": 1}), True)
    assert json.loads(text) == {"x": 1}
    decoded = js.decode(json.dumps(obj, ensure_ascii=False))
    assert decoded["name"] == obj["name"] and decoded["v"][3] == 3.25 and decoded["s"]["t"] == 7 and decoded["q"] == 'a"b'
    re = json.loads(js.encode(decoded))
    assert re["s"] == obj["s"] and re["v"] == obj["v"]


# --------------------------------------------------------------------------
# Worker jobs
# --------------------------------------------------------------------------


def _job(tmp_path, spec):
    d = tmp_path / ("job" + str(len(os.listdir(tmp_path))))
    d.mkdir()
    (d / "job.json").write_text(json.dumps(spec))
    code = worker.run_job(str(d))
    res = json.loads((d / "result.json").read_text())
    assert (d / "result.lua").exists() and (d / "status.json").exists()
    return code, res, d


@pytest.fixture
def chart_png(tmp_path):
    return synth.save_chart(synth.case_red_zigzag(), str(tmp_path / "charts"))


def base_spec(img, tmp_path, **kw):
    spec = {
        "job": "build",
        "image": img,
        "cache_dir": str(tmp_path / "cache"),
        "detect": {"mode": "auto"},
        "style": {"color": "#FFD21F", "thickness": 7},
        "timing": {"fps": 24, "duration": 2.5, "motion": "natural", "start_frame": 10, "comp_start": 0, "comp_end": 100},
        "range": {"start": 0.0, "end": 0.58},
        "output": {"mode": "native", "comp_width": 1920, "comp_height": 1080, "render_dir": str(tmp_path / "renders")},
    }
    spec.update(kw)
    return spec


def test_build_native_job_and_cache(tmp_path, chart_png):
    code, res, d = _job(tmp_path, base_spec(chart_png, tmp_path))
    assert code == 0 and res["ok"], res
    assert res["anim_frames"] == 60 and res["anim_start"] == 10 and res["anim_end"] == 70
    assert res["cached"] is False and os.path.isfile(res["setting"])
    L = geo.total_length(np.array(res["path_px"]))
    full = res["selected"]["length_px"]
    assert L == pytest.approx(0.58 * full, rel=0.02)
    code, res2, _ = _job(tmp_path, base_spec(chart_png, tmp_path))
    assert res2["cached"] is True  # unchanged image + detection params -> cached analysis


def test_build_raster_job_writes_sequence(tmp_path, chart_png):
    spec = base_spec(chart_png, tmp_path, output={"mode": "raster", "comp_width": 1920, "comp_height": 1080, "render_dir": str(tmp_path / "renders")})
    code, res, d = _job(tmp_path, spec)
    assert code == 0 and res["ok"], res
    seq = res["sequence"]
    assert seq["frames"] == 101 and os.path.isfile(seq["first_file"])
    files = sorted(f for f in os.listdir(seq["dir"]) if f.endswith(".png"))
    assert len(files) == 101
    img = cv2.imread(os.path.join(seq["dir"], files[70]), cv2.IMREAD_UNCHANGED)
    assert img.shape == (1080, 1920, 4) and img[:, :, 3].max() == 255
    # Same settings again: reuses the rendered sequence.
    code, res2, _ = _job(tmp_path, spec)
    assert res2["sequence"]["dir"] == seq["dir"]


@pytest.mark.parametrize(
    "patch,code",
    [
        ({"timing": {"fps": 0, "duration": 2.5}}, "bad_fps"),
        ({"range": {"start": 0.7, "end": 0.2}}, "bad_range"),
        ({"style": {"color": "nothex"}}, "bad_style"),
        ({"image": "/nonexistent/graph.png"}, "image_load"),
    ],
)
def test_build_job_errors_are_reported(tmp_path, chart_png, patch, code):
    spec = base_spec(chart_png, tmp_path)
    spec.update(patch)
    rc, res, _ = _job(tmp_path, spec)
    assert rc != 0 and res["ok"] is False and res["code"] == code
    assert "traceback" not in res  # user-facing, no raw stack trace


def test_blank_image_reports_no_line(tmp_path):
    p = str(tmp_path / "blank.png")
    cv2.imwrite(p, np.full((600, 900, 3), 255, np.uint8))
    rc, res, _ = _job(tmp_path, base_spec(p, tmp_path))
    assert res["ok"] is False and res["code"] in ("no_colors", "no_line")


def test_same_colour_highlight_is_warned(tmp_path, chart_png):
    spec = base_spec(chart_png, tmp_path, style={"color": "#E02020", "thickness": 7})
    rc, res, _ = _job(tmp_path, spec)
    assert res["ok"]
    assert any(w["code"] == "same_color" for w in res["warnings"])


def test_already_highlighted_source_is_warned(tmp_path):
    p = synth.save_chart(synth.case_already_highlighted(), str(tmp_path / "c"))
    rc, res, _ = _job(tmp_path, base_spec(p, tmp_path, style={"color": "#FF2020", "thickness": 7}))
    assert res["ok"] and any(w["code"] == "already_highlighted" for w in res["warnings"])


def test_thickness_scales_with_output_resolution():
    style = {"thickness": 7}
    assert worker.thickness_in_source(style, 1920, 1080, 1920, 1080) == pytest.approx(7)
    assert worker.thickness_in_source(style, 3840, 2160, 3840, 2160) == pytest.approx(14)
    # 1200x800 screenshot fitted into a 1080p timeline: 7 px on screen.
    t = worker.thickness_in_source(style, 1200, 800, 1920, 1080)
    assert t * min(1920 / 1200, 1080 / 800) == pytest.approx(7)


def test_verify_detects_offset_and_suggests_calibration(tmp_path):
    W, H = 1920, 1080
    T = 7.0
    exp = np.array([[200.0, 700.0], [600.0, 300.0], [1000.0, 760.0], [1700.0, 280.0]])
    # Fusion "draws" Y height-normalised while we sent width-normalised.
    cal = Calibration()
    f = to_fusion_xy(exp, W, H, cal)
    wrong = np.column_stack([(f[:, 0] + 0.5) * W, H / 2 - f[:, 1] * H])
    frames = {}
    for role, prog in (("start", 0.0), ("mid", 0.5), ("end", 1.0)):
        a = render_still(wrong, W, H, StrokeStyle(color=(1, 0, 0), thickness=T), prog)
        img = np.zeros((H, W, 4), np.uint8)
        img[:, :, 2] = 255
        img[:, :, 3] = np.round(a * 255).astype(np.uint8)
        p = str(tmp_path / f"{role}.png")
        cv2.imwrite(p, img)
        frames[role] = p
    res = verify(VerifyInput(frames, exp, W, H, T, (1, 0, 0), 0.5, cal, "native"))
    assert res["ok"] is False and res["checks"]["geometry"] is False
    sug = res["suggested_calibration"]
    assert sug["y_mode"] == "height"
    # With the suggestion, the same Fusion behaviour now aligns.
    cal2 = Calibration.from_dict(sug)
    f2 = to_fusion_xy(exp, W, H, cal2)
    drawn = np.column_stack([(f2[:, 0] + 0.5) * W, H / 2 - f2[:, 1] * H])
    assert np.abs(drawn - exp).max() < 0.6
