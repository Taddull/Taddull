-- Paths, files, logging and small helpers for MaxTrace+.

local M = {}

M.PRODUCT = "MaxTrace+"
M.VERSION = "1.0.0"

local sep = package.config:sub(1, 1)
M.sep = sep

function M.join(...)
	local parts = { ... }
	local out = parts[1] or ""
	for i = 2, #parts do
		local p = parts[i]
		if p and p ~= "" then
			if out:sub(-1) == "/" then
				out = out .. p
			else
				out = out .. "/" .. p
			end
		end
	end
	return out
end

function M.dirname(p)
	return (p:match("^(.*)/[^/]*$")) or "."
end

function M.basename(p)
	return (p:match("([^/]+)$")) or p
end

-- Root of all per-user MaxTrace+ data. MAXTRACE_HOME overrides (tests).
function M.support_dir()
	local override = os.getenv("MAXTRACE_HOME")
	if override and override ~= "" then
		return override
	end
	local home = os.getenv("HOME") or ""
	return home .. "/Library/Application Support/MaxTrace+"
end

function M.paths()
	local root = M.support_dir()
	return {
		root = root,
		app = M.join(root, "app"),
		python = M.join(root, "venv", "bin", "python3"),
		worker = M.join(root, "app", "engine", "maxtrace_worker.py"),
		cache = M.join(root, "cache"),
		jobs = M.join(root, "cache", "jobs"),
		grabs = M.join(root, "cache", "grabs"),
		renders = M.join(root, "renders"),
		logs = M.join(root, "logs"),
		presets_builtin = M.join(root, "app", "presets", "presets.json"),
		presets_user = M.join(root, "presets", "user_presets.json"),
		settings = M.join(root, "settings.json"),
		calibration = M.join(root, "calibration.json"),
	}
end

function M.exists(p)
	if bmd and bmd.fileexists then
		local ok, r = pcall(bmd.fileexists, p)
		if ok then
			return r and true or false
		end
	end
	local f = io.open(p, "rb")
	if f then
		f:close()
		return true
	end
	return false
end

function M.mkdirs(p)
	if bmd and bmd.createdir then
		local ok = pcall(bmd.createdir, p)
		if ok and M.isdir(p) then
			return true
		end
	end
	return M.exec("/bin/mkdir -p " .. M.shq(p)) or M.isdir(p)
end

-- os.execute returns 0 (Lua 5.1) or true (5.2+/LuaJIT compat) on success.
function M.exec(cmd)
	local r = os.execute(cmd)
	return r == 0 or r == true
end

function M.isdir(p)
	if bmd and bmd.direxists then
		local ok, r = pcall(bmd.direxists, p)
		if ok then
			return r and true or false
		end
	end
	local f = io.open(p .. "/.", "rb")
	if f then
		f:close()
		return true
	end
	return false
end

function M.read(p)
	local f = io.open(p, "rb")
	if not f then
		return nil
	end
	local s = f:read("*a")
	f:close()
	return s
end

-- Atomic write: temp file + rename, so readers never see partial content.
function M.write(p, data)
	M.mkdirs(M.dirname(p))
	local tmp = p .. ".tmp" .. tostring(math.random(100000, 999999))
	local f, err = io.open(tmp, "wb")
	if not f then
		return false, err
	end
	f:write(data)
	f:close()
	local ok, rerr = os.rename(tmp, p)
	if not ok then
		os.remove(tmp)
		return false, rerr
	end
	return true
end

function M.mtime_token(p)
	-- Cheap change detector without lfs: size + first bytes.
	local s = M.read(p)
	if not s then
		return nil
	end
	return #s .. ":" .. s:sub(1, 64)
end

-- POSIX shell single-quote.
function M.shq(s)
	return "'" .. tostring(s):gsub("'", "'\\''") .. "'"
end

function M.uuid()
	if bmd and bmd.createuuid then
		local ok, u = pcall(bmd.createuuid)
		if ok and u then
			return (tostring(u):gsub("[^%w]", "")):lower():sub(1, 16)
		end
	end
	local t = {}
	for i = 1, 16 do
		t[i] = string.format("%x", math.random(0, 15))
	end
	return table.concat(t)
end

-- Load a table literal written by the Python worker (no code execution:
-- the chunk runs in an empty environment and may only build tables).
function M.load_table(p)
	local s = M.read(p)
	if not s or s == "" then
		return nil, "missing"
	end
	local chunk, err = loadstring("return " .. s, "=" .. M.basename(p))
	if not chunk then
		return nil, err
	end
	setfenv(chunk, {})
	local ok, t = pcall(chunk)
	if not ok or type(t) ~= "table" then
		return nil, tostring(t)
	end
	return t
end

-- Logging -------------------------------------------------------------------

local log_path
function M.log_init(dir)
	M.mkdirs(dir)
	log_path = M.join(dir, "maxtrace.log")
	local s = M.read(log_path)
	if s and #s > 3000000 then
		os.rename(log_path, log_path .. ".1")
	end
end

function M.log(level, msg, ...)
	if select("#", ...) > 0 then
		msg = string.format(msg, ...)
	end
	local line = string.format("%s %s %s\n", os.date("%Y-%m-%d %H:%M:%S"), level, tostring(msg))
	if log_path then
		local f = io.open(log_path, "ab")
		if f then
			f:write(line)
			f:close()
		end
	end
	if level == "ERROR" or os.getenv("MAXTRACE_DEBUG") then
		print("[MaxTrace+] " .. tostring(msg))
	end
end

function M.info(...)
	M.log("INFO", ...)
end

function M.warn(...)
	M.log("WARN", ...)
end

function M.error(...)
	M.log("ERROR", ...)
end

-- Misc ------------------------------------------------------------------------

function M.clamp(v, a, b)
	if v < a then
		return a
	elseif v > b then
		return b
	end
	return v
end

function M.round(v, d)
	local m = 10 ^ (d or 0)
	return math.floor(v * m + 0.5) / m
end

function M.deepcopy(t)
	if type(t) ~= "table" then
		return t
	end
	local o = {}
	for k, v in pairs(t) do
		o[k] = M.deepcopy(v)
	end
	return o
end

function M.merge(dst, src)
	for k, v in pairs(src or {}) do
		if type(v) == "table" and type(dst[k]) == "table" then
			M.merge(dst[k], v)
		else
			dst[k] = v
		end
	end
	return dst
end

function M.hex_to_rgb(hex)
	hex = tostring(hex or ""):gsub("#", "")
	if #hex == 3 then
		hex = hex:gsub(".", "%0%0")
	end
	if not hex:match("^%x%x%x%x%x%x$") then
		return nil
	end
	return tonumber(hex:sub(1, 2), 16) / 255, tonumber(hex:sub(3, 4), 16) / 255, tonumber(hex:sub(5, 6), 16) / 255
end

function M.rgb_to_hex(r, g, b)
	local function c(v)
		return M.clamp(math.floor(v * 255 + 0.5), 0, 255)
	end
	return string.format("#%02X%02X%02X", c(r), c(g), c(b))
end

return M
