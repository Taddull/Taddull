-- Minimal JSON encode/decode for MaxTrace+ job, preset and settings files.
-- Lua 5.1 / LuaJIT compatible (Fusion's scripting runtime).

local json = {}

local escapes = { ['"'] = '\\"', ['\\'] = '\\\\', ['\b'] = '\\b', ['\f'] = '\\f', ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t' }

local function encode_string(s)
	return '"' .. s:gsub('[%c"\\]', function(c)
		return escapes[c] or string.format("\\u%04x", c:byte())
	end) .. '"'
end

local function is_array(t)
	local n = 0
	for k in pairs(t) do
		if type(k) ~= "number" or k < 1 or math.floor(k) ~= k then
			return false
		end
		n = n + 1
	end
	for i = 1, n do
		if t[i] == nil then
			return false
		end
	end
	return true, n
end

local function encode(v, indent, level)
	local t = type(v)
	if v == nil or v == json.null then
		return "null"
	elseif t == "boolean" then
		return v and "true" or "false"
	elseif t == "number" then
		if v ~= v or v == math.huge or v == -math.huge then
			error("cannot encode non-finite number")
		end
		if math.floor(v) == v and math.abs(v) < 1e15 then
			return string.format("%d", v)
		end
		return string.format("%.10g", v)
	elseif t == "string" then
		return encode_string(v)
	elseif t == "table" then
		level = level or 0
		local nl = indent and "\n" or ""
		local pad = indent and string.rep(indent, level + 1) or ""
		local endpad = indent and string.rep(indent, level) or ""
		local arr, n = is_array(v)
		local parts = {}
		if arr and n > 0 then
			for i = 1, n do
				parts[#parts + 1] = pad .. encode(v[i], indent, level + 1)
			end
			return "[" .. nl .. table.concat(parts, "," .. nl) .. nl .. endpad .. "]"
		end
		local keys = {}
		for k in pairs(v) do
			keys[#keys + 1] = tostring(k)
		end
		table.sort(keys)
		for _, k in ipairs(keys) do
			local val = v[k]
			if val == nil then
				val = v[tonumber(k)]
			end
			parts[#parts + 1] = pad .. encode_string(k) .. (indent and ": " or ":") .. encode(val, indent, level + 1)
		end
		if #parts == 0 then
			return arr and "[]" or "{}"
		end
		return "{" .. nl .. table.concat(parts, "," .. nl) .. nl .. endpad .. "}"
	end
	error("cannot encode value of type " .. t)
end

json.null = setmetatable({}, { __tostring = function() return "null" end })

function json.encode(v, pretty)
	return encode(v, pretty and "  " or nil, 0)
end

-- Decoder -------------------------------------------------------------------

local function decode_error(str, pos, msg)
	error(string.format("JSON error at %d: %s", pos, msg), 0)
end

local function skip(str, pos)
	local _, e = str:find("^[ \n\r\t]*", pos)
	return e + 1
end

local decode_value

local function decode_string(str, pos)
	local buf = {}
	local i = pos + 1
	while true do
		local c = str:sub(i, i)
		if c == "" then
			decode_error(str, i, "unterminated string")
		elseif c == '"' then
			return table.concat(buf), i + 1
		elseif c == "\\" then
			local n = str:sub(i + 1, i + 1)
			local map = { b = "\b", f = "\f", n = "\n", r = "\r", t = "\t", ['"'] = '"', ["\\"] = "\\", ["/"] = "/" }
			if map[n] then
				buf[#buf + 1] = map[n]
				i = i + 2
			elseif n == "u" then
				local hex = str:sub(i + 2, i + 5)
				local cp = tonumber(hex, 16)
				if not cp then
					decode_error(str, i, "bad unicode escape")
				end
				if cp < 0x80 then
					buf[#buf + 1] = string.char(cp)
				elseif cp < 0x800 then
					buf[#buf + 1] = string.char(0xC0 + math.floor(cp / 64), 0x80 + cp % 64)
				else
					buf[#buf + 1] = string.char(0xE0 + math.floor(cp / 4096), 0x80 + math.floor(cp / 64) % 64, 0x80 + cp % 64)
				end
				i = i + 6
			else
				decode_error(str, i, "bad escape")
			end
		else
			buf[#buf + 1] = c
			i = i + 1
		end
	end
end

local function decode_number(str, pos)
	local s, e = str:find("^-?%d+%.?%d*[eE]?[-+]?%d*", pos)
	if not s then
		decode_error(str, pos, "bad number")
	end
	local n = tonumber(str:sub(s, e))
	if not n then
		decode_error(str, pos, "bad number")
	end
	return n, e + 1
end

function decode_value(str, pos)
	pos = skip(str, pos)
	local c = str:sub(pos, pos)
	if c == "{" then
		local obj = {}
		pos = skip(str, pos + 1)
		if str:sub(pos, pos) == "}" then
			return obj, pos + 1
		end
		while true do
			pos = skip(str, pos)
			if str:sub(pos, pos) ~= '"' then
				decode_error(str, pos, "expected key")
			end
			local key
			key, pos = decode_string(str, pos)
			pos = skip(str, pos)
			if str:sub(pos, pos) ~= ":" then
				decode_error(str, pos, "expected ':'")
			end
			local val
			val, pos = decode_value(str, pos + 1)
			obj[key] = val
			pos = skip(str, pos)
			local d = str:sub(pos, pos)
			if d == "}" then
				return obj, pos + 1
			elseif d ~= "," then
				decode_error(str, pos, "expected ',' or '}'")
			end
			pos = pos + 1
		end
	elseif c == "[" then
		local arr = {}
		pos = skip(str, pos + 1)
		if str:sub(pos, pos) == "]" then
			return arr, pos + 1
		end
		while true do
			local val
			val, pos = decode_value(str, pos)
			arr[#arr + 1] = val
			pos = skip(str, pos)
			local d = str:sub(pos, pos)
			if d == "]" then
				return arr, pos + 1
			elseif d ~= "," then
				decode_error(str, pos, "expected ',' or ']'")
			end
			pos = pos + 1
		end
	elseif c == '"' then
		return decode_string(str, pos)
	elseif str:sub(pos, pos + 3) == "true" then
		return true, pos + 4
	elseif str:sub(pos, pos + 4) == "false" then
		return false, pos + 5
	elseif str:sub(pos, pos + 3) == "null" then
		return nil, pos + 4
	elseif c:match("[-%d]") then
		return decode_number(str, pos)
	end
	decode_error(str, pos, "unexpected character '" .. c .. "'")
end

function json.decode(str)
	if type(str) ~= "string" then
		error("JSON input must be a string", 0)
	end
	local v, pos = decode_value(str, 1)
	pos = skip(str, pos)
	if pos <= #str then
		decode_error(str, pos, "trailing data")
	end
	return v
end

return json
