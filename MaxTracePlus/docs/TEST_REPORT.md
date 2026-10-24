# MaxTrace+ test report

Environment: Linux x86_64 cloud container, Python 3.13, NumPy 2.5,
OpenCV 5.0 (headless), LuaJIT 2.1 (through `lupa`). **DaVinci Resolve was not
available**, so every result below is an offline test. No live Resolve
test is reported as passed.

Command: `python3 -m pytest tests -q`. Result: **62 passed, 0 failed** (about 2.5 min).

## Phase A: computer vision (17 synthetic charts with exact ground truth)

Charts are drawn with OpenCV's own antialiased renderer (independent of
MaxTrace's renderer) and include axes, grids, titles, tick labels, legends
with swatches in the line colour, annotations, JPEG compression,
occlusions, dark themes and several resolutions. Errors are in source
pixels. *Uncovered* is the share of the source line's ink still visible
under the default 7 px highlight.

| Chart | Size | Mean | p95 | Worst | Start/End | Uncovered |
|---|---|---|---|---|---|---|
| 01 red zigzag, white | 1920x1080 | 0.09 | 0.23 | 1.6 | 0.5 / 0.5 | 0.01% |
| 02 blue line, grey grid | 1920x1080 | 0.23 | 0.85 | 2.7 | 0.8 / 0.9 | 0.27% |
| 03 thin 1 px line, JPEG q55 | 1920x1080 | 0.13 | 0.40 | 6.2* | 0.8 / 0.8 | 0.10% |
| 04 thick (13 px) antialiased | 1920x1080 | 0.07 | 0.20 | 0.4 | 0.2 / 0.3 | 0.00% |
| 05 ninety sharp peaks | 1920x1080 | 0.03 | 0.08 | 1.8 | 0.7 / 0.7 | 0.01% |
| 06 labels, axes, legend, annotation | 1920x1080 | 0.16 | 0.54 | 1.4 | 0.2 / 0.3 | 0.04% |
| 07 three lines, blue picked | 1920x1080 | 0.27 | 0.95 | 13.2** | 0.8 / 0.7 | 1.32%** |
| 08 line interrupted by label box | 1920x1080 | 0.25 | 0.91 | 11.6** | 0.5 / 0.5 | 1.38%** |
| 09 300-point financial walk | 1920x1080 | 0.53 | 1.58 | 6.9 | 1.2 / 1.2 | 1.94% |
| 10 4K zigzag | 3840x2160 | 0.03 | 0.09 | 1.0 | 0.9 / 1.0 | 0.00% |
| 11 dark theme, orange | 1920x1080 | 0.32 | 1.05 | 5.3 | 1.2 / 1.1 | 0.22% |
| 12 already highlighted (red then blue) | 1920x1080 | 0.23 | 0.84 | 2.2 | 0.1 / 0.4 | 0.26% |
| 13 black line, black axes | 1920x1080 | 0.20 | 0.67 | 1.7 | 0.4 / 0.7 | 0.13% |
| 14 smooth curve | 1920x1080 | 0.13 | 0.38 | 0.6 | 0.6 / 0.6 | 0.00% |
| 15 yellow, 1440p | 2560x1440 | 0.06 | 0.16 | 1.7 | 0.5 / 1.1 | 0.00% |
| 16 1200x800 screenshot, JPEG | 1200x800 | 0.18 | 0.67 | 1.8 | 0.7 / 0.9 | 0.09% |
| 17 loop (not x-monotonic) | 1920x1080 | 0.23 | 0.55 | 1.8 | 0.8 / 1.0 | 0.17% |

\* A thin JPEG line touching a sharp turn; the worst point is one sample.
\*\* At spans where the line is genuinely hidden (crossed by other series, or
under the label box) the path is bridged straight. MaxTrace+ does not
invent geometry it cannot see, and it reports these spans as ambiguous regions.

Chart 09 draws a 6 px line through 300 points (one every 5.6 px), so some
pairs of corners lie closer together than two line widths. Even then, 98%
of its ink is covered by a 7.5 px highlight.

Other Phase A tests: every line in a three-line chart is offered as a
candidate (each matches its series at < 0.7 px); choosing a candidate by
colour is stable; a line that changes colour part-way (an existing
highlight) is joined and flagged; a manual region restricts detection; a
blank image or a picked background colour gives a clear reason instead of a
fake line; the same chart at 1x and 2x traces to the same normalised path.

Speed on this 4-core container: 0.4 to 2.5 s for 1080p charts and about 7 s
at 4K. Results are cached per image, so changing settings and generating
again does not repeat the analysis.

