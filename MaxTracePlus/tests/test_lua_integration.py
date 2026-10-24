"""Offline integration tests of the Lua launcher against a mock Fusion.

These run the real MaxTrace+ Lua code (LuaJIT via lupa) and real worker
processes. Fusion itself is simulated by tests/lua/fusion_mock.lua plus the
render hooks below:

* the source node renders the synthetic chart;
* the native highlight layer renders the pasted PolylineStroke under a
  configurable "true" Fusion convention (Y normalisation, brush-size unit),
  evaluating the pasted BezierSpline write-on keys;
* the rendered fallback layer emulates a Loader reading the generated PNG
  sequence through its Clip/GlobalStart settings.

They prove the pipeline logic (capture -> build -> apply -> verify ->
calibrate/fallback, regenerate, remove, undo bracketing, connections). They
do NOT prove Fusion's own behaviour; that needs DaVinci Resolve (see
docs/TEST_REPORT.md).
"""

from __future__ import annotations

import json
import os
import shutil
import sys

import cv2
import numpy as np
import pytest

lupa = pytest.importorskip("lupa")
from lupa import luajit21  # noqa: E402

import synth  # noqa: E402
from maxtrace.render import StrokeStyle, render_still  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lua_list(t):
    out = []
    i = 1
    while t[i] is not None:
        out.append(t[i])
        i += 1
    return out


def bezier_eval(keys, frame):
    ks = sorted((float(k), v) for k, v in keys.items())
    if frame <= ks[0][0]:
        return float(ks[0][1][1])
    if frame >= ks[-1][0]:
        return float(ks[-1][1][1])
    for (t0, a), (t1, b) in zip(ks[:-1], ks[1:]):
        if t0 <= frame <= t1:
            p0 = (t0, float(a[1]))
            p3 = (t1, float(b[1]))
            rh = a["RH"]
            lh = b["LH"]
            p1 = (float(rh[1]), float(rh[2])) if rh is not None else (t0 + (t1 - t0) / 3, p0[1])
            p2 = (float(lh[1]), float(lh[2])) if lh is not None else (t0 + 2 * (t1 - t0) / 3, p3[1])
            lo, hi = 0.0, 1.0
            for _ in range(60):
                s = (lo + hi) / 2
                x = (1 - s) ** 3 * p0[0] + 3 * (1 - s) ** 2 * s * p1[0] + 3 * (1 - s) * s * s * p2[0] + s ** 3 * p3[0]
                if x > frame:
                    hi = s
                else:
                    lo = s
            s = (lo + hi) / 2
            return (1 - s) ** 3 * p0[1] + 3 * (1 - s) ** 2 * s * p1[1] + 3 * (1 - s) * s * s * p2[1] + s ** 3 * p3[1]
    return 0.0


