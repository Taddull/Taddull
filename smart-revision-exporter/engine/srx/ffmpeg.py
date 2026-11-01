"""FFmpeg / FFprobe discovery and process management."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import threading
from typing import Callable, Dict, List, Optional, Sequence

MAC_PATHS = ["/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin"]


class ToolError(RuntimeError):
    pass


class Cancelled(Exception):
    pass


class CancelToken:
    """Cooperative cancellation shared by the whole job."""

    def __init__(self):
        self._event = threading.Event()
        self._procs: List[subprocess.Popen] = []
        self._lock = threading.Lock()
        self.reason = ""

    def cancel(self, reason: str = "cancelled by user") -> None:
        self.reason = reason
        self._event.set()
        with self._lock:
            for p in list(self._procs):
                _terminate(p)

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        if self._event.is_set():
            raise Cancelled(self.reason or "cancelled")

    def register(self, p: subprocess.Popen) -> None:
        with self._lock:
            self._procs.append(p)
            if self._event.is_set():
                _terminate(p)

    def unregister(self, p: subprocess.Popen) -> None:
        with self._lock:
            if p in self._procs:
                self._procs.remove(p)


def _terminate(p: subprocess.Popen) -> None:
    try:
        if p.poll() is None:
            p.send_signal(signal.SIGTERM)
    except Exception:
        pass


_TOOL_CACHE: Dict[str, str] = {}


def find_tool(name: str) -> str:
    if name in _TOOL_CACHE:
        return _TOOL_CACHE[name]
    env = os.environ.get(f"SRX_{name.upper()}")
    candidates = []
    if env:
        candidates.append(env)
    w = shutil.which(name)
    if w:
        candidates.append(w)
    candidates += [os.path.join(d, name) for d in MAC_PATHS]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            _TOOL_CACHE[name] = c
            return c
    raise ToolError(f"{name} not found. Install FFmpeg (e.g. 'brew install ffmpeg') or set SRX_{name.upper()}.")


def ffmpeg() -> str:
    return find_tool("ffmpeg")


def ffprobe() -> str:
    return find_tool("ffprobe")


def ffprobe_json(path: str, args: Sequence[str]) -> dict:
    cmd = [ffprobe(), "-v", "error", "-of", "json", *args, path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise ToolError(f"ffprobe failed on {path}: {r.stderr.strip()[-500:]}")
    return json.loads(r.stdout or "{}")


def version_info() -> dict:
    out = {}
    for tool in ("ffmpeg", "ffprobe"):
        try:
            p = find_tool(tool)
            r = subprocess.run([p, "-version"], capture_output=True, text=True)
            first = r.stdout.splitlines()[0] if r.stdout else ""
            m = re.search(r"version\s+(\S+)", first)
            out[tool] = {"path": p, "version": m.group(1) if m else first}
        except ToolError as e:
            out[tool] = {"error": str(e)}
    return out


def encoders() -> Dict[str, bool]:
    try:
        r = subprocess.run([ffmpeg(), "-hide_banner", "-encoders"], capture_output=True, text=True)
    except ToolError:
        return {}
    names = set()
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 6:
            names.add(parts[1])
    wanted = ["libx264", "aac", "aac_at", "h264_videotoolbox", "prores_ks", "pcm_s24le", "libfdk_aac"]
    return {w: (w in names) for w in wanted}


def supports_fps_mode() -> bool:
    try:
        r = subprocess.run([ffmpeg(), "-hide_banner", "-h", "full"], capture_output=True, text=True)
        return "-fps_mode" in r.stdout
    except Exception:
        return False


_FPS_MODE: Optional[bool] = None


def passthrough_args() -> List[str]:
    """Arguments that stop ffmpeg from duplicating/dropping frames."""
    global _FPS_MODE
    if _FPS_MODE is None:
        _FPS_MODE = supports_fps_mode()
    return ["-fps_mode", "passthrough"] if _FPS_MODE else ["-vsync", "passthrough"]


def run(cmd: Sequence[str], cancel: Optional[CancelToken] = None, log: Optional[Callable[[str], None]] = None,
        progress: Optional[Callable[[dict], None]] = None, cwd: Optional[str] = None) -> str:
    """Run an ffmpeg-like command, parse `-progress pipe:1` output if present.

    Returns captured stderr.  Raises ToolError on non-zero exit, Cancelled on
    cancellation.
    """
    cmd = list(cmd)
    if log:
        log("$ " + " ".join(_quote(c) for c in cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd,
                         stdin=subprocess.DEVNULL)
    if cancel:
        cancel.register(p)
    err_chunks: List[bytes] = []

    def _drain():
        for chunk in iter(lambda: p.stderr.read(65536), b""):
            err_chunks.append(chunk)

    t = threading.Thread(target=_drain, daemon=True)
    t.start()
    cur: dict = {}
    try:
        for raw in p.stdout:
            line = raw.decode("utf-8", "replace").strip()
            if "=" in line:
                k, v = line.split("=", 1)
                cur[k] = v
                if k == "progress":
                    if progress:
                        progress(dict(cur))
                    cur = {}
        p.wait()
    finally:
        t.join(timeout=5)
        if cancel:
            cancel.unregister(p)
    stderr = b"".join(err_chunks).decode("utf-8", "replace")
    if cancel and cancel.cancelled:
        raise Cancelled(cancel.reason)
    if p.returncode != 0:
        raise ToolError(f"{os.path.basename(cmd[0])} exited with {p.returncode}: {stderr.strip()[-2000:]}")
    return stderr


def _quote(s: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:=+,-]+", s):
        return s
    return "'" + s.replace("'", "'\\''") + "'"


class FrameReader:
    """Stream decoded raw frames from ffmpeg without loading the video."""

    def __init__(self, path: str, pix_fmt: str, width: int, height: int,
                 extra_input: Sequence[str] = (), vf: Optional[str] = None,
                 cancel: Optional[CancelToken] = None, stream: str = "0:v:0", threads: int = 0):
        self.frame_size = raw_frame_size(pix_fmt, width, height)
        cmd = [ffmpeg(), "-v", "error", "-nostdin", "-threads", str(threads), *extra_input, "-i", path,
               "-map", stream, "-an", "-sn", "-dn"]
        if vf:
            cmd += ["-vf", vf]
        cmd += [*passthrough_args(), "-f", "rawvideo", "-pix_fmt", pix_fmt, "-"]
        self.cmd = cmd
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     stdin=subprocess.DEVNULL, bufsize=0)
        self.cancel = cancel
        if cancel:
            cancel.register(self.proc)
        self._err: List[bytes] = []
        self._t = threading.Thread(target=self._drain, daemon=True)
        self._t.start()
        self.count = 0

    def _drain(self):
        for chunk in iter(lambda: self.proc.stderr.read(65536), b""):
            self._err.append(chunk)

    def read(self) -> Optional[bytes]:
        buf = bytearray(self.frame_size)
        view = memoryview(buf)
        got = 0
        while got < self.frame_size:
            n = self.proc.stdout.readinto(view[got:])
            if not n:
                break
            got += n
        if got == 0:
            return None
        if got != self.frame_size:
            raise ToolError(f"partial frame read ({got}/{self.frame_size} bytes) from decoder")
        self.count += 1
        return bytes(buf)

    def skip(self, n: int) -> int:
        done = 0
        for _ in range(n):
            if self.read() is None:
                break
            done += 1
        return done

    def close(self) -> str:
        """Stop the decoder early.  Returns only genuine decoder/demuxer messages;
        broken-pipe noise caused by the deliberate early stop is discarded."""
        try:
            if self.proc.poll() is None:
                self.proc.stdout.close()
                self.proc.terminate()
            self.proc.wait(timeout=30)
        except Exception:
            pass
        self._t.join(timeout=5)
        if self.cancel:
            self.cancel.unregister(self.proc)
        text = b"".join(self._err).decode("utf-8", "replace")
        keep = [ln for ln in text.splitlines() if _DECODER_MSG.search(ln)]
        return "\n".join(keep)

    def finish(self) -> str:
        """Wait for clean exit after the last frame; raise on decoder error."""
        rest = self.proc.stdout.read()
        if rest:
            raise ToolError("decoder produced trailing partial data")
        self.proc.wait()
        self._t.join(timeout=5)
        if self.cancel:
            self.cancel.unregister(self.proc)
        err = b"".join(self._err).decode("utf-8", "replace")
        if self.cancel and self.cancel.cancelled:
            raise Cancelled(self.cancel.reason)
        if self.proc.returncode != 0:
            raise ToolError(f"decoder failed ({self.proc.returncode}): {err[-1500:]}")
        return err


_DECODER_MSG = re.compile(r"\[(h264|hevc|prores|aac|mov,mp4[^ ]*|mp3|pcm_[a-z0-9]+|dnxhd|rawvideo @ 0x[0-9a-f]+\] (?!Error submitting))[^\]]*@")


def raw_frame_size(pix_fmt: str, w: int, h: int) -> int:
    cw2 = (w + 1) // 2
    ch2 = (h + 1) // 2
    table = {
        "yuv420p": w * h + 2 * cw2 * ch2,
        "yuvj420p": w * h + 2 * cw2 * ch2,
        "yuv422p": w * h + 2 * cw2 * h,
        "yuvj422p": w * h + 2 * cw2 * h,
        "yuv444p": 3 * w * h,
        "yuvj444p": 3 * w * h,
        "gray": w * h,
        "yuv420p10le": 2 * (w * h + 2 * cw2 * ch2),
        "yuv422p10le": 2 * (w * h + 2 * cw2 * h),
        "yuv444p10le": 6 * w * h,
        "gray10le": 2 * w * h,
    }
    if pix_fmt not in table:
        raise ToolError(f"unsupported pixel format for verification: {pix_fmt}")
    return table[pix_fmt]


def plane_layout(pix_fmt: str, w: int, h: int):
    """Return list of (offset, width, height, bytes_per_sample) for each plane."""
    bps = 2 if "10" in pix_fmt else 1
    cw2 = (w + 1) // 2
    ch2 = (h + 1) // 2
    if pix_fmt.startswith("gray"):
        return [(0, w, h, bps)]
    if "420" in pix_fmt:
        cw, ch = cw2, ch2
    elif "422" in pix_fmt:
        cw, ch = cw2, h
    else:
        cw, ch = w, h
    y = w * h * bps
    c = cw * ch * bps
    return [(0, w, h, bps), (y, cw, ch, bps), (y + c, cw, ch, bps)]