## Phase B: animation (rendered output)

All passed: frame count equals duration x fps (2.5 s at 24 fps = 60 frames,
at 29.97 fps = 75); frames up to and including the start frame are empty
(this caught and fixed a bug where Smooth easing returned 5.6e-37 instead of
0 at the first frame); intermediate frames are partial and grow
monotonically (no erasing or flicker); the final frame covers the whole path
(400 samples, all with alpha > 0.95) and is held afterwards; the reveal runs
from the first point to the last; in Linear mode revealed area grows in
equal steps along a path mixing one long segment with 70 short ones
(coefficient of variation < 0.12), which confirms arc-length timing rather
than per-point timing; trace range 0-58% and 20-60% trim to exactly that
fraction of the length and lie on the original geometry; colour and opacity
are exact, with straight (unpremultiplied) PNG colour and Loader post-multiply;
thick strokes are antialiased and have round caps; halo and glow stay subtle
(< 35% alpha outside the stroke).

## Phase C: Fusion integration, offline with a simulated Fusion

`tests/test_lua_integration.py` runs the **real Lua launcher code** on
LuaJIT against `tests/lua/fusion_mock.lua`. The mock is a Fusion stand-in
with tools, inputs/outputs, connections, CustomData, Paste of setting text
using Fusion's constructor syntax, Delete, undo bracketing, flow positions,
Saver rendering and a scriptable UIManager. The **real worker processes**
run alongside it. Render hooks draw the source chart, simulate Fusion
drawing the pasted PolylineStroke (evaluating the pasted BezierSpline
write-on keys), and emulate a Loader reading the generated sequence through
its Clip/GlobalStart settings.

| Scenario | Result |
|---|---|
| Generate native highlight, verify, regenerate with new colour/thickness, remove | passed: verified native stroke; regeneration replaces, no duplicate or renamed nodes; remove restores `MediaOut1 <- Paint1`, Paint1's input untouched; every undo group closed |
| Fusion using the other coordinate/brush convention | passed: first verification fails, calibration switches to height-normalised Y and size x0.5, the stroke is regenerated, verifies and is stored for later runs |
| Native stroke renders nothing | passed: automatic fallback to the rendered sequence, with the reason shown |
| Rendered mode forced | passed: Loader GlobalStart, Length and PostMultiply correct; timing verified |
| Saver capture fails | passed: falls back to the original media file, labelled as such, rendered output used |
| Paint node without input | passed: clear error, nothing created |
| Cancel during generation | passed: composition unchanged |
| Preview detection | passed: candidate list and preview filled, composition unchanged |
| Settings across sessions | passed: changed thickness, colour, duration and motion are saved and restored, and the startup event cascade (the mock fires change events on programmatic updates, like Qt) does not overwrite them |

Unit tests also cover setting generation (parsed back with Fusion's
constructor syntax), coordinate round trips, Lua JSON, every worker job
including its error codes (unsupported fps, bad range, bad colour, missing
image, blank image), same-colour and already-highlighted warnings,
resolution-aware thickness, and the calibration suggestion.

The installer and uninstaller were run in a sandbox (with `MAXTRACE_HOME`
and `MAXTRACE_SCRIPTS_ROOT` overrides):
- venv creation, engine self-test and smoke-test trace passed;
- the installed launcher completed a native generation against the mock, and opened with a clear message when no composition was open;
- the menu script is installed into `Scripts/Comp` and `Scripts/Utility` before the Python step; with no usable Python the private Python 3.12 was downloaded and checksum-verified, and when the engine step failed the menu scripts were still in place; `--check` reported every location correctly;
- uninstall kept user data, and `--purge` removed it;
- an unrelated `MaxTrace+.lua` in the Scripts folder is refused and never overwritten.

## Not performed (requires DaVinci Resolve on your Mac)

* Live Phase C/D in Resolve: opening the panel in Resolve Studio, Saver
  capture through `comp:Render`, Paste, the real PolylineStroke render and
  write-on, Resolve undo, and timeline playback.
* Whether Fusion's write-on parameterisation is exactly arc-length. Paths
  are resampled to near-uniform point spacing, so either parameterisation
  gives a near-constant speed. The mid-frame check measures it on every run.
* Real-world chart screenshots (only synthetic charts were tested).

The first generation in Resolve runs the verification described in
FUSION_API_NOTES.md and reports the outcome in the panel ("verified", or the
reason for using rendered output). The Advanced section's Diagnostics box
shows the measurements.
