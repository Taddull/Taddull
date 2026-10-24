-- Fusion composition integration: source discovery, frame capture,
-- applying / replacing / removing the generated highlight.
--
-- Only documented, sample-verified Fusion calls are used (see
-- docs/FUSION_API_NOTES.md). Everything is wrapped in pcall so a Fusion
-- error becomes a readable message instead of a script crash.

return function(util)
	local F = {}
	F.OWNER = "MaxTrace+"

	local function try(fn, ...)
		local ok, a, b, c = pcall(fn, ...)
		if ok then
			return a, b, c
		end
		return nil, a
	end

	function F.attrs(tool)
		local a = try(function()
			return tool:GetAttrs()
		end)
		return a or {}
	end

	function F.regid(tool)
		return F.attrs(tool).TOOLS_RegID
	end

	function F.name(tool)
		if not tool then
			return "?"
		end
		local n = F.attrs(tool).TOOLS_Name
		if not n then
			n = try(function()
				return tool.Name
			end)
		end
		return n or "?"
	end

	function F.get_data(obj, key)
		return (try(function()
			return obj:GetData(key)
		end))
	end

	function F.set_data(obj, key, value)
		return try(function()
			obj:SetData(key, value)
			return true
		end)
	end

	function F.is_owned(tool)
		return tool ~= nil and F.get_data(tool, "MaxTrace.Owner") == F.OWNER
	end

	function F.tool_list(comp, selected)
		local list = try(function()
			return comp:GetToolList(selected and true or false)
		end) or {}
		local out = {}
		for _, t in pairs(list) do
			out[#out + 1] = t
		end
		return out
	end

	-- Composition ----------------------------------------------------------

	function F.comp_info(comp)
		local a = try(function()
			return comp:GetAttrs()
		end) or {}
		local function pref(k)
			return tonumber((try(function()
				return comp:GetPrefs(k)
			end)))
		end
		local cur = try(function()
			return comp.CurrentTime
		end)
		return {
			name = a.COMPS_Name or "Composition",
			fps = pref("Comp.FrameFormat.Rate"),
			width = pref("Comp.FrameFormat.Width"),
			height = pref("Comp.FrameFormat.Height"),
			render_start = tonumber(a.COMPN_RenderStart) or tonumber(a.COMPN_GlobalStart) or 0,
			render_end = tonumber(a.COMPN_RenderEnd) or tonumber(a.COMPN_GlobalEnd) or 0,
			global_start = tonumber(a.COMPN_GlobalStart) or 0,
			global_end = tonumber(a.COMPN_GlobalEnd) or 0,
			current = tonumber(cur) or tonumber(a.COMPN_CurrentTime) or 0,
		}
	end

	function F.selected_tool(comp)
		local t = try(function()
			return comp.ActiveTool
		end)
		if t then
			return t
		end
		local sel = F.tool_list(comp, true)
		return sel[1]
	end

	local function main_output(tool)
		return (try(function()
			return tool:FindMainOutput(1)
		end))
	end

	local function main_input(tool)
		return (try(function()
			return tool:FindMainInput(1)
		end))
	end

	local function connected_output(inp)
		if not inp then
			return nil
		end
		return (try(function()
			return inp:GetConnectedOutput()
		end))
	end

	local function out_tool(out)
		if not out then
			return nil
		end
		return (try(function()
			return out:GetTool()
		end))
	end

	local function input_of(tool, id)
		return (try(function()
			return tool[id]
		end))
	end

	-- Image dimensions of an output at a time (Image object fields).
	function F.image_size(out, time)
		local img = try(function()
			return out[time]
		end)
		if not img then
			img = try(function()
				return out:GetValue(time)
			end)
		end
		if type(img) ~= "userdata" and type(img) ~= "table" then
			return nil
		end
		local w = tonumber((try(function()
			return img.Width
		end)))
		local h = tonumber((try(function()
			return img.Height
		end)))
		local meta = try(function()
			return img.Metadata
		end)
		local fname = meta and (try(function()
			return meta.Filename
		end)) or nil
		return w, h, fname
	end

	-- Decide which image to analyse and which output to composite over.
	-- A Paint node is analysed from its *input* (the clean graph, already
	-- transformed exactly as Paint sees it); the highlight is merged over
	-- the Paint node's output so existing strokes stay underneath.
	function F.resolve_source(comp, tool)
		if not tool then
			return nil, "Select the Paint, MediaIn or image node that shows your graph."
		end
		if F.is_owned(tool) then
			local bg = connected_output(input_of(tool, "Background"))
			if bg then
				return F.resolve_source(comp, out_tool(bg))
			end
			return nil, "Select your graph node, not a MaxTrace+ node."
		end
		local reg = F.regid(tool) or "?"
		local name = F.name(tool)
		if reg == "MediaOut" or reg == "Saver" then
			local co = connected_output(main_input(tool))
			if co then
				return F.resolve_source(comp, out_tool(co))
			end
			return nil, name .. " has nothing connected to it."
		end
		local out = main_output(tool)
		if not out then
			return nil, name .. " has no image output."
		end
		local dtype = (try(function()
			return out:GetAttrs().OUTS_DataType
		end))
		if dtype and dtype ~= "Image" then
			return nil, name .. " is not an image node (" .. tostring(dtype) .. ")."
		end
		local src = { tool = tool, name = name, regid = reg, output = out, analyze_output = out, analyze_name = name }
		if reg == "Paint" then
			local co = connected_output(main_input(tool))
			if not co then
				return nil, name .. " has no image connected to its input."
			end
			src.analyze_output = co
			src.analyze_name = F.name(out_tool(co))
		end
		return src
	end

	function F.describe_source(src)
		if not src then
			return "No source"
		end
		if src.analyze_name ~= src.name then
			return string.format("%s  (traces %s)", src.name, src.analyze_name)
		end
		return src.name
	end

	-- Pasting -------------------------------------------------------------

	function F.parse_setting(text)
		local t = try(function()
			return bmd.readstring(text)
		end)
		if type(t) ~= "table" then
			return nil, "Fusion could not parse the generated node settings."
		end
		return t
	end

	function F.paste(comp, text)
		local tbl, err = F.parse_setting(text)
		if not tbl then
			return nil, err
		end
		local ok, perr = pcall(function()
			return comp:Paste(tbl)
		end)
		if not ok then
			return nil, "Paste failed: " .. tostring(perr)
		end
		return true
	end

	-- All tools created by a generation, keyed by role.
	function F.find_generation(comp, gen_id)
		local found = {}
		for _, t in ipairs(F.tool_list(comp, false)) do
			if F.get_data(t, "MaxTrace.Owner") == F.OWNER and F.get_data(t, "MaxTrace.GenID") == gen_id then
				local role = F.get_data(t, "MaxTrace.Role") or "?"
				found[role] = t
			end
		end
		return found
	end

	-- Frame capture ------------------------------------------------------

	local function saver_text(name, filename)
		return string.format(
			[[{ Tools = ordered() { %s = Saver { CtrlWZoom = false, NameSet = true, CustomData = { MaxTrace = { Owner = "MaxTrace+", Role = "grab", GenID = "grab" } }, Inputs = { ProcessWhenBlendIs00 = Input { Value = 0, }, Clip = Input { Value = Clip { Filename = %q, FormatID = "PNGFormat", Length = 0, Saving = true, TrimIn = 0, ExtendFirst = 0, ExtendLast = 0, Loop = 1, AspectMode = 0, Depth = 0, TimeCode = 0, GlobalStart = -2000000000, GlobalEnd = 0 }, }, CreateDir = Input { Value = 1, }, OutputFormat = Input { Value = FuID { "PNGFormat" }, }, }, ViewInfo = OperatorInfo { Pos = { -2000, -2000 } }, }, }, }]],
			name,
			filename
		)
	end

	local function list_files(dir, prefix)
		local out = {}
		local entries = try(function()
			return bmd.readdir(util.join(dir, prefix .. "*"))
		end)
		if type(entries) == "table" then
			for _, e in pairs(entries) do
				if type(e) == "table" and e.Name and not e.IsDir then
					out[#out + 1] = util.join(dir, e.Name)
				end
			end
		end
		if #out == 0 then
			local p = io.popen("/bin/ls -1 " .. util.shq(dir) .. " 2>/dev/null")
			if p then
				for line in p:lines() do
					if line:sub(1, #prefix) == prefix then
						out[#out + 1] = util.join(dir, line)
					end
				end
				p:close()
			end
		end
		return out
	end

	local function remove_tool(t)
		return try(function()
			t:Delete()
			return true
		end)
	end

	local function cleanup_grabs(comp)
		for _, t in ipairs(F.tool_list(comp, false)) do
			if F.is_owned(t) and F.get_data(t, "MaxTrace.Role") == "grab" then
				remove_tool(t)
			end
		end
	end

	-- Render ``output`` at the given frames to PNG files through a temporary
	-- Saver. Returns { [frame] = path } or nil, reason.
	function F.render_frames(comp, output, frames, dir, tag)
		util.mkdirs(dir)
		local prefix = "mt_" .. tag .. "_"
		local filename = util.join(dir, prefix .. ".png")
		cleanup_grabs(comp)
		try(function()
			comp:StartUndo("MaxTrace+ frame capture")
		end)
		local results, reason = {}, nil
		local ok, err = pcall(function()
			local pok, perr = F.paste(comp, saver_text("MaxTrace_Grab", filename))
			if not pok then
				error(perr, 0)
			end
			local saver
			for _, t in ipairs(F.tool_list(comp, false)) do
				if F.is_owned(t) and F.get_data(t, "MaxTrace.Role") == "grab" then
					saver = t
				end
			end
			if not saver then
				error("Fusion did not create the capture Saver.", 0)
			end
			local inp = input_of(saver, "Input")
			local cok = inp and try(function()
				return inp:ConnectTo(output)
			end)
			if not connected_output(inp) then
				error("Could not connect the capture Saver.", 0)
			end
			for _, fr in ipairs(frames) do
				local before = {}
				for _, f in ipairs(list_files(dir, prefix)) do
					before[f] = true
				end
				local range = string.format("%d..%d", fr, fr)
				local r = try(function()
					return comp:Render({ Tool = saver, FrameRange = range, Wait = true, HiQ = true })
				end)
				local found
				for _, f in ipairs(list_files(dir, prefix)) do
					if not before[f] and f:lower():match("%.png$") then
						found = f
					end
				end
				if not found then
					-- Second documented form of the render call.
					try(function()
						return comp:Render({ Start = fr, End = fr, Tool = saver, Wait = true, HiQ = true })
					end)
					for _, f in ipairs(list_files(dir, prefix)) do
						if not before[f] and f:lower():match("%.png$") then
							found = f
						end
					end
				end
				if not found then
					error(string.format("Fusion did not write frame %d (render returned %s).", fr, tostring(r)), 0)
				end
				local final = util.join(dir, string.format("%s%d.png", prefix, fr))
				if found ~= final then
					os.remove(final)
					os.rename(found, final)
				end
				results[fr] = final
			end
		end)
		cleanup_grabs(comp)
		try(function()
			comp:EndUndo(false)
		end)
		if not ok then
			return nil, tostring(err)
		end
		return results
	end

	-- Obtain the analysis image for a source. Order: exact render of the
	-- analysed output; viewer snapshot; original media file (only reported
	-- as such). Returns { path, method, exact, width, height } or nil, reason.
	function F.capture_source(comp, src, frame, dir)
		local tag = util.uuid():sub(1, 8)
		local w, h, media = F.image_size(src.analyze_output, frame)
		local res, err = F.render_frames(comp, src.analyze_output, { frame }, dir, tag)
		if res and res[frame] then
			return { path = res[frame], method = "render", exact = true, width = w, height = h }
		end
		util.warn("Render capture failed: %s", tostring(err))
		-- Viewer snapshot of exactly this output.
		local vpath = util.join(dir, "mt_" .. tag .. "_viewer.png")
		local vok = try(function()
			local pl = comp:GetPreviewList()
			local view = pl.LeftView or pl.Left
			view:ViewOn(out_tool(src.analyze_output), 1)
			local viewer = view.View.CurrentViewer
			return viewer:SaveFile(vpath)
		end)
		if util.exists(vpath) then
			return { path = vpath, method = "viewer", exact = true, width = w, height = h, note = "Captured from the viewer." }
		end
		if media and util.exists(media) then
			local ext = (media:match("%.([%w]+)$") or ""):lower()
			if ext == "png" or ext == "jpg" or ext == "jpeg" or ext == "tif" or ext == "tiff" then
				return {
					path = media,
					method = "media",
					exact = false,
					width = w,
					height = h,
					note = "Using the original media file; upstream transforms are not reflected.",
				}
			end
		end
		return nil, "Could not read the frame from Fusion (" .. tostring(err) .. "). Use Import Graph Image."
	end

	-- Apply / remove -------------------------------------------------------

	local function consumers_of(output)
		local list = try(function()
			return output:GetConnectedInputs()
		end) or {}
		local out = {}
		for _, inp in pairs(list) do
			local t = try(function()
				return inp:GetTool()
			end)
			if t and not F.is_owned(t) then
				local id = (try(function()
					return inp:GetAttrs().INPS_ID
				end))
				out[#out + 1] = { input = inp, tool = t, tool_name = F.name(t), id = id }
			end
		end
		return out
	end

	local function flow_view(comp)
		return (try(function()
			return comp.CurrentFrame.FlowView
		end))
	end

	local LAYOUT = {
		canvas = { -1, 2 },
		loader = { 0, 2 },
		paint = { 0, 2 },
		soft = { 1, 3 },
		softmix = { 1, 2 },
		glow = { 2, 2 },
		merge = { 1, 1 },
	}

	local function place(comp, src_tool, tools)
		local flow = flow_view(comp)
		if not flow then
			return
		end
		local x, y = try(function()
			return flow:GetPos(src_tool)
		end)
		if not x then
			return
		end
		for role, t in pairs(tools) do
			local d = LAYOUT[role]
			if d then
				try(function()
					flow:SetPos(t, x + d[1], y + d[2])
				end)
			end
		end
	end

	-- Remove MaxTrace+ generations. If ``source_name`` is given only the
	-- highlight(s) composited over that source are removed. Downstream
	-- connections are restored to the original source output.
	function F.remove_generated(comp, source_name)
		local gens = {}
		local removed = 0
		for _, t in ipairs(F.tool_list(comp, false)) do
			if F.is_owned(t) and F.get_data(t, "MaxTrace.Role") == "merge" then
				local src = F.get_data(t, "MaxTrace.Source")
				if not source_name or src == source_name then
					local gid = F.get_data(t, "MaxTrace.GenID")
					gens[gid or ("?" .. F.name(t))] = true
					local bg = connected_output(input_of(t, "Background"))
					local mo = main_output(t)
					if mo then
						for _, c in ipairs(consumers_of(mo)) do
							if bg then
								try(function()
									c.input:ConnectTo(bg)
								end)
							end
						end
					end
				end
			end
		end
		for _, t in ipairs(F.tool_list(comp, false)) do
			if F.is_owned(t) then
				local gid = F.get_data(t, "MaxTrace.GenID")
				local role = F.get_data(t, "MaxTrace.Role")
				if role ~= "grab" and (gens[gid] or (not source_name and gid)) then
					if remove_tool(t) then
						removed = removed + 1
					end
				end
			end
		end
		-- Hidden stroke / spline tools that outlived their owner.
		for _, n in ipairs({ "MaxTrace_Path", "MaxTrace_PathWriteOn", "MaxTrace_MergeBlend" }) do
			local t = try(function()
				return comp:FindTool(n)
			end)
			if t and F.is_owned(t) and gens[F.get_data(t, "MaxTrace.GenID")] then
				remove_tool(t)
			end
		end
		return removed
	end

	function F.count_generated(comp)
		local n, src = 0, {}
		for _, t in ipairs(F.tool_list(comp, false)) do
			if F.is_owned(t) and F.get_data(t, "MaxTrace.Role") == "merge" then
				n = n + 1
				src[#src + 1] = F.get_data(t, "MaxTrace.Source") or "?"
			end
		end
		return n, src
	end

	-- Insert the generated highlight over ``src``. One undo step; on any
	-- failure everything created by this generation is removed again.
	function F.apply(comp, src, result)
		local text = util.read(result.setting or "")
		if not text or text == "" then
			return nil, "The generated node settings are missing."
		end
		local gen_id = result.gen_id
		try(function()
			comp:StartUndo("MaxTrace+ Highlight")
		end)
		local info = {}
		local ok, err = pcall(function()
			try(function()
				comp:Lock()
			end)
			info.replaced = F.remove_generated(comp, src.name)
			local pok, perr = F.paste(comp, text)
			if not pok then
				error(perr, 0)
			end
			local tools = F.find_generation(comp, gen_id)
			local merge = tools.merge
			if not merge then
				error("Fusion did not create the MaxTrace+ nodes.", 0)
			end
			local layer = tools[result.mode == "raster" and "loader" or "paint"]
			if not layer then
				error("The highlight layer node is missing after paste.", 0)
			end
			-- Wire: source -> Merge.Background, Merge -> previous consumers.
			local consumers = consumers_of(src.output)
			local bg = input_of(merge, "Background")
			try(function()
				return bg:ConnectTo(src.output)
			end)
			if F.name(out_tool(connected_output(bg))) ~= src.name then
				error("Could not connect " .. src.name .. " to MaxTrace_Merge.", 0)
			end
			local mout = main_output(merge)
			local rerouted = {}
			for _, c in ipairs(consumers) do
				try(function()
					return c.input:ConnectTo(mout)
				end)
				local now = out_tool(connected_output(c.input))
				if not now or F.name(now) ~= F.name(merge) then
					error("Could not reconnect " .. c.tool_name .. " to the highlight.", 0)
				end
				rerouted[#rerouted + 1] = c.tool_name .. "." .. tostring(c.id or "Input")
			end
			if not connected_output(input_of(merge, "Foreground")) then
				error("MaxTrace_Merge has no highlight connected.", 0)
			end
			F.set_data(merge, "MaxTrace.Source", src.name)
			F.set_data(merge, "MaxTrace.Rerouted", table.concat(rerouted, ","))
			F.set_data(merge, "MaxTrace.Mode", result.mode)
			F.set_data(merge, "MaxTrace.Created", os.date("%Y-%m-%d %H:%M:%S"))
			place(comp, src.tool, tools)
			info.tools = tools
			info.merge = merge
			info.layer = layer
			info.rerouted = rerouted
			try(function()
				comp:Unlock()
			end)
		end)
		if not ok then
			try(function()
				comp:Unlock()
			end)
			util.error("Apply failed: %s", tostring(err))
			-- Roll back whatever this generation created; restore wiring.
			local found = F.find_generation(comp, gen_id)
			if found.merge then
				local bgout = connected_output(input_of(found.merge, "Background"))
				local mo = main_output(found.merge)
				if mo and bgout then
					for _, c in ipairs(consumers_of(mo)) do
						try(function()
							c.input:ConnectTo(bgout)
						end)
					end
				end
			end
			for _, t in pairs(found) do
				remove_tool(t)
			end
			try(function()
				comp:EndUndo(true)
			end)
			return nil, tostring(err)
		end
		try(function()
			comp:EndUndo(true)
		end)
		-- Rendered sequences: confirm the Loader timing Fusion settled on.
		if result.mode == "raster" and info.layer and result.sequence then
			local gi = tonumber((try(function()
				return info.layer:GetInput("GlobalIn")
			end)))
			local want = tonumber(result.sequence.global_start)
			if gi and want and gi ~= want then
				util.warn("Loader GlobalIn %s != %s, correcting", tostring(gi), tostring(want))
				try(function()
					info.layer.GlobalIn[fu.TIME_UNDEFINED] = want
				end)
			end
		end
		return info
	end

	function F.view(comp, tool)
		try(function()
			local pl = comp:GetPreviewList()
			local view = pl.LeftView or pl.Left
			view:ViewOn(tool, 1)
		end)
	end

	function F.set_time(comp, t)
		try(function()
			comp.CurrentTime = t
		end)
	end

	return F
end
