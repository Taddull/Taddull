-- MaxTrace+ panel layout (Fusion UIManager).

return function(util)
	local U = {}

	U.WINDOW_ID = "MaxTracePlusWin"
	U.WIDTH = 440

	local C = {
		bg = "#1E1F22",
		panel = "#26272B",
		field = "#2A2B30",
		border = "#393B41",
		text = "#D9DBDF",
		dim = "#8D9097",
		accent = "#E0393F",
		accent_hover = "#EA4B51",
	}
	U.COLORS = C

	U.CSS = table.concat({
		"QWidget { background-color: " .. C.bg .. "; color: " .. C.text .. "; font-size: 12px; }",
		"QLabel { background: transparent; }",
		"QPushButton { background-color: " .. C.panel .. "; border: 1px solid " .. C.border .. "; border-radius: 4px; padding: 4px 10px; color: " .. C.text .. "; }",
		"QPushButton:hover { background-color: #303137; }",
		"QPushButton:pressed { background-color: #24252A; }",
		"QPushButton:disabled { color: #5F6269; border-color: #2E3035; }",
		"QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox { background-color: " .. C.field .. "; border: 1px solid " .. C.border .. "; border-radius: 3px; padding: 3px 6px; selection-background-color: #3B5BDB; }",
		"QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled { color: #5F6269; }",
		"QComboBox QAbstractItemView { background-color: " .. C.field .. "; border: 1px solid " .. C.border .. "; }",
		"QSlider::groove:horizontal { height: 4px; background: #3A3C42; border-radius: 2px; }",
		"QSlider::sub-page:horizontal { background: #9AA0A9; border-radius: 2px; }",
		"QSlider::handle:horizontal { width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; background: #E8E9EC; }",
		"QSlider::handle:horizontal:disabled { background: #5F6269; }",
		"QCheckBox { spacing: 6px; background: transparent; }",
		"QTextEdit { background-color: " .. C.panel .. "; border: 1px solid " .. C.border .. "; border-radius: 3px; font-family: Menlo, monospace; font-size: 10px; }",
	}, "\n")

	U.PRIMARY_CSS = "QPushButton { background-color: " .. C.accent .. "; border: none; border-radius: 5px; color: #FFFFFF; font-size: 13px; font-weight: 600; padding: 9px 12px; }"
		.. " QPushButton:hover { background-color: " .. C.accent_hover .. "; }"
		.. " QPushButton:disabled { background-color: #4A2B2D; color: #A9A9A9; }"
	U.CANCEL_CSS = "QPushButton { background-color: #3A3C42; border: none; border-radius: 5px; color: #FFFFFF; font-size: 13px; font-weight: 600; padding: 9px 12px; }"
		.. " QPushButton:hover { background-color: #45474E; }"

	local SECTION_CSS = "QLabel { color: " .. C.dim .. "; font-size: 10px; font-weight: 600; letter-spacing: 1px; padding-top: 8px; }"
	local RULE_CSS = "QLabel { background-color: #2E3035; min-height: 1px; max-height: 1px; }"
	local LABEL_W = 86

	function U.swatch_css(hex, selected)
		return string.format(
			"QPushButton { background-color: %s; border: %s; border-radius: 9px; min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px; padding: 0px; }",
			hex,
			selected and "2px solid #FFFFFF" or "1px solid #4A4C52"
		)
	end

	function U.dot_css(color)
		return "QLabel { color: " .. color .. "; font-size: 13px; }"
	end

	-- IDs of widgets that belong to the collapsible Advanced section.
	U.ADVANCED = {
		"AdvRule", "AdvSensLabel", "Sensitivity", "SensitivityVal", "AdvGapLabel", "Gap", "GapVal",
		"AdvSimpLabel", "Simplify", "SimplifyVal", "AdvRegionLabel", "RegionMode", "Region",
		"AdvOutLabel", "OutputMode", "Verify", "Diagnostics", "AdvBezLabel", "CustomBezier",
		"ImportImage", "CleanCache", "OpenLogs", "DiagText",
	}

	-- Controls disabled while a job is running.
	U.INTERACTIVE = {
		"UseSelected", "TraceMode", "PickHex", "LineChoice", "Detect", "Preset", "SavePreset",
		"SwRed", "SwYellow", "SwCyan", "SwGreen", "SwWhite", "ColorHex", "Thickness", "Softness",
		"Halo", "Opacity", "Glow", "Duration", "Motion", "StartMode", "StartFrame", "RangeMode",
		"RangeStart", "RangeEnd", "Remove", "Sensitivity", "Gap", "Simplify", "RegionMode", "Region",
		"OutputMode", "Verify", "CustomBezier", "ImportImage", "CleanCache",
	}

	function U.build(ui, disp, geometry)
		local function label(text, w)
			return ui:Label({ Text = text, MinimumSize = { w or LABEL_W, 0 }, MaximumSize = { w or LABEL_W, 40 }, StyleSheet = "QLabel { color: " .. C.dim .. "; }" })
		end
		local function value_label(id, text)
			return ui:Label({ ID = id, Text = text, MinimumSize = { 54, 0 }, MaximumSize = { 54, 40 }, Alignment = { AlignRight = true, AlignVCenter = true } })
		end
		local function section(text)
			return ui:Label({ Text = text, StyleSheet = SECTION_CSS, Weight = 0 })
		end
		local function rule(id)
			return ui:Label({ ID = id, Text = "", StyleSheet = RULE_CSS, Weight = 0 })
		end
		local function slider(id, min, max, value)
			return ui:Slider({ ID = id, Minimum = min, Maximum = max, Value = value, Events = { ValueChanged = true, SliderReleased = true } })
		end
		local function swatch(id, hex)
			return ui:Button({ ID = id, Text = "", StyleSheet = U.swatch_css(hex, false), ToolTip = hex })
		end

		local win = disp:AddWindow({
			ID = U.WINDOW_ID,
			WindowTitle = "MaxTrace+",
			Geometry = geometry or { 120, 120, U.WIDTH, 780 },
			StyleSheet = U.CSS,
			Spacing = 6,
			Margin = 14,

			ui:VGroup({
				ID = "Root",
				Spacing = 6,
				-- Header
				ui:HGroup({
					Weight = 0,
					ui:Label({ Text = "MaxTrace+", StyleSheet = "QLabel { font-size: 17px; font-weight: 600; color: #F2F3F5; }" }),
					ui:HGap(0, 1),
					ui:Label({ ID = "StatusDot", Text = "●", StyleSheet = U.dot_css("#6B6E75"), MaximumSize = { 16, 30 } }),
					ui:Label({ ID = "HeaderStatus", Text = "Checking…", StyleSheet = "QLabel { color: " .. C.dim .. "; }", Alignment = { AlignRight = true, AlignVCenter = true } }),
				}),
				rule(),

				-- Source
				section("SOURCE"),
				ui:HGroup({ Weight = 0, label("Source"), ui:Label({ ID = "SourceLabel", Text = "—", WordWrap = true }), ui:Button({ ID = "UseSelected", Text = "Use Selected", MaximumSize = { 100, 28 } }) }),
				ui:HGroup({
					Weight = 0,
					label("Trace"),
					ui:ComboBox({ ID = "TraceMode" }),
					ui:LineEdit({ ID = "PickHex", Text = "#E02020", PlaceholderText = "#RRGGBB", MaximumSize = { 86, 28 }, ToolTip = "Colour of the graph line to trace" }),
				}),
				ui:HGroup({ Weight = 0, label("Line"), ui:ComboBox({ ID = "LineChoice", ToolTip = "Detected graph lines - choose which one to trace" }), ui:Button({ ID = "Detect", Text = "Preview", MaximumSize = { 76, 28 }, ToolTip = "Detect the line and update the preview without changing the composition" }) }),
				ui:Label({ ID = "Preview", Text = "", Alignment = { AlignHCenter = true, AlignVCenter = true }, MinimumSize = { 400, 120 }, StyleSheet = "QLabel { background-color: #17181A; border: 1px solid #2E3035; border-radius: 4px; color: #6B6E75; }" }),

				-- Style
				section("STYLE"),
				ui:HGroup({ Weight = 0, label("Preset"), ui:ComboBox({ ID = "Preset" }), ui:Button({ ID = "SavePreset", Text = "Save…", MaximumSize = { 64, 28 }, ToolTip = "Save the current style as a preset" }) }),
				ui:HGroup({
					Weight = 0,
					label("Colour"),
					swatch("SwRed", "#FF2020"),
					swatch("SwYellow", "#FFD21F"),
					swatch("SwCyan", "#22D3EE"),
					swatch("SwGreen", "#35D06E"),
					swatch("SwWhite", "#FFFFFF"),
					ui:HGap(6, 0),
					ui:LineEdit({ ID = "ColorHex", Text = "#FF2020", MaximumSize = { 86, 28 }, ToolTip = "Custom highlight colour" }),
				}),
				ui:HGroup({ Weight = 0, label("Thickness"), slider("Thickness", 10, 400, 70), value_label("ThicknessVal", "7.0 px") }),
				ui:HGroup({ Weight = 0, label("Softness"), slider("Softness", 0, 100, 12), value_label("SoftnessVal", "12%") }),
				ui:HGroup({ Weight = 0, label("Soft halo"), slider("Halo", 0, 100, 0), value_label("HaloVal", "Off") }),
				ui:HGroup({ Weight = 0, label("Opacity"), slider("Opacity", 5, 100, 100), value_label("OpacityVal", "100%") }),
				ui:HGroup({ Weight = 0, label(""), ui:CheckBox({ ID = "Glow", Text = "Subtle glow", Checked = false }) }),

				-- Animation
				section("ANIMATION"),
				ui:HGroup({ Weight = 0, label("Duration"), slider("Duration", 5, 100, 25), value_label("DurationVal", "2.5 s") }),
				ui:HGroup({ Weight = 0, label("Motion"), ui:ComboBox({ ID = "Motion" }) }),
				ui:HGroup({ Weight = 0, label("Start"), ui:ComboBox({ ID = "StartMode" }), ui:SpinBox({ ID = "StartFrame", Minimum = -100000, Maximum = 1000000, Value = 0, MaximumSize = { 90, 28 } }) }),
				ui:HGroup({
					Weight = 0,
					label("Trace range"),
					ui:ComboBox({ ID = "RangeMode" }),
					ui:SpinBox({ ID = "RangeStart", Minimum = 0, Maximum = 100, Value = 0, Suffix = " %", MaximumSize = { 74, 28 } }),
					ui:SpinBox({ ID = "RangeEnd", Minimum = 0, Maximum = 100, Value = 100, Suffix = " %", MaximumSize = { 74, 28 } }),
				}),

				-- Action
				ui:VGap(6, 0),
				ui:Button({ ID = "Generate", Text = "Generate Highlight", StyleSheet = U.PRIMARY_CSS, MinimumSize = { 0, 38 } }),
				ui:Label({ ID = "Progress", Text = "Ready", Alignment = { AlignHCenter = true }, WordWrap = true, StyleSheet = "QLabel { color: " .. C.dim .. "; }" }),
				ui:HGroup({
					Weight = 0,
					ui:Button({ ID = "AdvToggle", Text = "▸  Advanced", Flat = true, StyleSheet = "QPushButton { border: none; background: transparent; color: " .. C.dim .. "; text-align: left; padding: 2px 0px; }" }),
					ui:HGap(0, 1),
					ui:Button({ ID = "Remove", Text = "Remove Highlight", ToolTip = "Remove MaxTrace+ nodes for this source and restore the original connections" }),
				}),

				-- Advanced (collapsed by default)
				rule("AdvRule"),
				ui:HGroup({ Weight = 0, ui:Label({ ID = "AdvSensLabel", Text = "Sensitivity", MinimumSize = { LABEL_W, 0 }, MaximumSize = { LABEL_W, 40 }, StyleSheet = "QLabel { color: " .. C.dim .. "; }" }), slider("Sensitivity", 0, 100, 50), value_label("SensitivityVal", "50%") }),
				ui:HGroup({ Weight = 0, ui:Label({ ID = "AdvGapLabel", Text = "Gap bridging", MinimumSize = { LABEL_W, 0 }, MaximumSize = { LABEL_W, 40 }, StyleSheet = "QLabel { color: " .. C.dim .. "; }" }), slider("Gap", 0, 100, 50), value_label("GapVal", "50%") }),
				ui:HGroup({ Weight = 0, ui:Label({ ID = "AdvSimpLabel", Text = "Simplify", MinimumSize = { LABEL_W, 0 }, MaximumSize = { LABEL_W, 40 }, StyleSheet = "QLabel { color: " .. C.dim .. "; }" }), slider("Simplify", 1, 50, 6), value_label("SimplifyVal", "0.6 px") }),
				ui:HGroup({
					Weight = 0,
					ui:Label({ ID = "AdvRegionLabel", Text = "Region", MinimumSize = { LABEL_W, 0 }, MaximumSize = { LABEL_W, 40 }, StyleSheet = "QLabel { color: " .. C.dim .. "; }" }),
					ui:ComboBox({ ID = "RegionMode", MaximumSize = { 90, 28 } }),
					ui:LineEdit({ ID = "Region", Text = "0, 0, 1, 1", ToolTip = "Graph region as left, top, right, bottom (0-1 of the image)" }),
				}),
				ui:HGroup({
					Weight = 0,
					ui:Label({ ID = "AdvOutLabel", Text = "Output", MinimumSize = { LABEL_W, 0 }, MaximumSize = { LABEL_W, 40 }, StyleSheet = "QLabel { color: " .. C.dim .. "; }" }),
					ui:ComboBox({ ID = "OutputMode" }),
				}),
				ui:HGroup({ Weight = 0, ui:CheckBox({ ID = "Verify", Text = "Verify native output", Checked = true }), ui:CheckBox({ ID = "Diagnostics", Text = "Diagnostics", Checked = false }) }),
				ui:HGroup({
					Weight = 0,
					ui:Label({ ID = "AdvBezLabel", Text = "Custom curve", MinimumSize = { LABEL_W, 0 }, MaximumSize = { LABEL_W, 40 }, StyleSheet = "QLabel { color: " .. C.dim .. "; }" }),
					ui:LineEdit({ ID = "CustomBezier", Text = "0.25, 0.1, 0.25, 1", ToolTip = "Cubic-bezier x1, y1, x2, y2 used by Motion: Custom" }),
				}),
				ui:HGroup({ Weight = 0, ui:Button({ ID = "ImportImage", Text = "Import Graph Image…" }), ui:Button({ ID = "CleanCache", Text = "Clean Cache" }), ui:Button({ ID = "OpenLogs", Text = "Logs" }) }),
				ui:TextEdit({ ID = "DiagText", ReadOnly = true, Text = "", MinimumSize = { 0, 110 } }),
			}),
		})
		return win, win:GetItems()
	end

	function U.fill_combos(itm)
		itm.TraceMode:Clear()
		itm.TraceMode:AddItems({ "Auto Detect", "Pick Color" })
		itm.Motion:Clear()
		itm.Motion:AddItems({ "Linear", "Smooth", "Natural", "Custom" })
		itm.StartMode:Clear()
		itm.StartMode:AddItems({ "Comp start", "Current frame", "Frame…" })
		itm.RangeMode:Clear()
		itm.RangeMode:AddItems({ "Entire line", "Custom" })
		itm.RegionMode:Clear()
		itm.RegionMode:AddItems({ "Auto", "Custom" })
		itm.OutputMode:Clear()
		itm.OutputMode:AddItems({ "Auto (native, verified)", "Native editable stroke", "Rendered sequence" })
		itm.LineChoice:Clear()
		itm.LineChoice:AddItem("Best match (auto)")
	end

	function U.set_visible(itm, ids, visible)
		for _, id in ipairs(ids) do
			local w = itm[id]
			if w then
				pcall(function()
					w.Visible = visible
				end)
			end
		end
	end

	function U.set_enabled(itm, ids, enabled)
		for _, id in ipairs(ids) do
			local w = itm[id]
			if w then
				pcall(function()
					w.Enabled = enabled
				end)
			end
		end
	end

	return U
end
