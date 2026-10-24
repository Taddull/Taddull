-- MAXTRACE_PLUS_LAUNCHER (identifies this file to install/uninstall)
--[[
MaxTrace+  -  automatic graph-line tracing and write-on highlight for Fusion.

Launcher installed into Fusion's user Scripts/Utility folder so it appears as
Workspace > Scripts > MaxTrace+ (on every page; it works on the Fusion page). The application itself
lives in ~/Library/Application Support/MaxTrace+/app (see install.sh).
--]]

local home = os.getenv("HOME") or ""
local root = os.getenv("MAXTRACE_HOME")
if not root or root == "" then
	root = home .. "/Library/Application Support/MaxTrace+"
end
local app_dir = root .. "/app"
local entry = app_dir .. "/lua/maxtrace/main.lua"

local f = io.open(entry, "r")
if not f then
	print("[MaxTrace+] Application files not found at " .. app_dir .. ". Please run install.sh again.")
	return
end
f:close()

-- Works as a Utility script (listed on every page) and as a Comp script.
-- Without an open composition the panel still opens and says what to do.
local fusion_app = fu or fusion or app
if not fusion_app then
	print("[MaxTrace+] Fusion scripting is not available here.")
	return
end
local current = comp
if not current then
	pcall(function()
		current = fusion_app:GetCurrentComp()
	end)
end

local ok, err = pcall(function()
	local factory = dofile(entry)
	local main = factory({ root = app_dir, comp = current, fu = fusion_app, bmd = bmd })
	main.run()
end)
if not ok then
	print("[MaxTrace+] " .. tostring(err))
	local logdir = root .. "/logs"
	os.execute("/bin/mkdir -p '" .. logdir:gsub("'", "'\\''") .. "'")
	local lf = io.open(logdir .. "/maxtrace.log", "ab")
	if lf then
		lf:write(os.date("%Y-%m-%d %H:%M:%S") .. " ERROR launcher: " .. tostring(err) .. "\n")
		lf:close()
	end
end
