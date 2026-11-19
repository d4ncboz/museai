#!/usr/bin/env python3
"""Heavy steps on the Colab render queue (github.com/lvluu/muse-renderer) instead of this machine.

  remote.py online                     print the render server's host (exit 0), or why not (stderr, exit 1)
  remote.py ace OUT.wav SCRIPT ARGS..  run an ACE-Step script of museai (path relative to the museai root,
                                       e.g. .claude/skills/healing-video/scripts/ace_piano.py) on the Colab GPU
                                       with ARGS + --out; OUT.wav comes back here. Exit 1 when the job failed.

Online = MUSE_RENDER_DRIVE set, the CLI at MUSE_RENDERER (default ~/dev/muse-renderer/muse-renderer) and a
server.json heartbeat under 60 s old. The job runs the museai main checkout on the runtime: push a script
change before a remote job needs it. --ref FILE goes up with the job.
"""

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RENDERER = Path(os.environ.get("MUSE_RENDERER", "~/dev/muse-renderer/muse-renderer")).expanduser()


def online():
    drive = os.environ.get("MUSE_RENDER_DRIVE")
    if not drive:
        return None, "MUSE_RENDER_DRIVE not set"
    if not os.access(RENDERER, os.X_OK):
        return None, f"muse-renderer not found at {RENDERER}"
    try:
        beat = json.loads((Path(drive).expanduser() / "server.json").read_text())
    except (OSError, ValueError):
        return None, "render server offline"
    if time.time() - beat.get("ts", 0) >= 60:
        return None, "render server offline"
    return beat.get("host") or "?", None


def ace(out, script, args, minutes=90):
    args, files = list(args), []
    if "--ref" in args:  # the reference recording travels with the job, by its name
        i = args.index("--ref") + 1
        files.append(args[i])
        args[i] = Path(args[i]).name
    cmd = 'bash "$MUSEAI/.claude/skills/muse-video/scripts/ace_colab.sh" ' + shlex.join(
        [script, *args, "--out", "ace.wav"]
    )
    jid = subprocess.run(
        [str(RENDERER), "submit", "-n", "music", *files, "--", cmd],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        # --clean: a done job's folder (inputs, log, output) leaves the drive once the wav is here
        rc = subprocess.run(
            [str(RENDERER), "wait", jid, "-o", tmp, "-t", str(minutes), "--clean"]
        ).returncode
        if rc != 0 or not (Path(tmp) / "ace.wav").is_file():
            print(f"remote: job {jid} gave no music (rc={rc})", file=sys.stderr)
            return 1
        shutil.move(str(Path(tmp) / "ace.wav"), out)
    return 0


def main(argv):
    if argv[:1] == ["online"]:
        host, why = online()
        print(host or why, file=sys.stdout if host else sys.stderr)
        return 0 if host else 1
    if argv[:1] == ["ace"] and len(argv) >= 3:
        return ace(argv[1], argv[2], argv[3:])
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
