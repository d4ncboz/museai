#!/usr/bin/env python3
"""Heavy steps on the Colab render queue (github.com/lvluu/muse-renderer) instead of this machine.

  remote.py online                     print the render server's host (exit 0), or why not (stderr, exit 1)
  remote.py drive                      print the render queue's Drive folder (exit 1 when none is known)
  remote.py ace OUT.wav SCRIPT ARGS..  run an ACE-Step script of museai (path relative to the museai root,
                                       e.g. .claude/skills/healing-video/scripts/ace_piano.py) on the Colab GPU
                                       with ARGS + --out; OUT.wav comes back here. Exit 1 when the job failed.
Also imported: speakers.py (lip-sync QA) and healing-longform/longform.py (compose) run on the runtime
through speakers() / compose() while it is online (SPEAKERS_REMOTE=0 / LONGFORM_REMOTE=0 keep them here).

Drive folder = MUSE_RENDER_DRIVE, else the --root of the worker service installed on this machine
(`muse-renderer install-service`): agent sessions and launchd jobs do not read ~/.zshrc, so the env var
alone sent their renders to this Mac (2026-11-19: a local ACE render while the queue was up).
Online = a drive folder, the CLI at MUSE_RENDERER (default ~/dev/muse-renderer/muse-renderer) and a
server.json heartbeat under 60 s old. The job runs the museai main checkout on the runtime: push a script
change before a remote job needs it. --ref FILE goes up with the job.
"""

import contextlib
import json
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

RENDERER = Path(os.environ.get("MUSE_RENDERER", "~/dev/muse-renderer/muse-renderer")).expanduser()


def _service_root():
    try:
        plist = Path.home() / "Library/LaunchAgents/com.muse-renderer.worker.plist"
        if plist.is_file():
            args = plistlib.loads(plist.read_bytes()).get("ProgramArguments", [])
        else:
            unit = (Path.home() / ".config/systemd/user/muse-renderer.service").read_text()
            line = next(ln for ln in unit.splitlines() if ln.startswith("ExecStart="))
            args = shlex.split(line.split("=", 1)[1])
        return args[args.index("--root") + 1]
    except (OSError, ValueError, StopIteration, IndexError, plistlib.InvalidFileException):
        return None


def drive():
    d = os.environ.get("MUSE_RENDER_DRIVE") or _service_root()
    if d:
        os.environ["MUSE_RENDER_DRIVE"] = d  # for the muse-renderer CLI this script calls
    return d


def online():
    if not drive():
        return None, "MUSE_RENDER_DRIVE not set and no muse-renderer service installed"
    if not os.access(RENDERER, os.X_OK):
        return None, f"muse-renderer not found at {RENDERER}"
    try:
        beat = json.loads((Path(os.environ["MUSE_RENDER_DRIVE"]).expanduser() / "server.json").read_text())
    except (OSError, ValueError):
        return None, "render server offline"
    if time.time() - beat.get("ts", 0) >= 60:
        return None, "render server offline"
    return beat.get("host") or "?", None


