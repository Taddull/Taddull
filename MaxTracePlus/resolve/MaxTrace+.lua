-- MAXTRACE_PLUS_LAUNCHER (identifies this file to install/uninstall)
--[[
MaxTrace+  -  automatic graph-line tracing and write-on highlight for Fusion.

Launcher installed into Fusion's user Scripts/Comp folder so it appears as
Workspace > Scripts > MaxTrace+ on the Fusion page. The application itself
lives in ~/Library/Application Support/MaxTrace+/app (see install.sh).
--]]

local home = os.getenv("HOME") or ""
local root = os.getenv("MAXTRACE_HOME")
if not root or root == "" then
	root = home .. "/Library/Application Support/MaxTrace+"
end
local app = root .. "/app"
local entry = app .. "/lua/maxtrace/main.lua"

local f = io.open(entry, "r")
if not f then
	print("[MaxTrace+] Application files not found at " .. app .. ". Please run install.sh again.")
	return
end
f:close()

local current = comp
if not current then
	pcall(function()
		current = fu:GetCurrentComp()
	end)
end
if not current then
	print("[MaxTrace+] Open the Fusion page with a composition before starting MaxTrace+.")
	return
end

local ok, err = pcall(function()
	local factory = dofile(entry)
	local main = factory({ root = app, comp = current, fu = fu or fusion, bmd = bmd })
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