class Harness:
    def __init__(self, tmp_path, chart, truth=None, capture_fails=False, source_regid="Paint", paint_input=True):
        self.tmp = str(tmp_path)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.home, "venv", "bin"))
        os.symlink(ROOT, os.path.join(self.home, "app"))
        os.symlink(sys.executable, os.path.join(self.home, "venv", "bin", "python3"))
        os.environ["MAXTRACE_HOME"] = self.home
        self.chart = chart
        self.chart_path = synth.save_chart(chart, os.path.join(self.tmp, "charts"))
        self.W, self.H = chart.size
        self.truth = truth or {"y_mode": "width", "size_factor": 1.0}
        self.capture_fails = capture_fails
        self.renders = []
        self.lua = luajit21.LuaRuntime(unpack_returned_tuples=True)
        self.mock = self.lua.execute(open(os.path.join(ROOT, "tests", "lua", "fusion_mock.lua")).read())
        self.mock.hooks.render = self.render_hook
        self.mock.hooks.image_info = self.image_info
        self.steps = []
        self.mock.hooks.driver = self.driver
        attrs = self.lua.table_from(
            {"COMPN_RenderStart": 0, "COMPN_RenderEnd": 119, "COMPN_GlobalStart": 0, "COMPN_GlobalEnd": 119, "COMPS_Name": "Graph Comp", "COMPN_CurrentTime": 0}
        )
        prefs = self.lua.table_from({"Comp.FrameFormat.Rate": 24, "Comp.FrameFormat.Width": 1920, "Comp.FrameFormat.Height": 1080})
        self.comp = self.mock.new_comp(self.lua.table_from({"attrs": attrs, "prefs": prefs, "current": 0}))
        add = self.comp._add
        self.media_in = add(self.comp, "MediaIn", "MediaIn1")
        self.paint = add(self.comp, source_regid, "Paint1")
        self.media_out = add(self.comp, "MediaOut", "MediaOut1")
        if paint_input:
            self.paint.Input.ConnectTo(self.paint.Input, self.media_in.Output)
        self.media_out.Input.ConnectTo(self.media_out.Input, self.paint.Output)
        self.comp.ActiveTool = self.paint
        ui = self.mock.new_ui()
        self.bmd = self.mock.make_bmd(ui)
        g = self.lua.globals()
        g.bmd = self.bmd
        self.fu = self.lua.table_from(
            {
                "UIManager": ui,
                "TIME_UNDEFINED": -1e9,
            }
        )
        self.lua.execute(
            "local fu, comp = ...; fu.GetCurrentComp = function() return comp end; "
            "fu.GetVersion = function() return { App = 'Resolve', 19, 1, 4 } end; "
            "fu.AskUser = function() return { Name = 'Test Preset' } end; fu.RequestFile = function() return nil end",
            self.fu,
            self.comp,
        )
        g.fu = self.fu
        g.comp = self.comp

    # -- hooks ------------------------------------------------------------

    def image_info(self, tool_name):
        if tool_name in ("MediaIn1", "Paint1"):
            return self.lua.table_from({"width": self.W, "height": self.H, "filename": self.chart_path})
        return None

    def render_hook(self, tool_name, frame, path):
        self.renders.append((tool_name, int(frame)))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if tool_name in ("MediaIn1", "Paint1"):
            if self.capture_fails:
                return  # Saver "renders" but writes nothing
            shutil.copyfile(self.chart_path, path) if self.chart_path.endswith(".png") else cv2.imwrite(path, cv2.imread(self.chart_path))
            return
        tool = self.comp._byname[tool_name]
        regid = tool._regid
        if regid == "Paint":
            self._render_native(tool, frame, path)
        elif regid == "Loader":
            self._render_loader(tool, frame, path)
        else:
            raise AssertionError(f"unexpected render of {tool_name}")

    def _render_native(self, paint, frame, path):
        stroke = paint.Paint._source._tool
        d = stroke._def
        inputs = d.Inputs
        pts = [(float(p.X), float(p.Y)) for p in lua_list(inputs.Polyline.Value.Points)]
        size = float(inputs["SoftBrush.Size"].Value)
        color = (float(inputs["PaintApplyColor.Red"].Value), float(inputs["PaintApplyColor.Green"].Value), float(inputs["PaintApplyColor.Blue"].Value))
        spline = stroke.WriteOnEnd._source._tool
        prog = bezier_eval(dict(spline._def.KeyFrames.items()), frame)
        W, H = self.W, self.H
        xs = np.array([(x + 0.5) * W for x, _ in pts])
        if self.truth["y_mode"] == "width":
            ys = np.array([H / 2.0 - y * W for _, y in pts])
        else:
            ys = np.array([H / 2.0 - y * H for _, y in pts])
        diam = size * W * self.truth["size_factor"]
        a = render_still(np.column_stack([xs, ys]), W, H, StrokeStyle(color=color, thickness=max(0.5, diam)), float(prog))
        img = np.zeros((H, W, 4), np.uint8)
        img[:, :, 0] = int(color[2] * 255)
        img[:, :, 1] = int(color[1] * 255)
        img[:, :, 2] = int(color[0] * 255)
        img[:, :, 3] = np.round(a * 255).astype(np.uint8)
        cv2.imwrite(path, img)

    def _render_loader(self, loader, frame, path):
        clip = loader._def.Clips[1]
        first = clip.Filename
        gs = int(clip.GlobalStart)
        n = int(clip.Length)
        idx = frame - gs
        img = np.zeros((self.H, self.W, 4), np.uint8)
        if 0 <= idx < n:
            base = os.path.basename(first)
            num = int(base.split("_")[-1].split(".")[0]) + idx
            f = os.path.join(os.path.dirname(first), base.rsplit("_", 1)[0] + "_%05d.png" % num)
            img = cv2.imread(f, cv2.IMREAD_UNCHANGED)
        cv2.imwrite(path, img)

    # -- driver -----------------------------------------------------------

    def driver(self, mock, disp):
        for step in self.steps:
            step(mock)
        mock.close()

    def run(self, *steps):
        self.steps = list(steps)
        factory = self.lua.execute("return dofile(...)", os.path.join(ROOT, "lua", "maxtrace", "main.lua"))
        ctx = self.lua.table_from({"root": ROOT, "comp": self.comp, "fu": self.fu, "bmd": self.bmd})
        factory(ctx).run()

    # -- inspection ---------------------------------------------------------

    def owned(self):
        return [t for t in lua_list(self.comp.GetToolList(self.comp, False)) if t._data["MaxTrace.Owner"] == "MaxTrace+"]

    def names(self):
        return sorted(t._name for t in lua_list(self.comp.GetToolList(self.comp, False)))

    def status(self):
        return self.mock['items'].Progress.Text

    def src_of(self, tool, inp):
        s = tool[inp]._source
        return None if s is None else s._tool._name