@contextlib.contextmanager
def job(name, files, cmd, minutes=180):
    """Run CMD (bash, in a folder holding FILES by name; $MUSEAI = the museai main checkout) on the render queue.
    Yields (folder with the job's new files and log.txt, rc); the folder goes when the block ends. --clean: a
    done job leaves the drive once its files are here (a failed one stays in failed/ to look at)."""
    jid = subprocess.run(
        [str(RENDERER), "submit", "-n", name, *map(str, files), "--", cmd],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        # the CLI's progress lines go to stderr: callers parse this process's stdout (check_clip.sh)
        rc = subprocess.run(
            [str(RENDERER), "wait", jid, "-o", tmp, "-t", str(minutes), "--clean"], stdout=sys.stderr
        ).returncode
        yield Path(tmp), rc


def ace(out, script, args, minutes=90):
    args, files = list(args), []
    if "--ref" in args:  # the reference recording travels with the job, by its name
        i = args.index("--ref") + 1
        files.append(args[i])
        args[i] = Path(args[i]).name
    cmd = 'bash "$MUSEAI/.claude/skills/muse-video/scripts/ace_colab.sh" ' + shlex.join(
        [script, *args, "--out", "ace.wav"]
    )
    with job("music", files, cmd, minutes) as (tmp, rc):
        if rc != 0 or not (tmp / "ace.wav").is_file():
            print(f"remote: music job gave no music (rc={rc})", file=sys.stderr)
            return 1
        shutil.move(str(tmp / "ace.wav"), out)
    return 0


SPEAKERS_DEPS = "--python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless==4.10.0.84 --with librosa"


def speakers(argv):
    """speakers.py on the Colab runtime (mediapipe + librosa there): same args, same stdout, mouths sheet and
    REPORT come back, same exit code. None when the job itself failed (the caller then runs it here)."""
    video, a2, a3, sheet = argv[0], argv[1], argv[2], argv[-1]
    files = [video, a2] + ([a3] if Path(a3).is_file() else [])
    names = [Path(video).name, Path(a2).name, Path(a3).name if Path(a3).is_file() else a3]
    env = " ".join(f"{k}={shlex.quote(os.environ[k])}" for k in ("FEMALE", "LEFT") if k in os.environ)
    # speakers.py exits 1 on a failed line, a verdict: rc.txt carries it so the job itself counts as done
    cmd = (
        "command -v uv >/dev/null || pip install -q uv; "
        # Colab's kernel env names its inline matplotlib backend, which mediapipe's import rejects outside a notebook
        f"{env} MPLBACKEND=Agg REPORT=report.json uv run -q --no-project {SPEAKERS_DEPS} python "
        '"$MUSEAI/.claude/skills/muse-video/scripts/speakers.py" '
        + shlex.join([*names, "mouths.jpg"])
        + "; echo $? > rc.txt"
    )
    with job("speakers", files, cmd, 30) as (tmp, rc):
        # no report.json: speakers.py crashed before its verdict (an env problem there, not a line that failed)
        if rc != 0 or not (tmp / "rc.txt").is_file() or not (tmp / "report.json").is_file():
            sys.stderr.write((tmp / "log.txt").read_text()[-1500:] if (tmp / "log.txt").is_file() else "")
            return None
        sys.stdout.write((tmp / "log.txt").read_text())
        if (tmp / "mouths.jpg").is_file():
            shutil.move(str(tmp / "mouths.jpg"), sheet)
        if os.environ.get("REPORT"):
            shutil.move(str(tmp / "report.json"), os.environ["REPORT"])
        return int((tmp / "rc.txt").read_text().strip() or 1)


def compose(root, files, assets, cmd, out, minutes=240):
    """A longform compose on the Colab runtime: FILES (paths under ROOT) and ASSETS (name -> local path) go up
    as one tar (w/ and w/_assets there), CMD runs in the job folder and writes out.mp4, which lands at OUT.
    The segment cache (build/) is not sent: the runtime rebuilds every segment. 0 = OUT written."""
    with tempfile.TemporaryDirectory() as t:
        tar = Path(t) / "in.tar"
        with tarfile.open(tar, "w") as tf:
            for f in files:
                tf.add(f, arcname=str(Path(f).relative_to(root)))
            for name, src in assets.items():
                tf.add(src, arcname=f"_assets/{name}")
        with job("compose", [tar], f"mkdir w && tar xf in.tar -C w && {cmd}", minutes) as (tmp, rc):
            log = tmp / "log.txt"
            if log.is_file():
                sys.stdout.write(log.read_text()[-3000:])
            if rc != 0 or not (tmp / "out.mp4").is_file():
                print(f"remote: compose job gave no video (rc={rc})", file=sys.stderr)
                return 1
            shutil.move(str(tmp / "out.mp4"), out)
    return 0


def main(argv):
    if argv[:1] == ["online"]:
        host, why = online()
        print(host or why, file=sys.stdout if host else sys.stderr)
        return 0 if host else 1
    if argv[:1] == ["drive"]:
        d = drive()
        if d:
            print(d)
        return 0 if d else 1
    if argv[:1] == ["ace"] and len(argv) >= 3:
        if not drive():
            sys.exit("remote: no render queue drive (MUSE_RENDER_DRIVE)")
        return ace(argv[1], argv[2], argv[3:])
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
