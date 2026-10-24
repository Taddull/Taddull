-- Minimal Fusion / UIManager mock for offline tests of the MaxTrace+ Lua code.
--
-- It models what MaxTrace+ relies on: tools with inputs/outputs and
-- connections, CustomData, Paste of setting tables (parsed with the same
-- constructor syntax Fusion uses), FindTool/GetToolList/Delete, undo
-- bracketing, comp attributes/prefs, Saver rendering through a host hook,
-- the flow view and a scriptable UIManager. It is NOT Fusion: behaviour of
-- the real renderer is supplied by the Python test (see test_lua_integration.py).

local Mock = { calls = {}, undo = {}, hooks = {} }

local function record(name, ...)
	Mock.calls[#Mock.calls + 1] = name
end

-- Setting parser ----------------------------------------------------------------

local function ctor(kind)
	return function(t)
		t = t or {}
		t.__ctor = kind
		return t
	end
end

local setting_env = {
	FuID = function(t)
		return { __ctor = "FuID", value = t[1] }
	end,
	ordered = function()
		return function(t)
			return t
		end
	end,
}
setmetatable(setting_env, { __index = function(_, k)
	return ctor(k)
end })

local function readstring(text)
	local chunk, err = loadstring("return " .. text)
	if not chunk then
		error("readstring parse error: " .. tostring(err))
	end
	setfenv(chunk, setting_env)
	return chunk()
end

-- Graph objects -----------------------------------------------------------------

local OutputMethods, InputMethods, ToolMethods = {}, {}, {}
local OutputMT = {
	__index = function(o, k)
		if type(k) == "number" then
			return Mock.image_for(o, k)
		end
		return OutputMethods[k]
	end,
}
local InputMT = {
	__index = function(i, k)
		if type(k) == "number" then
			return rawget(i, "_value")
		end
		return InputMethods[k]
	end,
	__newindex = function(i, k, v)
		if type(k) == "number" then
			rawset(i, "_value", v)
		else
			rawset(i, k, v)
		end
	end,
}

local function new_output(tool, id)
	return setmetatable({ _tool = tool, _id = id, _consumers = {} }, OutputMT)
end

local function new_input(tool, id)
	return setmetatable({ _tool = tool, _id = id }, InputMT)
end

function OutputMethods.GetConnectedInputs(self)
	local t = {}
	for inp in pairs(self._consumers) do
		t[#t + 1] = inp
	end
	table.sort(t, function(a, b)
		return (a._tool._name .. a._id) < (b._tool._name .. b._id)
	end)
	return t
end
function OutputMethods.GetTool(self)
	return self._tool
end
function OutputMethods.GetAttrs(self)
	return { OUTS_ID = self._id, OUTS_DataType = "Image" }
end
function OutputMethods.GetValue(self, t)
	return Mock.image_for(self, t)
end

function InputMethods.ConnectTo(self, out)
	if self._source then
		self._source._consumers[self] = nil
	end
	self._source = out
	if out then
		out._consumers[self] = true
	end
	return true
end
function InputMethods.GetConnectedOutput(self)
	return self._source
end
function InputMethods.GetTool(self)
	return self._tool
end
function InputMethods.GetAttrs(self)
	return { INPS_ID = self._id, INPS_Name = self._id }
end

local MAIN_INPUT = { Paint = "Input", Merge = "Background", Saver = "Input", Transform = "Input", Blur = "Input", SoftGlow = "Input", MediaOut = "Input" }
local MAIN_OUTPUT = { PolylineStroke = "Out", BezierSpline = "Value" }

local ToolMT = {}
ToolMT = {
	__index = function(t, k)
		if k == "Name" then
			return rawget(t, "_name")
		end
		local m = ToolMethods[k]
		if m then
			return m
		end
		if type(k) ~= "string" then
			return nil
		end
		local outs = rawget(t, "_outputs")
		if outs[k] then
			return outs[k]
		end
		if k == "Output" or k == "Out" or k == "Value" then
			outs[k] = new_output(t, k)
			return outs[k]
		end
		local ins = rawget(t, "_inputs")
		if not ins[k] then
			ins[k] = new_input(t, k)
		end
		return ins[k]
	end,
	__newindex = function(t, k, v)
		local inp = t[k]
		if type(v) == "table" and getmetatable(v) == OutputMT then
			inp:ConnectTo(v)
		elseif type(v) == "table" and getmetatable(v) == ToolMT then
			inp:ConnectTo(v:FindMainOutput(1))
		else
			inp._value = v
		end
	end,
}

local function new_tool(comp, regid, name)
	local t = setmetatable({ _comp = comp, _regid = regid, _name = name, _inputs = {}, _outputs = {}, _data = {}, _pos = { 0, 0 } }, ToolMT)
	return t
end

function ToolMethods.GetAttrs(self)
	return { TOOLS_Name = self._name, TOOLS_RegID = self._regid }
end
function ToolMethods.SetAttrs(self, a)
	if a.TOOLS_Name then
		self._comp:_rename(self, a.TOOLS_Name)
	end
end
function ToolMethods.GetData(self, key)
	return self._data[key]
end
function ToolMethods.SetData(self, key, v)
	self._data[key] = v
end
function ToolMethods.FindMainOutput(self, i)
	local id = MAIN_OUTPUT[self._regid] or "Output"
	return self[id]
end
function ToolMethods.FindMainInput(self, i)
	local id = MAIN_INPUT[self._regid]
	if not id then
		return nil
	end
	return self[id]
end
function ToolMethods.ConnectInput(self, id, src)
	local out = src
	if getmetatable(src) == ToolMT then
		out = src:FindMainOutput(1)
	end
	return self[id]:ConnectTo(out)
end
function ToolMethods.GetInput(self, id)
	return rawget(self._inputs, id) and rawget(self._inputs, id)._value or nil
end
function ToolMethods.Delete(self)
	self._comp:_remove(self)
end

-- Composition ----------------------------------------------------------------

local CompMethods = {}
local CompMT = { __index = CompMethods }

function Mock.new_comp(opts)
	local c = setmetatable({
		_tools = {},
		_byname = {},
		_attrs = opts.attrs,
		_prefs = opts.prefs,
		CurrentTime = opts.current or 0,
		_undo_depth = 0,
		_locked = 0,
	}, CompMT)
	c.CurrentFrame = {
		FlowView = {
			GetPos = function(_, tool)
				return tool._pos[1], tool._pos[2]
			end,
			SetPos = function(_, tool, x, y)
				tool._pos = { x, y }
			end,
		},
	}
	return c
end

function CompMethods._unique(self, name)
	if not self._byname[name] then
		return name
	end
	local i = 1
	while self._byname[name .. "_" .. i] do
		i = i + 1
	end
	return name .. "_" .. i
end

function CompMethods._add(self, regid, name)
	name = self:_unique(name)
	local t = new_tool(self, regid, name)
	self._tools[#self._tools + 1] = t
	self._byname[name] = t
	return t
end

function CompMethods._rename(self, tool, name)
	self._byname[tool._name] = nil
	tool._name = self:_unique(name)
	self._byname[tool._name] = tool
end

function CompMethods._remove(self, tool)
	for id, inp in pairs(tool._inputs) do
		inp:ConnectTo(nil)
	end
	for id, out in pairs(tool._outputs) do
		for inp in pairs(out._consumers) do
			inp._source = nil
		end
		out._consumers = {}
	end
	for i, t in ipairs(self._tools) do
		if t == tool then
			table.remove(self._tools, i)
			break
		end
	end
	self._byname[tool._name] = nil
	rawset(tool, "_deleted", true)
	-- Fusion removes a Paint node's strokes and unused modifiers with it.
	local again = true
	while again do
		again = false
		for _, t in ipairs(self._tools) do
			if t._regid == "PolylineStroke" or t._regid == "BezierSpline" then
				local used = false
				for _, out in pairs(t._outputs) do
					if next(out._consumers) then
						used = true
					end
				end
				if not used then
					self:_remove(t)
					again = true
					break
				end
			end
		end
	end
end

function CompMethods.AddTool(self, regid, x, y)
	return self:_add(regid, regid .. "1")
end
function CompMethods.FindTool(self, name)
	return self._byname[name]
end
function CompMethods.GetToolList(self, selected)
	local out = {}
	if selected then
		if self.ActiveTool then
			out[1] = self.ActiveTool
		end
		return out
	end
	for i, t in ipairs(self._tools) do
		out[i] = t
	end
	return out
end
function CompMethods.GetAttrs(self)
	return self._attrs
end
function CompMethods.GetPrefs(self, key)
	return self._prefs[key]
end
function CompMethods.StartUndo(self, name)
	self._undo_depth = self._undo_depth + 1
	Mock.undo[#Mock.undo + 1] = "start:" .. name
end
function CompMethods.EndUndo(self, keep)
	self._undo_depth = self._undo_depth - 1
	Mock.undo[#Mock.undo + 1] = "end:" .. tostring(keep)
end
function CompMethods.Lock(self)
	self._locked = self._locked + 1
end
function CompMethods.Unlock(self)
	self._locked = self._locked - 1
end

local function flatten(prefix, t, out)
	for k, v in pairs(t) do
		local key = prefix and (prefix .. "." .. k) or k
		if type(v) == "table" then
			flatten(key, v, out)
		else
			out[key] = v
		end
	end
end

function CompMethods.Paste(self, tbl)
	record("Paste")
	if type(tbl) ~= "table" or type(tbl.Tools) ~= "table" then
		return false
	end
	local rename, created = {}, {}
	for name, def in pairs(tbl.Tools) do
		local t = self:_add(def.__ctor, name)
		rename[name] = t._name
		created[name] = t
		rawset(t, "_def", def)
		if def.CustomData then
			flatten(nil, def.CustomData, t._data)
		end
		if def.ViewInfo and def.ViewInfo.Pos then
			t._pos = { def.ViewInfo.Pos[1], def.ViewInfo.Pos[2] }
		end
	end
	for name, def in pairs(tbl.Tools) do
		local t = created[name]
		for id, inp in pairs(def.Inputs or {}) do
			if inp.SourceOp then
				local src = created[inp.SourceOp] or self._byname[inp.SourceOp]
				if src then
					t[id]:ConnectTo(src[inp.Source or "Output"])
				end
			elseif inp.Value ~= nil then
				t[id]._value = type(inp.Value) == "table" and inp.Value.__ctor == "FuID" and inp.Value.value or inp.Value
			end
		end
	end
	return true
end

local function parse_range(r)
	local a, b = tostring(r):match("^(%-?%d+)%.%.(%-?%d+)$")
	return tonumber(a), tonumber(b)
end

function CompMethods.Render(self, opts)
	record("Render")
	local saver = opts.Tool
	if not saver or saver._regid ~= "Saver" then
		return false
	end
	if self._locked > 0 then
		return false
	end
	local a, b = parse_range(opts.FrameRange or "")
	a = a or opts.Start
	b = b or opts.End
	local fname = saver._def.Inputs.Clip.Value.Filename
	local stem = fname:gsub("%.png$", "")
	local src = saver.Input._source
	if not src then
		return false
	end
	for fr = a, b do
		local path = string.format("%s%04d.png", stem, fr)
		Mock.hooks.render(src._tool._name, fr, path)
	end
	return true
end

function CompMethods.GetPreviewList(self)
	return {
		LeftView = {
			ViewOn = function(_, tool)
				Mock.viewed = tool and tool._name
			end,
			View = { CurrentViewer = { SaveFile = function()
				return false
			end } },
		},
	}
end

function Mock.image_for(output, time)
	local info = Mock.hooks.image_info(output._tool._name)
	if not info then
		return nil
	end
	return { Width = info.width, Height = info.height, Metadata = { Filename = info.filename } }
end

-- bmd / fu ------------------------------------------------------------------------

function Mock.make_bmd(ui)
	return {
		readstring = readstring,
		fileexists = function(p)
			local f = io.open(p, "rb")
			if f then
				f:close()
				return true
			end
			return false
		end,
		direxists = function(p)
			local f = io.open(p .. "/.", "rb")
			if f then
				f:close()
				return true
			end
			return false
		end,
		createdir = function(p)
			os.execute("/bin/mkdir -p '" .. p:gsub("'", "'\\''") .. "'")
			return true
		end,
		readdir = function(pattern)
			local dir, glob = pattern:match("^(.*)/([^/]*)$")
			local out = {}
			local h = io.popen("/bin/ls -1 '" .. dir:gsub("'", "'\\''") .. "' 2>/dev/null")
			local lua_pat = "^" .. glob:gsub("([%.%-%+])", "%%%1"):gsub("%*", ".*") .. "$"
			for line in h:lines() do
				if line:match(lua_pat) then
					out[#out + 1] = { Name = line, IsDir = false }
				end
			end
			h:close()
			return out
		end,
		createuuid = function()
			return string.format("%08x-%04x", math.random(0, 0x7fffffff), math.random(0, 0xffff))
		end,
		UIDispatcher = function(u)
			return Mock.new_dispatcher(u)
		end,
		openfileexternal = function() end,
	}
end

-- UIManager ------------------------------------------------------------------------

local function element(kind)
	return function(self, props)
		props = props or {}
		props._kind = kind
		return props
	end
end

function Mock.new_ui()
	local ui = {}
	for _, k in ipairs({ "Label", "Button", "ComboBox", "Slider", "LineEdit", "CheckBox", "SpinBox", "DoubleSpinBox", "TextEdit", "ColorPicker", "HGroup", "VGroup" }) do
		ui[k] = element(k)
	end
	ui.HGap = function(self, a, b)
		return { _kind = "HGap" }
	end
	ui.VGap = function(self, a, b)
		return { _kind = "VGap" }
	end
	ui.Timer = function(self, props)
		local t = { ID = props.ID, running = false }
		t.Start = function(s)
			s.running = true
		end
		t.Stop = function(s)
			s.running = false
		end
		Mock.timer = t
		return t
	end
	ui.FindWindow = function()
		return nil
	end
	return ui
end

local function make_item(props)
	local it = props
	if props._kind == "ComboBox" then
		it._items = {}
		it.CurrentIndex = 0
		it.Clear = function(s)
			s._items = {}
			s.CurrentIndex = 0
		end
		it.AddItem = function(s, v)
			s._items[#s._items + 1] = v
		end
		it.AddItems = function(s, list)
			for _, v in ipairs(list) do
				s._items[#s._items + 1] = v
			end
		end
	end
	if it.Enabled == nil then
		it.Enabled = true
	end
	if it.Visible == nil then
		it.Visible = true
	end
	-- Like Qt, programmatic changes of index/value emit change events.
	local store = {}
	for k, v in pairs(it) do
		store[k] = v
	end
	for k in pairs(store) do
		it[k] = nil
	end
	local EVENTS = { CurrentIndex = "CurrentIndexChanged", Value = "ValueChanged" }
	return setmetatable(it, {
		__index = store,
		__newindex = function(t, k, v)
			local old = store[k]
			store[k] = v
			local ev = EVENTS[k]
			if ev and old ~= v and Mock.win and store.ID then
				local h = rawget(Mock.win.On, store.ID)
				h = h and h[ev]
				if h then
					h({})
				end
			end
		end,
	})
end

function Mock.new_dispatcher(ui)
	local disp = { On = {} }
	disp.AddWindow = function(self, props)
		local items = {}
		local function walk(node)
			if type(node) ~= "table" then
				return
			end
			for _, child in ipairs(node) do
				walk(child)
			end
			if node.ID then
				items[node.ID] = make_item(node)
			end
		end
		walk(props)
		local win = { _props = props }
		win.On = setmetatable({}, { __index = function(t, id)
			local e = {}
			rawset(t, id, e)
			return e
		end })
		win.GetItems = function()
			return items
		end
		win.Show = function() end
		win.Hide = function() end
		win.Raise = function() end
		win.RecalcLayout = function() end
		win.GetGeometry = function()
			return { 100, 100, 440, 780 }
		end
		Mock.win, Mock.items = win, items
		return win
	end
	disp.RunLoop = function(self)
		Mock.hooks.driver(Mock, self)
	end
	disp.ExitLoop = function(self)
		Mock.exited = true
	end
	Mock.disp = disp
	return disp
end

-- Test driver helpers ------------------------------------------------------------

function Mock.click(id)
	local h = Mock.win.On[id] and Mock.win.On[id].Clicked
	assert(h, "no Clicked handler for " .. id)
	h({})
end

function Mock.select(id, index)
	Mock.items[id].CurrentIndex = index
	local h = Mock.win.On[id] and Mock.win.On[id].CurrentIndexChanged
	if h then
		h({})
	end
end

function Mock.pump(timeout)
	local t0 = os.time()
	while Mock.timer and Mock.timer.running do
		Mock.disp.On.Timeout({ who = Mock.timer.ID })
		if os.time() - t0 > (timeout or 120) then
			error("timeout waiting for job")
		end
		os.execute("sleep 0.05")
	end
end

function Mock.close()
	Mock.win.On["MaxTracePlusWin"].Close({})
end

return Mock