def generate(mock):
    mock.click("Generate")
    mock.pump(180)


def set_style(thickness=None, color=None, output_index=None):
    def step(mock):
        items = mock['items']
        if thickness is not None:
            items.Thickness.Value = int(thickness * 10)
        if color is not None:
            items.ColorHex.Text = color
        if output_index is not None:
            mock.select("OutputMode", output_index)

    return step


@pytest.fixture
def chart():
    return synth.case_labels_axes()


def _assert_wired(h):
    assert h.src_of(h.media_out, "Input") == "MaxTrace_Merge"
    assert h.src_of(h.comp._byname["MaxTrace_Merge"], "Background") == "Paint1"
    assert h.src_of(h.paint, "Input") == "MediaIn1"  # original chain untouched


def test_native_generate_verify_regenerate_remove(tmp_path, chart):
    h = Harness(tmp_path, chart)
    snapshots = {}

    def snap(name):
        def step(mock):
            snapshots[name] = (h.status(), h.names(), [t._name for t in h.owned()])

        return step

    h.run(generate, snap("first"), set_style(thickness=12, color="#FFD21F"), generate, snap("second"), lambda m: m.click("Remove"), snap("removed"))

    status, names, owned = snapshots["first"]
    assert status.startswith("Complete · native stroke · verified"), status
    assert {"MaxTrace_Canvas", "MaxTrace_Stroke", "MaxTrace_Merge"} <= set(owned)
    # Regenerate replaced the previous result instead of stacking a duplicate.
    status2, names2, owned2 = snapshots["second"]
    assert status2.startswith("Complete · native stroke · verified"), status2
    assert sorted(owned2) == sorted(owned)
    assert names2.count("MaxTrace_Merge") == 1
    assert not any(n.startswith("MaxTrace_") and n.rsplit("_", 1)[-1].isdigit() for n in names2), names2  # no renamed duplicates
    # Remove restored the original composition.
    status3, names3, owned3 = snapshots["removed"]
    assert owned3 == [] and "Removed" in status3
    assert names3 == ["MediaIn1", "MediaOut1", "Paint1"]
    assert h.src_of(h.media_out, "Input") == "Paint1"
    assert h.src_of(h.paint, "Input") == "MediaIn1"
    # Every undo group was closed.
    starts = [u for u in h.mock.undo.values() if str(u).startswith("start:")]
    ends = [u for u in h.mock.undo.values() if str(u).startswith("end:")]
    assert len(starts) == len(ends)
    # Calibration recorded as verified for this Resolve version.
    cal = json.load(open(os.path.join(h.home, "calibration.json")))
    assert cal["Resolve-19.1.4"]["verified"] is True


def test_native_self_calibrates_to_other_fusion_convention(tmp_path, chart):
    # Pretend Fusion normalises Y by height and SoftBrush.Size is a radius.
    h = Harness(tmp_path, chart, truth={"y_mode": "height", "size_factor": 2.0})
    out = {}

    def check(mock):
        out["status"] = h.status()
        _assert_wired(h)

    h.run(generate, check)
    assert out["status"].startswith("Complete · native stroke · verified"), out["status"]
    cal = json.load(open(os.path.join(h.home, "calibration.json")))["Resolve-19.1.4"]
    assert cal["y_mode"] == "height"
    assert cal["size_scale"] == pytest.approx(0.5, rel=0.08)
    # Later generations start from the stored calibration: one verification pass.
    h.renders.clear()
    h2 = h
    h2.run(generate)
    layer_renders = [r for r in h.renders if r[0] == "MaxTrace_Stroke"]
    assert len(layer_renders) <= 4


