"""Serialise Python data to Lua table literals (read by the Fusion launcher)."""

from __future__ import annotations

import math
import re
from typing import Any

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LUA_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function", "if", "in",
    "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while", "goto",
}


def lua_string(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif o < 32 or o == 127:
            out.append("\\%03d" % o)
        else:
            out.append(ch)
    out.append('"')
    # Lua 5.1 strings are byte strings; UTF-8 passes through unchanged.
    return "".join(out)


def lua_number(v: float) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if not math.isfinite(v):
        raise ValueError("non-finite number cannot be serialised")
    if float(v).is_integer() and abs(v) < 1e15:
        return str(int(v))
    return "%.10g" % v


def lua_key(k: Any) -> str:
    if isinstance(k, str):
        if _IDENT.match(k) and k not in _LUA_KEYWORDS:
            return k
        return "[" + lua_string(k) + "]"
    if isinstance(k, (int, float)) and not isinstance(k, bool):
        return "[" + lua_number(k) + "]"
    raise TypeError(f"unsupported key {k!r}")


def to_lua(v: Any, indent: int = 0) -> str:
    pad = "\t" * indent
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return lua_number(v)
    if isinstance(v, str):
        return lua_string(v)
    if isinstance(v, (list, tuple)):
        if not v:
            return "{}"
        inner = ",\n".join(pad + "\t" + to_lua(x, indent + 1) for x in v)
        return "{\n" + inner + ",\n" + pad + "}"
    if isinstance(v, dict):
        if not v:
            return "{}"
        items = []
        for k, x in v.items():
            if x is None:
                continue
            items.append(pad + "\t" + lua_key(k) + " = " + to_lua(x, indent + 1))
        return "{\n" + ",\n".join(items) + ",\n" + pad + "}"
    if hasattr(v, "tolist"):
        return to_lua(v.tolist(), indent)
    raise TypeError(f"unsupported value {type(v)!r}")
