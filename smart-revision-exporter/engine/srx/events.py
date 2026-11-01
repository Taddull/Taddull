"""Progress/event reporting.

In --json mode every event is one JSON object per line on stdout; the SwiftUI
app parses this stream.  Otherwise events are printed human-readably to stderr.
"""

from __future__ import annotations

import json

from . import jsonutil
import os
import subprocess
import sys
import threading
import time
from typing import Optional


class Emitter:
    def __init__(self, json_mode: bool = False, log_path: Optional[str] = None, quiet: bool = False):
        self.json_mode = json_mode
        self.quiet = quiet
        self._lock = threading.Lock()
        self._log = open(log_path, "a", encoding="utf-8") if log_path else None
        self._stage_start = {}
        self._last_progress = 0.0
        self._stats_thread = None
        self._stop = threading.Event()
        self.cancel = None

    def attach_log(self, path: str) -> None:
        with self._lock:
            if self._log:
                self._log.close()
            self._log = open(path, "a", encoding="utf-8")

    def _write(self, obj: dict) -> None:
        obj.setdefault("ts", round(time.time(), 3))
        line = jsonutil.dumps(obj)
        with self._lock:
            if self._log:
                self._log.write(line + "\n")
                self._log.flush()
            if self.json_mode:
                sys.stdout.write(line + "\n")
                sys.stdout.flush()
            elif not self.quiet:
                t = obj.get("type")
                if t == "progress":
                    msg = f"[{obj['stage']}] {obj['fraction'] * 100:5.1f}%"
                    if obj.get("message"):
                        msg += " " + obj["message"]
                    if obj.get("eta_s") is not None:
                        msg += f" (eta {obj['eta_s']:.0f}s)"
                    sys.stderr.write(msg + "\n")
                elif t in ("log", "warning", "error"):
                    sys.stderr.write(f"{t.upper() if t != 'log' else ''}{': ' if t != 'log' else ''}{obj.get('message')}\n")
                elif t == "stage":
                    sys.stderr.write(f"== {obj.get('stage')}: {obj.get('message', '')}\n")

    def emit(self, type_: str, **fields) -> None:
        fields["type"] = type_
        self._write(fields)

    def stage(self, stage: str, message: str = "") -> None:
        self._stage_start[stage] = time.time()
        self.emit("stage", stage=stage, message=message)

    def progress(self, stage: str, fraction: float, message: str = "") -> None:
        now = time.time()
        fraction = max(0.0, min(1.0, fraction))
        if fraction < 1.0 and now - self._last_progress < 0.25:
            return
        self._last_progress = now
        start = self._stage_start.setdefault(stage, now)
        eta = None
        if 0.03 < fraction < 1.0 and now - start > 1.0:
            eta = (now - start) / fraction * (1 - fraction)
        self.emit("progress", stage=stage, fraction=round(fraction, 4), message=message,
                  eta_s=round(eta, 1) if eta is not None else None)

    def log(self, message: str) -> None:
        self.emit("log", message=message)

    def warn(self, message: str) -> None:
        self.emit("warning", message=message)

    def error(self, message: str, code: str = "error", **extra) -> None:
        self.emit("error", message=message, code=code, **extra)

    def result(self, payload: dict) -> None:
        self.emit("result", **payload)

    # ---- resource statistics -------------------------------------------------
    def start_stats(self, interval: float = 2.0) -> None:
        if self._stats_thread is not None:
            return

        def loop():
            last_cpu = _self_cpu()
            last_t = time.time()
            while not self._stop.wait(interval):
                now = time.time()
                cpu = _self_cpu()
                pids = []
                if self.cancel is not None:
                    try:
                        pids = [p.pid for p in list(self.cancel._procs) if p.poll() is None]
                    except Exception:
                        pids = []
                child_cpu, child_rss = _ps(pids)
                self.emit("stats",
                          engine_cpu_percent=round(100.0 * (cpu - last_cpu) / max(1e-6, now - last_t), 1),
                          child_cpu_percent=round(child_cpu, 1),
                          engine_rss_mb=round(_self_rss_mb(), 1),
                          child_rss_mb=round(child_rss, 1),
                          load_avg=os.getloadavg()[0] if hasattr(os, "getloadavg") else None,
                          active_processes=len(pids))
                last_cpu, last_t = cpu, now

        self._stats_thread = threading.Thread(target=loop, daemon=True)
        self._stats_thread.start()

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            if self._log:
                self._log.close()
                self._log = None


def _self_cpu() -> float:
    t = os.times()
    return t.user + t.system


def _self_rss_mb() -> float:
    try:
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024
    except Exception:
        return 0.0


def _ps(pids) -> tuple:
    if not pids:
        return 0.0, 0.0
    try:
        out = subprocess.run(["ps", "-o", "%cpu=,rss=", "-p", ",".join(str(p) for p in pids)],
                             capture_output=True, text=True, timeout=5).stdout
        cpu = rss = 0.0
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                cpu += float(parts[0])
                rss += float(parts[1]) / 1024
        return cpu, rss
    except Exception:
        return 0.0, 0.0
