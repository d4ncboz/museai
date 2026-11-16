#!/usr/bin/env python3
"""Keep the muse accounts busy: top the gateway up to ``--target`` active tasks, forever.

  python scripts/feeder.py [--target 10] [--url http://127.0.0.1:18610] [--spool DIR] [--interval 15]

Every ``--interval`` seconds it counts the gateway's running + queued tasks. Below the target it starts
more work, in this order:
  1. a line from a job file in the spool (default ``~/.config/museai/feeder``): ``*.txt``, one shell
     command per line (``scripts/shot ...``, ``muse-video ...``; ``#`` comments skipped). A line is
     taken once (its file is rewritten without it) and run with bash from the repo root.
  2. a failed video task, retried through ``POST /dashboard/videos/{id}/retry`` (at most
     ``--max-retries`` times per task; a duplicate the gateway refuses with 400 is skipped for good).
Free accounts get work at once: the gateway hands a task to the next free account the moment one
releases, so a full queue is all that is needed. When the machine reports ``overloaded`` the feeder
only keeps one task per active account (never below) instead of the full target.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def say(msg: str) -> None:
    print(f"{datetime.now():%H:%M:%S} feeder: {msg}", flush=True)


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as res:
        return json.load(res)


def post(url: str, key: str) -> int:
    req = urllib.request.Request(url, method="POST", headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status
    except urllib.error.HTTPError as exc:
        return exc.code


def take_line(spool: Path) -> str | None:
    """Pop the first job line of the oldest spool file."""
    for path in sorted(spool.glob("*.txt")):
        lines = path.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.strip() and not line.lstrip().startswith("#"):
                path.write_text("\n".join(lines[:i] + lines[i + 1:]) + "\n")
                return line.strip()
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=int, default=10)
    ap.add_argument("--url", default="http://127.0.0.1:18610")
    ap.add_argument("--spool", type=Path, default=Path.home() / ".config/museai/feeder")
    ap.add_argument("--key-file", type=Path, default=ROOT / "data/api_key")
    ap.add_argument("--interval", type=float, default=15)
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--ignore-overload", action="store_true", help="keep the full target even when the Mac is overloaded")
    args = ap.parse_args()
    args.spool.mkdir(parents=True, exist_ok=True)
    key = args.key_file.read_text().strip()
    procs: list[tuple[subprocess.Popen, float]] = []
    retried: dict[str, int] = {}
    say(f"target {args.target}, spool {args.spool}")
    while True:
        try:
            data = get(f"{args.url}/dashboard/data")
        except (OSError, ValueError) as exc:
            say(f"gateway not reachable ({exc}); waiting")
            time.sleep(args.interval)
            continue
        procs = [(p, t) for p, t in procs if p.poll() is None]
        active = sum(v["status"] in ("running", "queued") for v in data["videos"])
        # a job just started has not reached the gateway yet: count it until it has had time to submit
        submitting = sum(time.time() - t < 45 for _, t in procs)
        ready = sum(a["status"] == "active" and a.get("enabled", True) for a in data["accounts"])
        goal = args.target
        if not args.ignore_overload and data.get("system", {}).get("level") == "overloaded":
            goal = max(ready, 1)
        failed = [v for v in data["videos"] if v["status"] == "failed"
                  and retried.get(v["id"], 0) < args.max_retries]
        started = 0
        while active + submitting + started < goal:
            line = take_line(args.spool)
            if line:
                procs.append((subprocess.Popen(line, shell=True, cwd=ROOT, executable="/bin/bash"), time.time()))
                say(f"job: {line[:90]}")
            elif failed:
                v = failed.pop(0)
                code = post(f"{args.url}/dashboard/videos/{v['id']}/retry", key)
                retried[v["id"]] = retried.get(v["id"], 0) + 1 if code == 200 else args.max_retries
                say(f"retry {v['id']} -> {code}")
                if code != 200:
                    continue
            else:
                break
            started += 1
        say(f"active {active}, started {started}, ready accounts {ready}, goal {goal}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
