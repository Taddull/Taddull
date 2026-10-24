-- Settings, presets and calibration persistence.
-- User data lives outside the app folder so reinstalling never overwrites it.

return function(util, json)
	local M = {}

	M.DEFAULTS = {
		preset = "Clean Red",
		style = { color = "#FF2020", thickness = 7, opacity = 1.0, softness = 0.12, halo = 0.0, glow = 0.0 },
		timing = { duration = 2.5, motion = "linear", custom = { 0.25, 0.1, 0.25, 1.0 }, start_mode = "comp", start_frame = 0 },
		range = { mode = "entire", start = 0, ["end"] = 100 },
		detect = { mode = "auto", color_hex = "#E02020", sensitivity = 0.5, gap = 0.5, simplify = 0.6, region_mode = "auto", region = { 0, 0, 1, 1 } },
		output = { mode = "auto", verify = true },
		ui = { advanced = false, diagnostics = false },
	}

	local function read_json(path)
		local s = util.read(path)
		if not s or s == "" then
			return nil
		end
		local ok, v = pcall(json.decode, s)
		if not ok then
			util.warn("Ignoring unreadable %s: %s", path, tostring(v))
			return nil
		end
		return v
	end

	local function sanitize(st)
		local d = M.DEFAULTS
		local s = st.style
		s.thickness = util.clamp(tonumber(s.thickness) or d.style.thickness, 0.5, 60)
		s.opacity = util.clamp(tonumber(s.opacity) or 1, 0.05, 1)
		s.softness = util.clamp(tonumber(s.softness) or 0, 0, 1)
		s.halo = util.clamp(tonumber(s.halo) or 0, 0, 1)
		s.glow = util.clamp(tonumber(s.glow) or 0, 0, 1)
		if not util.hex_to_rgb(s.color) then
			s.color = d.style.color
		end
		local t = st.timing
		t.duration = util.clamp(tonumber(t.duration) or 2.5, 0.5, 10)
		if t.motion ~= "linear" and t.motion ~= "smooth" and t.motion ~= "natural" and t.motion ~= "custom" then
			t.motion = "linear"
		end
		if type(t.custom) ~= "table" or #t.custom ~= 4 then
			t.custom = util.deepcopy(d.timing.custom)
		end
		local r = st.range
		r.start = util.clamp(tonumber(r.start) or 0, 0, 99.5)
		r["end"] = util.clamp(tonumber(r["end"]) or 100, 0.5, 100)
		if r["end"] <= r.start then
			r.start, r["end"] = 0, 100
		end
		local de = st.detect
		de.sensitivity = util.clamp(tonumber(de.sensitivity) or 0.5, 0, 1)
		de.gap = util.clamp(tonumber(de.gap) or 0.5, 0, 1)
		de.simplify = util.clamp(tonumber(de.simplify) or 0.6, 0.1, 5)
		return st
	end

	function M.load_settings()
		local st = util.deepcopy(M.DEFAULTS)
		local saved = read_json(util.paths().settings)
		if type(saved) == "table" then
			util.merge(st, saved)
		end
		local ok, res = pcall(sanitize, st)
		if not ok then
			util.warn("Settings reset to defaults: %s", tostring(res))
			return util.deepcopy(M.DEFAULTS)
		end
		return res
	end

	function M.save_settings(st)
		local ok, txt = pcall(json.encode, st, true)
		if ok then
			util.write(util.paths().settings, txt)
		end
	end

	function M.load_presets()
		local p = util.paths()
		local builtin = read_json(p.presets_builtin) or {}
		local user = read_json(p.presets_user) or {}
		local list = {}
		for _, pr in ipairs(builtin.presets or {}) do
			pr.builtin = true
			list[#list + 1] = pr
		end
		for _, pr in ipairs(user.presets or {}) do
			if type(pr) == "table" and pr.name and pr.style then
				pr.builtin = false
				list[#list + 1] = pr
			end
		end
		return list, builtin.colors or {}
	end

	function M.save_user_preset(name, style)
		local p = util.paths()
		local user = read_json(p.presets_user) or { version = 1, presets = {} }
		user.presets = user.presets or {}
		local replaced = false
		for i, pr in ipairs(user.presets) do
			if pr.name == name then
				user.presets[i] = { name = name, style = util.deepcopy(style) }
				replaced = true
			end
		end
		if not replaced then
			user.presets[#user.presets + 1] = { name = name, style = util.deepcopy(style) }
		end
		return util.write(p.presets_user, json.encode(user, true))
	end

	function M.delete_user_preset(name)
		local p = util.paths()
		local user = read_json(p.presets_user)
		if not user or not user.presets then
			return false
		end
		local out = {}
		for _, pr in ipairs(user.presets) do
			if pr.name ~= name then
				out[#out + 1] = pr
			end
		end
		user.presets = out
		return util.write(p.presets_user, json.encode(user, true))
	end

	-- Calibration is measured per Resolve version (see verify.py).
	function M.load_calibration(version_key)
		local all = read_json(util.paths().calibration) or {}
		return all[version_key]
	end

	function M.save_calibration(version_key, cal)
		local p = util.paths().calibration
		local all = read_json(p) or {}
		all[version_key] = cal
		util.write(p, json.encode(all, true))
	end

	return M
end
