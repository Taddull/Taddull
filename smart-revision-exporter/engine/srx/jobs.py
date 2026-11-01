"""Job directories, recoverable manifests, atomic output and revision history."""

from __future__ import annotations

import datetime
import json
import os
import shutil
import sys
import uuid

from . import jsonutil
from typing import List, Optional


def app_support_dir() -> str:
    env = os.environ.get("SRX_HOME")
    if env:
        return env
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Smart Revision Exporter")
    base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(base, "smart-revision-exporter")


def _atomic_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        jsonutil.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class Job:
    def __init__(self, kind: str, params: dict, root: Optional[str] = None):
        self.root = root or os.path.join(app_support_dir(), "jobs")
        os.makedirs(self.root, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.id = f"{stamp}-{uuid.uuid4().hex[:6]}"
        self.dir = os.path.join(self.root, self.id)
        self.tmp_dir = os.path.join(self.dir, "tmp")
        os.makedirs(self.tmp_dir)
        self.manifest_path = os.path.join(self.dir, "job.json")
        self.log_path = os.path.join(self.dir, "log.jsonl")
        self.data = {
            "id": self.id,
            "kind": kind,
            "state": "running",
            "pid": os.getpid(),
            "created": datetime.datetime.now().isoformat(),
            "params": params,
            "steps": [],
            "resolve_render_jobs": [],
            "partial_output": None,
            "final_output": None,
        }
        self.save()

    def save(self) -> None:
        self.data["updated"] = datetime.datetime.now().isoformat()
        _atomic_json(self.manifest_path, self.data)

    def step(self, name: str, **info) -> None:
        self.data["steps"].append({"name": name, "at": datetime.datetime.now().isoformat(), **info})
        self.save()

    def set(self, **kv) -> None:
        self.data.update(kv)
        self.save()

    def add_resolve_job(self, job_id: str) -> None:
        self.data["resolve_render_jobs"].append(job_id)
        self.save()

    def tmp(self, name: str) -> str:
        return os.path.join(self.tmp_dir, name)

    def finish(self, state: str, keep_temp: bool = False, **kv) -> None:
        self.data.update(kv)
        self.data["state"] = state
        self.data["finished"] = datetime.datetime.now().isoformat()
        if not keep_temp and os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
            self.data["temp_removed"] = True
        self.save()


def partial_path_for(final_path: str, job_id: str) -> str:
    d, name = os.path.split(os.path.abspath(final_path))
    stem, ext = os.path.splitext(name)
    return os.path.join(d, f".{stem}.srx-partial-{job_id}{ext or '.mp4'}")


def commit_output(partial: str, final: str) -> None:
    """Move the verified partial file into place without ever overwriting."""
    if os.path.exists(final):
        raise FileExistsError(f"refusing to overwrite existing file: {final}")
    try:
        os.link(partial, final)      # fails atomically if `final` appears meanwhile
        os.unlink(partial)
    except (OSError, NotImplementedError) as e:
        if isinstance(e, FileExistsError):
            raise
        if os.path.exists(final):
            raise FileExistsError(f"refusing to overwrite existing file: {final}")
        os.rename(partial, final)


def check_disk_space(path: str, needed_bytes: int) -> Optional[str]:
    d = os.path.dirname(os.path.abspath(path)) or "."
    try:
        free = shutil.disk_usage(d).free
    except OSError:
        return None
    if free < needed_bytes:
        return (f"not enough disk space in {d}: {free / 1e9:.2f} GB free, about "
                f"{needed_bytes / 1e9:.2f} GB needed")
    return None


def list_jobs(root: Optional[str] = None) -> List[dict]:
    root = root or os.path.join(app_support_dir(), "jobs")
    out = []
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name, "job.json")
        try:
            with open(p) as f:
                d = json.load(f)
            d["dir"] = os.path.join(root, name)
            out.append(d)
        except Exception:
            continue
    return out


def recover_jobs(root: Optional[str] = None, cleanup: bool = True) -> List[dict]:
    """Find jobs that were interrupted (crash, force quit) and clean them up.

    The original master is never touched by a job, so recovery only removes
    temporary renders and orphaned partial outputs and reports Resolve render
    jobs that may need deleting.
    """
    recovered = []
    for d in list_jobs(root):
        if d.get("state") != "running" or _pid_alive(int(d.get("pid", 0))):
            continue
        info = {"id": d["id"], "dir": d["dir"], "removed": [],
                "resolve_render_jobs": d.get("resolve_render_jobs", [])}
        if cleanup:
            tmp = os.path.join(d["dir"], "tmp")
            if os.path.isdir(tmp):
                shutil.rmtree(tmp, ignore_errors=True)
                info["removed"].append(tmp)
            part = d.get("partial_output")
            if part and os.path.exists(part):
                os.unlink(part)
                info["removed"].append(part)
            d["state"] = "interrupted"
            d["recovered"] = datetime.datetime.now().isoformat()
            dd = dict(d)
            dd.pop("dir", None)
            _atomic_json(os.path.join(d["dir"], "job.json"), dd)
        recovered.append(info)
    return recovered


class ProjectStore:
    """Revision history keyed by the fingerprint of the ORIGINAL approved master.

    Each cycle records its base file, revisions, output and verification
    result.  Approving an output makes it the base of the next cycle; unchanged
    packets keep being copied (never re-encoded), so repeated cycles do not
    accumulate generation loss.
    """

    def __init__(self, root: Optional[str] = None):
        self.root = root or os.path.join(app_support_dir(), "projects")
        os.makedirs(self.root, exist_ok=True)

    def _path(self, original_fp: str) -> str:
        return os.path.join(self.root, f"{original_fp}.json")

    def find(self, fingerprint: str) -> Optional[dict]:
        """Return the project whose original or any cycle output has this fingerprint."""
        for name in os.listdir(self.root):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(self.root, name)) as f:
                d = json.load(f)
            if d["original"]["fingerprint"] == fingerprint:
                return d
            for c in d["cycles"]:
                if c.get("output", {}).get("fingerprint") == fingerprint:
                    return d
        return None

    def ensure(self, master_path: str, fingerprint: str) -> dict:
        d = self.find(fingerprint)
        if d is not None:
            return d
        d = {"original": {"path": os.path.abspath(master_path), "fingerprint": fingerprint,
                          "registered": datetime.datetime.now().isoformat()},
             "cycles": []}
        _atomic_json(self._path(fingerprint), d)
        return d

    def record_cycle(self, project: dict, base_path: str, base_fp: str, output_path: str, output_fp: str,
                     revisions: list, report_path: str, status: str, mode: str) -> dict:
        cyc = {"cycle": len(project["cycles"]) + 1, "created": datetime.datetime.now().isoformat(),
               "base": {"path": os.path.abspath(base_path), "fingerprint": base_fp},
               "output": {"path": os.path.abspath(output_path), "fingerprint": output_fp},
               "revisions": revisions, "report": report_path, "verification": status, "mode": mode,
               "approved": False}
        project["cycles"].append(cyc)
        _atomic_json(self._path(project["original"]["fingerprint"]), project)
        return cyc

    def approve(self, output_fp: str) -> dict:
        d = self.find(output_fp)
        if d is None:
            raise KeyError("output not found in any project history")
        for c in d["cycles"]:
            if c["output"]["fingerprint"] == output_fp:
                if c["verification"] != "passed":
                    raise ValueError("only verified outputs can be approved")
                c["approved"] = True
                c["approved_at"] = datetime.datetime.now().isoformat()
        _atomic_json(self._path(d["original"]["fingerprint"]), d)
        return d
