# Fusion API verification notes

MaxTrace+ was developed in a cloud Linux container **without DaVinci Resolve**.
The local Resolve install, its bundled scripting README and a live Fusion
could not be inspected there, and the Blackmagic forums/documentation hosts
were not reachable. Every Fusion call and serialisation used by MaxTrace+
was therefore taken from **real Fusion/Resolve compositions, macros and
scripts** in the WeSuckLess *Reactor* package repository
(`gitlab.com/WeSuckLess/Reactor`, ~1,350 `.comp`/`.setting` files and
~450 comp/tool scripts, many written for Resolve). Nothing below is invented
from memory alone. The two quantities no sample could settle are handled by
measuring the real result inside Resolve (see *Runtime verification*).

## Verified from samples

| Need | Verified form | Example source in Reactor |
|---|---|---|
| Paint stroke chain | `PaintX.Inputs.Paint = Input { SourceOp = "<last stroke>", Source = "Out" }`; each stroke's `Paint` input points at the previous stroke's `Out`; the first stroke has none | `Atoms/com.AndrewHazelden.KartaVR.Comps/.../Ricoh Theta S Stitch.comp` (`PaintFront`, `PolylineStroke1`, `CloneMultistroke*`) |
| PolylineStroke block | `PolylineStroke { Points = {}, IsThreaded = false, Brushes = { "SoftBrush" }, ApplyModes = { ... }, Inputs = { BrushControls, ["SoftBrush.Size"], ApplyMode = FuID{...}, Polyline = Input { Value = Polyline { ... } } } }` | same file |
| Colour / softness inputs | `["PaintApplyColor.Red/Green/Blue"]`, `["SoftBrush.Softness"]`, `StrokeControls` | `Ricoh Theta S Stitch.comp`, `Krokodove/Mirror/Mirror_A_001.comp` |
| Write-on animation | `WriteOnEnd = Input { SourceOp = "Stroke1WriteOnEnd", Source = "Value" }` + `Stroke1WriteOnEnd = BezierSpline { KeyFrames = { [30] = { 0, RH = { 46.67, 0 } }, [80] = { 1, LH = { 42.8, 0.998 } } } }` (absolute time/value handles) | `Atoms/com.KomkomDoorn.Krokodove.Showcase/Comps/Krokodove/Mirror/Mirror_A_001.comp` |
| Linear keyframes | `[t] = { v, RH = {..}, Flags = { Linear = true } }` (most common keyframe form across all samples) | hundreds of comps |
| Polyline points | `{ Linear = true, X = .., Y = .., LX = .., LY = .., RX = .., RY = .. }`, handle offsets relative to the point (= neighbour delta / 3 for linear segments), open polylines omit `Closed` | `Mirror_A_001.comp` (`Polygon1`, `Stroke1`) |
| Points relative to `Center` | `Stroke1` has `Center = { 0.1357, 0.518 }` with points around +-0.1 | `Mirror_A_001.comp` |
| Transparent Background | `TopLeftAlpha = Input { Value = 0 }`, `UseFrameFormatSettings`, `Width`, `Height` | 100+ settings |
| Merge / Blur / SoftGlow inputs | `Background`, `Foreground`, `Blend`, `PerformDepthMerge`; `XBlurSize`; `Gain`, `Threshold`, `XGlowSize` | input-frequency survey of all samples |
| Saver for a still | `Clip = Input { Value = Clip { Filename = "...png", FormatID = "PNGFormat", Saving = true, ... } }`, `OutputFormat = FuID { "PNGFormat" }`, `CreateDir = 1` | `KartaVR.Comps/.../CubicFaces2Equirectangular.comp` |
| Loader for a PNG sequence | `Clips = { Clip { ID = "Clip1", Filename, FormatID = "PNGFormat", StartFrame, Length, LengthSetManually, TrimIn/TrimOut, ExtendFirst/ExtendLast, GlobalStart/GlobalEnd } }`, straight PNG alpha via `["Clip1.PNGFormat.PostMultiply"] = Input { Value = 1 }` | `Vonk Mission Control Resolve v001.comp`, KartaVR comps |
| CustomData on tools | `CustomData = { Path = { Map = {...} } }`; read/write with dotted keys `tool:GetData("A.B")` / `SetData` | Vonk comps; `FrameRanger`, `AnimUtility` scripts |
| Paste generated nodes | `comp:Paste(bmd.readstring(text))`, `comp:Paste(bmd.readfile(path))` | 20+ scripts |
| Render one node from Resolve's Fusion page | `comp:Render({ Tool = tool, FrameRange = "t..t", Wait = true })` ("output content in Resolve's Fusion Page directly to disk using ... Saver") | `Atoms/com.AndrewHazelden.ResolveEssentials/Scripts/Comp/Resolve Essentials/Render Current Frame.lua` |
| Connections | `out:GetConnectedInputs()`, `inp:ConnectTo(out)`, `inp:GetConnectedOutput()`, `out:GetTool()`, `tool:FindMainInput(1)`, `tool:FindMainOutput(1)`, `inp:GetAttrs().INPS_ID`, `out:GetAttrs().OUTS_DataType` | Loader/pipe scripts |
| Node graph positions | `comp.CurrentFrame.FlowView:GetPos(tool)` / `:SetPos(tool, x+1, y)` (grid units) | many scripts |
| Comp timing/format | `comp:GetAttrs().COMPN_RenderStart/End`, `COMPN_GlobalStart/End`, `comp.CurrentTime`, `comp:GetPrefs("Comp.FrameFormat.Rate")`, `"Comp.FrameFormat"` | many scripts |
| Image size / media path of a node | `tool.Output[comp.CurrentTime].Metadata.Filename`; `img = loader.Output:GetValue(); img.Width/Height` | KartaVR "Send Media" scripts |
| Viewer snapshot | `comp:GetPreviewList().LeftView.View.CurrentViewer:SaveFile(path)`, `LeftView:ViewOn(tool, 1)` | 22 scripts |
| UIManager | `fu.UIManager`, `bmd.UIDispatcher`, `disp:AddWindow{...}`, `win:GetItems()`, `ui:FindWindow(id)`, widgets Label/Button/ComboBox/Slider/LineEdit/CheckBox/SpinBox/TextEdit, `itm.X.Visible/Enabled/Text/Value/CurrentIndex/Checked/PlainText`, events `Clicked`, `CurrentIndexChanged`, `ValueChanged`, `EditingFinished`, `Close`; timers `ui:Timer{ID, Interval}` + `disp.On.Timeout(ev)` with `ev.who`; HTML `<img src>` in labels | Reactor UI scripts (Propagate, Toolbar16, ...) |
| Misc | `bmd.readdir(pattern)`, `bmd.fileexists`, `bmd.createdir`, `bmd.createuuid`, `bmd.openfileexternal`, `fu:RequestFile(dir, file, opts)`, `comp:AskUser(title, { {"ID", Name=..., "Text", ...} })`, `app:GetVersion()` (`[1]`, `.App`) | many scripts |
| Script menu location | user Fusion scripts in `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/<Utility or Comp>`; `Utility` scripts are listed under Workspace > Scripts on every page, `Comp` scripts only on the Fusion page. MaxTrace+ installs the same launcher into both (Comp is the location used by ~700 Reactor scripts, including names with `+`) and finds the composition with `fu:GetCurrentComp()` | Resolve scripting README (documented location) |