def test_native_failure_falls_back_to_rendered(tmp_path, chart):
    # A Fusion that draws strokes 3x too wide in X cannot be fixed by the
    # supported calibration -> automatic fallback to the rendered sequence.
    class Weird(Harness):
        def _render_native(self, paint, frame, path):
            img = np.zeros((self.H, self.W, 4), np.uint8)
            cv2.imwrite(path, img)  # renders nothing at all

    h = Weird(tmp_path, chart)
    out = {}

    def check(mock):
        out["status"] = h.status()
        out["owned"] = sorted(t._name for t in h.owned())
        _assert_wired(h)

    h.run(generate, check)
    assert out["status"].startswith("Complete · rendered · verified"), out["status"]
    assert "Native stroke not used" in out["status"]
    assert "MaxTrace_Render" in out["owned"] and "MaxTrace_Stroke" not in out["owned"]


def test_forced_rendered_mode_and_loader_timing(tmp_path, chart):
    h = Harness(tmp_path, chart)
    out = {}

    def check(mock):
        out["status"] = h.status()
        ldr = h.comp._byname["MaxTrace_Render"]
        clip = ldr._def.Clips[1]
        out["gs"] = int(clip.GlobalStart)
        out["len"] = int(clip.Length)
        out["pm"] = ldr._def.Inputs["Clip1.PNGFormat.PostMultiply"].Value
        _assert_wired(h)

    h.run(set_style(output_index=2), generate, check)
    assert out["status"].startswith("Complete · rendered · verified"), out["status"]
    assert out["gs"] == 0 and out["len"] == 120 and out["pm"] == 1


def test_capture_failure_uses_media_file_and_rendered_output(tmp_path, chart):
    h = Harness(tmp_path, chart, capture_fails=True)
    out = {}

    def check(mock):
        out["status"] = h.status()

    h.run(generate, check)
    assert out["status"].startswith("Complete · rendered"), out["status"]
    assert "original media file" in out["status"]


def test_paint_without_input_reports_error(tmp_path, chart):
    h = Harness(tmp_path, chart, paint_input=False)
    out = {}

    def check(mock):
        out["status"] = h.status()
        out["owned"] = h.owned()

    h.run(generate, check)
    assert "has no image connected" in out["status"]
    assert out["owned"] == []


def test_cancel_leaves_comp_untouched(tmp_path, chart):
    h = Harness(tmp_path, chart)
    out = {}

    def cancel(mock):
        mock.click("Generate")
        mock.click("Generate")  # second click = Cancel
        mock.pump(120)
        out["status"] = h.status()
        out["owned"] = h.owned()

    h.run(cancel)
    assert out["owned"] == []
    assert out["status"] in ("Cancelled", "Cancelling…") or out["status"].startswith("Complete")


def test_preview_detects_without_modifying_comp(tmp_path):
    h = Harness(tmp_path, synth.case_multi_lines())
    out = {}

    def preview(mock):
        mock.click("Detect")
        mock.pump(120)
        out["status"] = h.status()
        out["lines"] = lua_list(mock['items'].LineChoice._items)
        out["owned"] = h.owned()
        out["preview"] = mock['items'].Preview.Text

    h.run(preview)
    assert out["owned"] == []
    assert len(out["lines"]) >= 4  # "Best match" + 3 detected lines
    assert "<img" in out["preview"]
    assert out["status"].startswith("Line #")


def test_settings_persist_across_sessions(tmp_path, chart):
    h = Harness(tmp_path, chart)

    def change(mock):
        items = mock["items"]
        items.Thickness.Value = 125
        items.Duration.Value = 40
        mock.select("Motion", 1)
        items.ColorHex.Text = "#22D3EE"
        mock.win.On.ColorHex.EditingFinished({})

    h.run(change)
    saved = json.load(open(os.path.join(h.home, "settings.json")))
    assert saved["style"]["thickness"] == pytest.approx(12.5)
    assert saved["style"]["color"] == "#22D3EE"
    assert saved["timing"]["duration"] == pytest.approx(4.0)
    assert saved["timing"]["motion"] == "smooth"
    seen = {}

    def inspect(mock):
        items = mock["items"]
        seen.update(t=items.Thickness.Value, d=items.Duration.Value, m=items.Motion.CurrentIndex, c=items.ColorHex.Text, p=items.Preset.CurrentIndex)

    h.run(inspect)  # second session: startup must not overwrite the saved values
    assert seen["t"] == 125 and seen["d"] == 40 and seen["m"] == 1 and seen["c"] == "#22D3EE"
    again = json.load(open(os.path.join(h.home, "settings.json")))
    assert again["style"]["thickness"] == pytest.approx(12.5) and again["timing"]["motion"] == "smooth"
