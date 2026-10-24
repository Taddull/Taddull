-- MaxTrace+ controller: panel events and the one-click generation pipeline.
--
-- Generate:  capture source frame (Fusion render)  ->  build job (worker)
--            ->  apply to comp (one undo step)  ->  render + verify
--            ->  [native: auto-calibrate and retry | fall back to rendered]

return function(ctx)
	local root = ctx.root
	local function load(name)
		return dofile(root .. "/lua/maxtrace/" .. name .. ".lua")
	end
	local util = load("util")
	local json = load("json")
	local config = load("config")(util, json)
	local W = load("worker")(util, json)
	local F = load("fusionio")(util)
	local U = load("ui")(util)

	local fu = ctx.fu
	local bmd = ctx.bmd
	local paths = util.paths()
	util.log_init(paths.logs)
	math.randomseed(os.time())

	local M = {}

	function M.run()
		local ui = fu.UIManager
		if not ui then
			print("[MaxTrace+] Fusion UIManager is not available in this version of Resolve.")
			return
		end
		-- Single instance: bring the existing window forward.
		local existing = ui:FindWindow(U.WINDOW_ID)
		if existing then
			pcall(function()
				existing:Show()
				existing:Raise()
				existing:ActivateWindow()
			end)
			return
		end
		local disp = bmd.UIDispatcher(ui)

		local app_version = "unknown"
		pcall(function()
			local v = fu:GetVersion()
			app_version = string.format("%s-%s.%s.%s", tostring(v.App or "Fusion"), tostring(v[1]), tostring(v[2]), tostring(v[3]))
		end)
		util.info("MaxTrace+ %s launched in %s", util.VERSION, app_version)

		local state = {
			settings = config.load_settings(),
			busy = false,
			job = nil,
			gen = nil,
			analysis = nil,
			candidates = {},
			candidate_id = nil,
			candidate_hex = nil,
			import_path = nil,
			source_name = nil,
			comp = ctx.comp,
			calibration = config.load_calibration(app_version),
			preview_seq = 0,
		}
		local presets, palette = config.load_presets()

		local win, itm = U.build(ui, disp, state.settings.ui.geometry)
		U.fill_combos(itm)
		local timer = ui:Timer({ ID = "MaxTraceTimer", Interval = 150, SingleShot = false })

		-- Helpers ------------------------------------------------------------

		local function current_comp()
			local c = nil
			pcall(function()
				c = fu:GetCurrentComp()
			end)
			c = c or state.comp
			if c ~= state.comp then
				state.comp = c
				state.analysis = nil
			end
			return c
		end

		local function set_status(text, color)
			itm.Progress.Text = text
			if color then
				itm.Progress.StyleSheet = "QLabel { color: " .. color .. "; }"
			end
		end

		local function header(text, color)
			itm.HeaderStatus.Text = text
			itm.StatusDot.StyleSheet = U.dot_css(color)
		end

		local function diag(lines)
			if type(lines) == "table" then
				lines = table.concat(lines, "\n")
			end
			itm.DiagText.PlainText = lines or ""
		end

		local function friendly_error(msg)
			util.error("%s", tostring(msg))
			set_status(tostring(msg), "#F08A8A")
		end

		local function refresh_source()
			local comp = current_comp()
			if not comp then
				itm.SourceLabel.Text = "Open the Fusion page with your graph clip, then click Use Selected."
				header("No Fusion composition", "#E5A13A")
				return nil
			end
			local tool
			if state.source_name then
				pcall(function()
					tool = comp:FindTool(state.source_name)
				end)
			end
			tool = tool or F.selected_tool(comp)
			local src, why = F.resolve_source(comp, tool)
			if not src then
				itm.SourceLabel.Text = why
				header("No source", "#E5A13A")
				return nil
			end
			state.source_name = src.name
			local info = F.comp_info(comp)
			local txt = F.describe_source(src)
			if state.import_path then
				txt = "Image: " .. util.basename(state.import_path) .. "  →  over " .. src.name
			end
			itm.SourceLabel.Text = txt
			local n = F.count_generated(comp)
			header(
				string.format("%s · %s fps%s", tostring(info.width and (info.width .. "×" .. info.height) or "?"), tostring(info.fps and util.round(info.fps, 3) or "?"), n > 0 and " · highlighted" or ""),
				"#3CCB7F"
			)
			return src, comp
		end

		-- Settings <-> UI ------------------------------------------------------

		local MOTIONS = { "linear", "smooth", "natural", "custom" }
		local STARTS = { "comp", "current", "custom" }
		local OUTPUTS = { "auto", "native", "raster" }

		local function index_of(list, v)
			for i, x in ipairs(list) do
				if x == v then
					return i - 1
				end
			end
			return 0
		end

		local function update_swatches()
			local hex = state.settings.style.color:upper()
			local map = { SwRed = "#FF2020", SwYellow = "#FFD21F", SwCyan = "#22D3EE", SwGreen = "#35D06E", SwWhite = "#FFFFFF" }
			for id, h in pairs(map) do
				itm[id].StyleSheet = U.swatch_css(h, h == hex)
			end
		end

		local function update_value_labels()
			local s = state.settings
			itm.ThicknessVal.Text = string.format("%.1f px", s.style.thickness)
			itm.SoftnessVal.Text = string.format("%d%%", math.floor(s.style.softness * 100 + 0.5))
			itm.HaloVal.Text = s.style.halo > 0 and string.format("%d%%", math.floor(s.style.halo * 100 + 0.5)) or "Off"
			itm.OpacityVal.Text = string.format("%d%%", math.floor(s.style.opacity * 100 + 0.5))
			itm.DurationVal.Text = string.format("%.1f s", s.timing.duration)
			itm.SensitivityVal.Text = string.format("%d%%", math.floor(s.detect.sensitivity * 100 + 0.5))
			itm.GapVal.Text = string.format("%d%%", math.floor(s.detect.gap * 100 + 0.5))
			itm.SimplifyVal.Text = string.format("%.1f px", s.detect.simplify)
		end

		local function update_visibility()
			local s = state.settings
			pcall(function()
				itm.PickHex.Visible = s.detect.mode == "color"
				itm.StartFrame.Visible = s.timing.start_mode == "custom"
				itm.RangeStart.Visible = s.range.mode == "custom"
				itm.RangeEnd.Visible = s.range.mode == "custom"
				itm.Region.Enabled = s.detect.region_mode == "custom"
				itm.CustomBezier.Enabled = s.timing.motion == "custom"
			end)
			U.set_visible(itm, U.ADVANCED, s.ui.advanced)
			itm.DiagText.Visible = s.ui.advanced and s.ui.diagnostics
			itm.AdvToggle.Text = s.ui.advanced and "▾  Advanced" or "▸  Advanced"
			pcall(function()
				win:RecalcLayout()
			end)
		end

		local function apply_settings_to_ui()
			local s = state.settings
			itm.TraceMode.CurrentIndex = s.detect.mode == "color" and 1 or 0
			itm.PickHex.Text = s.detect.color_hex
			itm.ColorHex.Text = s.style.color
			itm.Thickness.Value = math.floor(s.style.thickness * 10 + 0.5)
			itm.Softness.Value = math.floor(s.style.softness * 100 + 0.5)
			itm.Halo.Value = math.floor(s.style.halo * 100 + 0.5)
			itm.Opacity.Value = math.floor(s.style.opacity * 100 + 0.5)
			itm.Glow.Checked = s.style.glow > 0
			itm.Duration.Value = math.floor(s.timing.duration * 10 + 0.5)
			itm.Motion.CurrentIndex = index_of(MOTIONS, s.timing.motion)
			itm.StartMode.CurrentIndex = index_of(STARTS, s.timing.start_mode)
			itm.StartFrame.Value = s.timing.start_frame or 0
			itm.RangeMode.CurrentIndex = s.range.mode == "custom" and 1 or 0
			itm.RangeStart.Value = s.range.start
			itm.RangeEnd.Value = s.range["end"]
			itm.Sensitivity.Value = math.floor(s.detect.sensitivity * 100 + 0.5)
			itm.Gap.Value = math.floor(s.detect.gap * 100 + 0.5)
			itm.Simplify.Value = math.floor(s.detect.simplify * 10 + 0.5)
			itm.RegionMode.CurrentIndex = s.detect.region_mode == "custom" and 1 or 0
			itm.Region.Text = table.concat(s.detect.region or { 0, 0, 1, 1 }, ", ")
			itm.OutputMode.CurrentIndex = index_of(OUTPUTS, s.output.mode)
			itm.Verify.Checked = s.output.verify and true or false
			itm.Diagnostics.Checked = s.ui.diagnostics and true or false
			itm.CustomBezier.Text = table.concat(s.timing.custom, ", ")
			itm.Preset:Clear()
			local sel = 0
			for i, pr in ipairs(presets) do
				itm.Preset:AddItem(pr.name)
				if pr.name == s.preset then
					sel = i - 1
				end
			end
			itm.Preset:AddItem("Custom")
			itm.Preset.CurrentIndex = s.preset == "Custom" and #presets or sel
			update_swatches()
			update_value_labels()
			update_visibility()
		end

		local function parse_numbers(text, n)
			local out = {}
			for v in tostring(text or ""):gmatch("[-%d%.]+") do
				out[#out + 1] = tonumber(v)
			end
			if #out ~= n then
				return nil
			end
			return out
		end

		local function collect()
			local s = state.settings
			s.detect.mode = itm.TraceMode.CurrentIndex == 1 and "color" or "auto"
			local ph = itm.PickHex.Text
			if util.hex_to_rgb(ph) then
				s.detect.color_hex = ph:upper():sub(1, 1) == "#" and ph:upper() or ("#" .. ph:upper())
			end
			local hex = itm.ColorHex.Text
			if util.hex_to_rgb(hex) then
				s.style.color = hex:sub(1, 1) == "#" and hex:upper() or ("#" .. hex:upper())
			end
			s.style.thickness = (tonumber(itm.Thickness.Value) or 70) / 10
			s.style.softness = (tonumber(itm.Softness.Value) or 0) / 100
			s.style.halo = (tonumber(itm.Halo.Value) or 0) / 100
			s.style.opacity = (tonumber(itm.Opacity.Value) or 100) / 100
			s.style.glow = itm.Glow.Checked and 0.25 or 0
			s.timing.duration = (tonumber(itm.Duration.Value) or 25) / 10
			s.timing.motion = MOTIONS[(itm.Motion.CurrentIndex or 0) + 1] or "linear"
			s.timing.start_mode = STARTS[(itm.StartMode.CurrentIndex or 0) + 1] or "comp"
			s.timing.start_frame = tonumber(itm.StartFrame.Value) or 0
			s.range.mode = itm.RangeMode.CurrentIndex == 1 and "custom" or "entire"
			s.range.start = tonumber(itm.RangeStart.Value) or 0
			s.range["end"] = tonumber(itm.RangeEnd.Value) or 100
			s.detect.sensitivity = (tonumber(itm.Sensitivity.Value) or 50) / 100
			s.detect.gap = (tonumber(itm.Gap.Value) or 50) / 100
			s.detect.simplify = (tonumber(itm.Simplify.Value) or 6) / 10
			s.detect.region_mode = itm.RegionMode.CurrentIndex == 1 and "custom" or "auto"
			local reg = parse_numbers(itm.Region.Text, 4)
			if reg then
				s.detect.region = reg
			end
			s.output.mode = OUTPUTS[(itm.OutputMode.CurrentIndex or 0) + 1] or "auto"
			s.output.verify = itm.Verify.Checked and true or false
			s.ui.diagnostics = itm.Diagnostics.Checked and true or false
			local bez = parse_numbers(itm.CustomBezier.Text, 4)
			if bez then
				s.timing.custom = bez
			end
			update_value_labels()
			return s
		end

		local function save_settings()
			pcall(function()
				local g = win:GetGeometry()
				if g and g[3] then
					state.settings.ui.geometry = { g[1], g[2], g[3], g[4] }
				end
			end)
			config.save_settings(state.settings)
		end

		local function mark_custom_preset()
			if state.settings.preset ~= "Custom" then
				state.settings.preset = "Custom"
				state.suppress = true
				itm.Preset.CurrentIndex = #presets
				state.suppress = false
			end
		end

		-- Busy state -------------------------------------------------------

		local function set_busy(busy)
			state.busy = busy
			U.set_enabled(itm, U.INTERACTIVE, not busy)
			if busy then
				itm.Generate.Text = "Cancel"
				itm.Generate.StyleSheet = U.CANCEL_CSS
			else
				itm.Generate.Text = "Generate Highlight"
				itm.Generate.StyleSheet = U.PRIMARY_CSS
				pcall(function()
					timer:Stop()
				end)
				state.job = nil
			end
		end

		local function fail(msg, res)
			if res and res.traceback then
				util.error("%s", res.traceback)
				if state.settings.ui.diagnostics then
					diag(res.traceback)
				end
			end
			set_busy(false)
			state.gen = nil
			friendly_error(msg or "Generation failed.")
		end

		-- Jobs -------------------------------------------------------------

		local function run_job(kind, spec, on_done, label)
			local job, err = W.new(kind, spec)
			if not job then
				return fail(err)
			end
			local ok, serr = W.start(job)
			if not ok then
				return fail(serr)
			end
			job.on_done = on_done
			job.label = label
			state.job = job
			set_status(label or "Working…", U.COLORS.dim)
			timer:Start()
		end

		local function poll()
			local job = state.job
			if not job then
				pcall(function()
					timer:Stop()
				end)
				return
			end
			local st, payload = W.poll(job)
			if st == "running" then
				if payload and payload.message then
					local pct = payload.progress and math.floor(payload.progress * 100 + 0.5) or nil
					set_status((pct and pct > 0) and string.format("%s · %d%%", payload.message, pct) or payload.message, U.COLORS.dim)
				end
				return
			end
			pcall(function()
				timer:Stop()
			end)
			state.job = nil
			if st == "failed" then
				return fail(payload and payload.message or "The engine failed.", payload)
			end
			local ok, err = pcall(job.on_done, payload)
			if not ok then
				fail("Unexpected error: " .. tostring(err))
			end
		end

		-- Candidates / preview ------------------------------------------

		local function show_preview(res)
			if res and res.preview and res.preview.path and util.exists(res.preview.path) then
				itm.Preview.Text = string.format('<img src="%s" width="%d">', res.preview.path, math.min(400, res.preview.width or 400))
			end
		end

		local function show_candidates(analysis)
			if not analysis or not analysis.candidates then
				return
			end
			state.candidates = analysis.candidates
			state.suppress = true
			itm.LineChoice:Clear()
			itm.LineChoice:AddItem("Best match (auto)")
			local sel = 0
			for i, c in ipairs(analysis.candidates) do
				local label = string.format("%d · %s · %s · %d%%", c.id + 1, c.color, c.kind == "joined" and "two-colour line" or c.kind, math.floor((c.confidence or 0) * 100 + 0.5))
				itm.LineChoice:AddItem(label)
				if state.candidate_id ~= nil and c.id == state.candidate_id then
					sel = i
				end
			end
			itm.LineChoice.CurrentIndex = sel
			state.suppress = false
		end

		local function warnings_text(res)
			local lines = {}
			for _, w in ipairs(res.warnings or {}) do
				lines[#lines + 1] = "⚠ " .. tostring(w.message or w)
			end
			return lines
		end

		-- Detection spec shared by preview and build.
		local function detect_spec()
			local s = state.settings
			return {
				mode = s.detect.mode,
				color_hex = s.detect.color_hex,
				candidate = state.candidate_id,
				candidate_hex = state.candidate_hex,
				sensitivity = s.detect.sensitivity,
				gap = s.detect.gap,
				simplify_px = s.detect.simplify,
				region = s.detect.region_mode == "custom" and s.detect.region or nil,
			}
		end

		local function next_preview_path()
			state.preview_seq = state.preview_seq + 1
			return util.join(paths.cache, "previews", string.format("preview_%s_%d.png", util.uuid():sub(1, 6), state.preview_seq))
		end

		-- Source image -----------------------------------------------------

		local function obtain_image(comp, src, frame)
			if state.import_path then
				if not util.exists(state.import_path) then
					return nil, "The imported image no longer exists: " .. state.import_path
				end
				local w, h = F.image_size(src.output, frame)
				return { path = state.import_path, method = "import", exact = false, width = w, height = h }
			end
			set_status("Reading source frame", U.COLORS.dim)
			return F.capture_source(comp, src, frame, paths.grabs)
		end

		-- Preview (detect only) ---------------------------------------------

		local function on_preview_done(res)
			set_busy(false)
			if not res.ok then
				return friendly_error(res.message)
			end
			state.analysis = res.analysis
			show_candidates(res.analysis)
			show_preview(res)
			local sel = res.selected or {}
			local lines = warnings_text(res)
			set_status(
				string.format("Line %s · %d points · confidence %d%%%s", tostring(sel.color), sel.points or 0, math.floor((sel.confidence or 0) * 100 + 0.5), #lines > 0 and ("  " .. lines[1]) or ""),
				#lines > 0 and "#E5C07B" or "#7FD1A0"
			)
			diag({ json.encode(res.analysis or {}, true) })
		end

		local function start_preview()
			if state.busy then
				return
			end
			collect()
			local src, comp = refresh_source()
			if not src then
				return friendly_error(itm.SourceLabel.Text)
			end
			local info = F.comp_info(comp)
			set_busy(true)
			local image, err = obtain_image(comp, src, info.current)
			if not image then
				return fail(err)
			end
			state.last_image = image
			run_job("analyze", {
				image = image.path,
				detect = detect_spec(),
				style = state.settings.style,
				range = { start = state.settings.range.mode == "custom" and state.settings.range.start / 100 or 0, ["end"] = state.settings.range.mode == "custom" and state.settings.range["end"] / 100 or 1 },
				preview_path = next_preview_path(),
				diagnostics = state.settings.ui.diagnostics,
			}, on_preview_done, "Detecting line")
		end

		-- Generate pipeline --------------------------------------------------

		local run_build, run_verify, finish

		local function build_spec(gen)
			local s = state.settings
			local info = gen.info
			local spec = {
				image = gen.image.path,
				source_kind = gen.image.method,
				detect = detect_spec(),
				style = util.deepcopy(s.style),
				timing = {
					fps = info.fps,
					duration = s.timing.duration,
					motion = s.timing.motion,
					custom = s.timing.custom,
					start_frame = gen.start,
					comp_start = info.render_start,
					comp_end = info.render_end,
				},
				range = {
					start = s.range.mode == "custom" and s.range.start / 100 or 0,
					["end"] = s.range.mode == "custom" and s.range["end"] / 100 or 1,
				},
				output = {
					mode = gen.mode,
					comp_width = info.width,
					comp_height = info.height,
					gen_id = util.uuid():sub(1, 12),
					render_dir = paths.renders,
				},
				calibration = state.calibration,
				preview_path = next_preview_path(),
				diagnostics = s.ui.diagnostics,
				force = gen.force,
			}
			-- An imported image may differ in size from the node it is drawn
			-- over; the path is then fitted to the node's image size.
			if (gen.image.method == "import" or gen.image.method == "media") and gen.node_w and gen.node_h then
				spec.output.target_width = gen.node_w
				spec.output.target_height = gen.node_h
			end
			return spec
		end

		local function on_verify_done(res)
			local gen = state.gen
			if not gen then
				return
			end
			gen.verify_result = res
			if res.ok then
				if gen.mode == "native" then
					local cal = util.deepcopy(gen.result.calibration or {})
					cal.verified = true
					state.calibration = cal
					config.save_calibration(gen.app_version, cal)
				end
				gen.verified = true
				return finish()
			end
			util.warn("Verification failed (%s): %s", gen.mode, tostring(res.reason or res.message))
			if gen.mode == "native" then
				if res.suggested_calibration and gen.attempt < 2 then
					gen.attempt = gen.attempt + 1
					state.calibration = res.suggested_calibration
					set_status(string.format("Calibrating native stroke (pass %d)", gen.attempt + 1), U.COLORS.dim)
					return run_build()
				end
				if gen.auto then
					gen.fallback_reason = res.reason or res.message
					gen.mode = "raster"
					gen.attempt = 0
					return run_build()
				end
			end
			gen.verify_warning = res.reason or res.message or "Could not confirm the rendered result."
			finish()
		end

		function run_verify()
			local gen = state.gen
			local res = gen.result
			local comp = gen.comp
			local info = gen.info
			local layer = gen.applied.tools[gen.mode == "raster" and "loader" or "paint"]
			local out = layer and layer:FindMainOutput(1)
			if not out then
				gen.verify_warning = "Could not locate the highlight layer to verify."
				return finish()
			end
			local frames, roles = {}, {}
			local function add(role, fr)
				if fr >= info.render_start and fr <= info.render_end and not roles[fr] then
					frames[#frames + 1] = fr
					roles[fr] = role
				end
			end
			add("before", res.anim_start - 1)
			add("start", res.anim_start)
			add("mid", res.mid_frame)
			add("end", math.min(res.anim_end, info.render_end))
			set_status("Verifying the rendered highlight", U.COLORS.dim)
			local files, err = F.render_frames(comp, out, frames, util.join(paths.cache, "verify"), util.uuid():sub(1, 8))
			if not files then
				gen.verify_warning = "Could not render frames to verify (" .. tostring(err) .. ")."
				if gen.mode == "native" and gen.auto then
					gen.fallback_reason = gen.verify_warning
					gen.mode = "raster"
					return run_build()
				end
				return finish()
			end
			local role_files = {}
			for fr, p in pairs(files) do
				role_files[roles[fr]] = p
			end
			if res.anim_end > info.render_end then
				role_files["end"] = nil -- the full line is never reached inside the comp
				role_files["mid"] = nil
			end
			if not role_files["end"] then
				gen.verify_warning = "The animation ends after the composition; full-line check skipped."
				return finish()
			end
			run_job("verify", {
				verify = {
					frames = role_files,
					path_px = res.path_sent_px,
					width = res.width,
					height = res.height,
					thickness_px = res.thickness_px,
					color = res.color,
					mid_progress = res.mid_progress,
					calibration = res.calibration,
					mode = gen.mode,
				},
				diagnostics = state.settings.ui.diagnostics,
			}, on_verify_done, "Verifying the rendered highlight")
		end

		local function on_build_done(res)
			local gen = state.gen
			if not gen then
				return
			end
			if not res.ok then
				if res.code == "cancelled" then
					set_busy(false)
					state.gen = nil
					return set_status("Cancelled", U.COLORS.dim)
				end
				return fail(res.message, res)
			end
			state.analysis = res.analysis
			show_candidates(res.analysis)
			show_preview(res)
			gen.result = res
			set_status("Applying animation", U.COLORS.dim)
			local src = F.resolve_source(gen.comp, gen.comp:FindTool(gen.src_name))
			if not src then
				return fail("The source node " .. gen.src_name .. " is no longer available.")
			end
			local applied, err = F.apply(gen.comp, src, res)
			if not applied then
				if gen.mode == "native" and gen.auto then
					gen.fallback_reason = err
					gen.mode = "raster"
					return run_build()
				end
				return fail("Could not add the highlight to the composition: " .. tostring(err))
			end
			gen.applied = applied
			if gen.verify then
				return run_verify()
			end
			finish()
		end

		function run_build()
			local gen = state.gen
			local label = gen.mode == "raster" and "Rendering highlight frames" or "Generating path"
			run_job("build", build_spec(gen), on_build_done, label)
		end

		function finish()
			local gen = state.gen
			local res = gen.result
			set_busy(false)
			local sel = res.selected or {}
			local lines = warnings_text(res)
			local method
			if gen.mode == "native" then
				method = "Native editable Paint stroke (MaxTrace_Path)"
			else
				method = "Rendered PNG sequence (MaxTrace_Render)"
			end
			local verified = gen.verified and " · verified" or ""
			if gen.fallback_reason then
				lines[#lines + 1] = "Native stroke not used: " .. tostring(gen.fallback_reason)
			end
			if gen.verify_warning then
				lines[#lines + 1] = "⚠ " .. gen.verify_warning
			end
			if gen.image.note then
				lines[#lines + 1] = gen.image.note
			end
			local summary = string.format(
				"Complete · %s%s · %d frames from %d · %d points",
				gen.mode == "native" and "native stroke" or "rendered",
				verified,
				res.anim_frames or 0,
				res.anim_start or 0,
				sel.points or 0
			)
			local color = (#lines > 0) and "#E5C07B" or "#7FD1A0"
			set_status(summary .. ((#lines > 0) and ("\n" .. table.concat(lines, "\n")) or ""), color)
			diag({
				"Method: " .. method,
				"Source capture: " .. tostring(gen.image.method),
				"Detected line: " .. tostring(sel.color) .. "  confidence " .. tostring(sel.confidence),
				"Source line width: " .. tostring(sel.thickness_px) .. " px; highlight " .. string.format("%.2f", res.thickness_px or 0) .. " px",
				"Rerouted: " .. table.concat(gen.applied.rerouted or {}, ", "),
				"Verification: " .. json.encode(gen.verify_result or {}, true),
			})
			if #(gen.applied.rerouted or {}) == 0 then
				F.view(gen.comp, gen.applied.merge)
			end
			util.info("generation complete: %s %s", gen.mode, verified)
			state.gen = nil
			collect()
			save_settings()
			refresh_source()
		end

		local function start_generate()
			if state.busy then
				-- Cancel.
				if state.job then
					W.cancel(state.job)
				end
				set_status("Cancelling…", U.COLORS.dim)
				return
			end
			collect()
			local src, comp = refresh_source()
			if not src then
				return friendly_error(itm.SourceLabel.Text)
			end
			local info = F.comp_info(comp)
			if not info.fps or info.fps <= 0 then
				return friendly_error("Could not read the composition frame rate.")
			end
			set_busy(true)
			local image, err = obtain_image(comp, src, info.current)
			if not image then
				return fail(err)
			end
			local s = state.settings
			local start = info.render_start
			if s.timing.start_mode == "current" then
				start = info.current
			elseif s.timing.start_mode == "custom" then
				start = math.floor(tonumber(s.timing.start_frame) or info.render_start)
			end
			local mode = s.output.mode
			local native_ok = image.method == "render" or image.method == "viewer"
			local gen = {
				comp = comp,
				src_name = src.name,
				info = info,
				image = image,
				start = start,
				attempt = 0,
				auto = mode == "auto",
				mode = (mode == "raster" or (mode == "auto" and not native_ok)) and "raster" or "native",
				verify = (s.output.verify or mode == "auto") and image.method == "render",
				app_version = app_version,
			}
			if mode == "auto" and not native_ok then
				gen.fallback_reason = "the frame could not be rendered from Fusion, so the native stroke cannot be verified"
			end
			gen.node_w, gen.node_h = F.image_size(src.output, info.current)
			state.gen = gen
			run_build()
		end

		local function remove_highlight()
			if state.busy then
				return
			end
			local comp = current_comp()
			if not comp then
				return friendly_error("No Fusion composition is open.")
			end
			local src = refresh_source()
			local n
			pcall(function()
				comp:StartUndo("MaxTrace+ Remove")
			end)
			local ok, err = pcall(function()
				n = F.remove_generated(comp, src and src.name or nil)
			end)
			pcall(function()
				comp:EndUndo(true)
			end)
			if not ok then
				return friendly_error("Remove failed: " .. tostring(err))
			end
			if n and n > 0 then
				set_status(string.format("Removed %d MaxTrace+ node%s · original connections restored", n, n == 1 and "" or "s"), "#7FD1A0")
			else
				set_status("No MaxTrace+ highlight found for this source.", U.COLORS.dim)
			end
			refresh_source()
		end

		-- Events ------------------------------------------------------------

		win.On[U.WINDOW_ID].Close = function(ev)
			if state.job then
				W.cancel(state.job)
			end
			pcall(function()
				timer:Stop()
			end)
			collect()
			save_settings()
			disp:ExitLoop()
		end

		function disp.On.Timeout(ev)
			if ev.who == "MaxTraceTimer" then
				local ok, err = pcall(poll)
				if not ok then
					fail("Unexpected error: " .. tostring(err))
				end
			end
		end

		function win.On.Generate.Clicked(ev)
			local ok, err = pcall(start_generate)
			if not ok then
				fail("Unexpected error: " .. tostring(err))
			end
		end

		function win.On.Detect.Clicked(ev)
			local ok, err = pcall(start_preview)
			if not ok then
				fail("Unexpected error: " .. tostring(err))
			end
		end

		function win.On.Remove.Clicked(ev)
			local ok, err = pcall(remove_highlight)
			if not ok then
				friendly_error("Unexpected error: " .. tostring(err))
			end
		end

		function win.On.UseSelected.Clicked(ev)
			local comp = current_comp()
			state.source_name = nil
			state.analysis = nil
			state.candidate_id, state.candidate_hex = nil, nil
			if comp then
				local t = F.selected_tool(comp)
				if t then
					state.source_name = F.name(t)
				end
			end
			refresh_source()
			set_status("Ready", U.COLORS.dim)
		end

		function win.On.AdvToggle.Clicked(ev)
			state.settings.ui.advanced = not state.settings.ui.advanced
			update_visibility()
		end

		function win.On.TraceMode.CurrentIndexChanged(ev)
			if state.suppress then
				return
			end
			collect()
			state.candidate_id, state.candidate_hex = nil, nil
			update_visibility()
		end

		function win.On.LineChoice.CurrentIndexChanged(ev)
			if state.suppress then
				return
			end
			local i = itm.LineChoice.CurrentIndex or 0
			if i <= 0 then
				state.candidate_id, state.candidate_hex = nil, nil
			else
				local c = state.candidates[i]
				if c then
					state.candidate_id, state.candidate_hex = c.id, c.color
				end
			end
			if state.analysis and not state.busy then
				start_preview()
			end
		end

		for _, id in ipairs({ "Motion", "StartMode", "RangeMode", "RegionMode", "OutputMode" }) do
			win.On[id].CurrentIndexChanged = function(ev)
				if state.suppress then
					return
				end
				collect()
				update_visibility()
			end
		end

		function win.On.Preset.CurrentIndexChanged(ev)
			if state.suppress then
				return
			end
			local i = (itm.Preset.CurrentIndex or 0) + 1
			local pr = presets[i]
			if not pr then
				state.settings.preset = "Custom"
				return
			end
			state.settings.preset = pr.name
			for k, v in pairs(pr.style) do
				state.settings.style[k] = v
			end
			state.suppress = true
			apply_settings_to_ui()
			state.suppress = false
		end

		function win.On.SavePreset.Clicked(ev)
			collect()
			local name = nil
			pcall(function()
				local c = current_comp()
				local r = c:AskUser("Save MaxTrace+ preset", { { "Name", Name = "Preset name", "Text", Default = "My Highlight", Lines = 1 } })
				name = r and r.Name
			end)
			if not name or name == "" then
				return
			end
			for _, pr in ipairs(presets) do
				if pr.builtin and pr.name == name then
					return friendly_error("'" .. name .. "' is a built-in preset; choose another name.")
				end
			end
			if config.save_user_preset(name, state.settings.style) then
				presets, palette = config.load_presets()
				state.settings.preset = name
				state.suppress = true
				apply_settings_to_ui()
				state.suppress = false
				set_status("Preset saved: " .. name, "#7FD1A0")
			end
		end

		local function on_style_changed()
			if state.suppress then
				return
			end
			collect()
			mark_custom_preset()
			update_swatches()
		end

		for _, id in ipairs({ "Thickness", "Softness", "Halo", "Opacity" }) do
			win.On[id].ValueChanged = on_style_changed
		end
		for _, id in ipairs({ "Duration", "Sensitivity", "Gap", "Simplify" }) do
			win.On[id].ValueChanged = function(ev)
				if state.suppress then
					return
				end
				collect()
			end
		end
		win.On.Glow.Clicked = on_style_changed
		win.On.ColorHex.EditingFinished = on_style_changed
		win.On.PickHex.EditingFinished = function(ev)
			if not state.suppress then
				collect()
			end
		end

		local SW = { SwRed = "#FF2020", SwYellow = "#FFD21F", SwCyan = "#22D3EE", SwGreen = "#35D06E", SwWhite = "#FFFFFF" }
		for id, hex in pairs(SW) do
			win.On[id].Clicked = function(ev)
				itm.ColorHex.Text = hex
				on_style_changed()
			end
		end

		function win.On.ImportImage.Clicked(ev)
			if state.import_path then
				state.import_path = nil
				itm.ImportImage.Text = "Import Graph Image…"
				refresh_source()
				return
			end
			local path
			pcall(function()
				path = fu:RequestFile(os.getenv("HOME") or "", "", { FReqS_Title = "Choose a graph image (PNG, JPG, TIFF)" })
			end)
			if not path or path == "" then
				pcall(function()
					local r = current_comp():AskUser("Import graph image", { { "File", Name = "Image (PNG, JPG, TIFF)", "FileBrowse", Save = false } })
					path = r and r.File
				end)
			end
			if path and path ~= "" then
				pcall(function()
					path = current_comp():MapPath(path)
				end)
			end
			if path and path ~= "" then
				state.import_path = path
				state.analysis = nil
				itm.ImportImage.Text = "Clear Imported Image"
				refresh_source()
				set_status("Imported image will be traced and drawn over the selected node.", U.COLORS.dim)
			end
		end

		function win.On.CleanCache.Clicked(ev)
			if state.busy then
				return
			end
			set_busy(true)
			run_job("clean", { cache_dir = paths.cache }, function(res)
				set_busy(false)
				set_status(string.format("Cache cleaned (%.1f MB)", (res.removed_bytes or 0) / 1e6), "#7FD1A0")
			end, "Cleaning cache")
		end

		function win.On.OpenLogs.Clicked(ev)
			pcall(function()
				bmd.openfileexternal("Open", paths.logs)
			end)
		end

		function win.On.Diagnostics.Clicked(ev)
			if state.suppress then
				return
			end
			collect()
			update_visibility()
		end

		-- Start ----------------------------------------------------------------

		state.suppress = true
		apply_settings_to_ui()
		state.suppress = false
		refresh_source()
		local ready, why = W.engine_ready()
		if not ready then
			set_status(why, "#F08A8A")
		else
			set_status("Ready", U.COLORS.dim)
		end
		itm.Preview.Text = "Preview appears after detection"
		win:Show()
		disp:RunLoop()
		win:Hide()
	end

	return M
end
