"""Colab render queue (github.com/lvluu/muse-renderer) for the dashboard: is the GPU worker up, what is queued."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

STATES = ("queue", "running", "done", "failed")
# server.json older than this and the worker counts as gone (it writes one every poll).
ONLINE_SECONDS = 60
RECENT = 10
LOG_TAIL = 1500
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _jobs(root: Path, state: str) -> list[Path]:
    return sorted(
        (p for p in (root / state).iterdir() if p.is_dir() and not p.name.endswith(".part")),
        key=lambda p: p.name,
    )


def job_files(job: Path) -> list[str]:
    """Output files of a finished job: everything but its bookkeeping and the inputs it was sent."""
    skip = {"job.json", "result.json", *(_json(job / "job.json").get("inputs") or {})}
    return sorted(p.name for p in job.iterdir() if p.is_file() and p.name not in skip)


def job_file(root: str, job_id: str, name: str) -> Path | None:
    """A file of a done or failed job, or None unless both names are plain and the file is inside it."""
    if not root or not SAFE_NAME.match(job_id) or not SAFE_NAME.match(name) or ".." in job_id + name:
        return None
    for state in ("done", "failed"):
        job = (Path(root).expanduser() / state / job_id).resolve()
        path = (job / name).resolve()
        if path.parent == job and path.is_file():
            return path
    return None


def renderer_status(path: str) -> dict[str, Any]:
    """Queue counts, recent jobs and worker heartbeat; never raises."""
    try:
        root = Path(path).expanduser()
        if not root.is_dir():
            return {"configured": True, "error": f"{root} is not a folder: is Google Drive mounted?"}
        jobs: dict[str, list[Path]] = {s: _jobs(root, s) if (root / s).is_dir() else [] for s in STATES}
        recent = sorted(((p, s) for s, ps in jobs.items() for p in ps), key=lambda x: x[0].name, reverse=True)
        out_jobs = []
        for job, state in recent[:RECENT]:
            res = _json(job / "result.json")
            item: dict[str, Any] = {"id": job.name, "state": state,
                                    "seconds": res.get("seconds"), "rc": res.get("rc")}
            if state == "failed":
                try:
                    item["log"] = (job / "log.txt").read_text(errors="replace")[-LOG_TAIL:]
                except OSError:
                    item["log"] = ""
            if state == "done":
                item["files"] = job_files(job)
            out_jobs.append(item)
        srv = _json(root / "server.json")
        ts = srv.get("ts")
        online = isinstance(ts, (int, float)) and 0 <= time.time() - ts < ONLINE_SECONDS
        runtime = srv.get("runtime")
        beat = root / "server.json"
        return {
            "configured": True,
            **({"error": "server.json is not readable JSON"} if beat.exists() and not srv else {}),
            "counts": {s: len(ps) for s, ps in jobs.items()},
            "jobs": out_jobs,
            "online": online,
            "host": srv.get("host"),
            "runtime": runtime,
            "colab_url": srv.get("colab_url"),
            "job": srv.get("job"),
            "state": "offline" if not online else "online" if runtime == "up" else "idle",
        }
    except Exception as exc:  # the dashboard must load whatever state the Drive is in
        return {"configured": True, "error": f"{type(exc).__name__}: {exc}"}