## Not determinable from samples, handled at runtime

1. **Vertical scale of polyline coordinates.** The evidence points to
   Fusion's resolution-independent convention: X relative to image width,
   Y also relative to *width* (range +-0.5*H/W). Fusion's own Fuse code says
   "vertically, 1.0 isn't the image height but equals the image's width",
   and a hand-drawn polygon in a 1920x1080 comp reaches Y = 0.2856, just past
   0.28125. MaxTrace+ starts with that convention.
2. **Unit of `SoftBrush.Size`.** Taken as diameter / image width to start.

### Runtime verification and self-calibration

After every native generation (when the frame can be rendered), MaxTrace+
renders the highlight layer through a temporary Saver at the frame before
the start, the start, the middle and the end. `engine/maxtrace/verify.py`
then measures:

* geometry, by comparing the rendered stroke's centre line with the path
  that was sent; an axis-aligned affine fit detects a Y convention mismatch
  (scale H/W or W/H), other scale errors and offsets;
* the stroke width (alpha area / length), which corrects the brush size;
* timing: empty before and at the first frame, the expected arc-length
  fraction at the middle frame, and complete at the end.

When a check fails, a corrected calibration is computed. The highlight is
regenerated and verified again (up to 3 passes), and the calibration is
stored per Resolve version in `calibration.json`. If the native stroke still
does not verify, Auto mode replaces it with the rendered PNG sequence, which
MaxTrace+ draws itself, and the reason is shown. The offline integration
tests simulate a Fusion that uses the *other* convention (height-normalised
Y, size as radius) and confirm that the loop converges to it.

## Native output structure

```
MediaIn1 ─▶ Paint1 ─┬──────────────────────────▶ MaxTrace_Merge ─▶ (previous consumers, e.g. MediaOut1)
                    │                                 ▲ Foreground
MaxTrace_Canvas ─▶ MaxTrace_Stroke ─[▶ MaxTrace_Soft/SoftMix]─[▶ MaxTrace_Glow]
 (transparent bg)   (Paint + editable PolylineStroke "MaxTrace_Path",
                     WriteOnEnd ← BezierSpline "MaxTrace_PathWriteOn")
```

* The user's Paint1 is never modified. Its strokes stay underneath, and it
  is the frame *entering* Paint1 that is analysed, so upstream Transform or
  Resize nodes are already included.
* `MaxTrace_Merge.Blend` is driven by a step spline: 0 up to the first
  animation frame, then the chosen opacity. Nothing can show before the
  reveal starts.
* Every created tool carries `CustomData.MaxTrace = { Owner, GenID, Role }`.
  Regenerating or removing touches only tools whose Owner is `MaxTrace+`
  and restores the previous downstream connections.
