"""Check a nostalgia plan and render its shots.

  python3 scripts/plan.py check plan.json [--shot 2.3]
  python3 scripts/plan.py render plan.json WORK [s03 s07 ...]   # every shot (or the ids given), one at a time

plan.json: {"slug", "era", "music", "shots": [{"id", "brief", "en", "zh", "start"?}, ...]}
check: 30-45 s total, 10-16 shots, one EN + 中文 line per shot short enough for one row,
the first line is the hook, the last one a question (comments drive the reach).
render: one background muse-video call per shot (9:16, 6 s, prompt/look.txt, ERA line first),
writing WORK/clips/<id>.mp4 and <id>.log; RETAKE=1 passes through for a re-render."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
MUSE_VIDEO = SKILL.parent / "muse-video" / "scripts" / "muse-video"
EN_MAX, ZH_MAX = 36, 16  # one row each at the compose.py font sizes on 1080 px


def check(plan, shot):
    errs = []
    shots = plan["shots"]
    total = len(shots) * shot
    if not 29.5 <= total <= 45.5:
        errs.append(
            f"total {total:.1f} s: keep it 30-45 s (user rule) - change the shot count or --shot"
        )
    if not 10 <= len(shots) <= 16:
        errs.append(f"{len(shots)} shots: use 10-16")
    for s in shots:
        for k in ("id", "brief", "en", "zh"):
            if not s.get(k):
                errs.append(f"{s.get('id', '?')}: missing {k}")
        if len(s.get("en", "")) > EN_MAX:
            errs.append(f"{s['id']}: en line over {EN_MAX} chars")
        if len(s.get("zh", "")) > ZH_MAX:
            errs.append(f"{s['id']}: zh line over {ZH_MAX} chars")
    if shots and not shots[-1].get("en", "").rstrip().endswith("?"):
        errs.append("last line is not a question (end on one: 'would you go back?')")
    for e in errs:
        print("FAIL", e)
    print(f"{'OK' if not errs else 'FAIL'} {len(shots)} shots x {shot} s = {total:.1f} s")
    return not errs


KEEP = {"QUALITY", "SIZE", "DURATION", "OUT_NAME", "NO_OPEN", "RETAKE", "IMAGE"}


def render(plan, work, only):
    clips = Path(work).expanduser().resolve() / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    look = (SKILL / "prompt" / "look.txt").read_text()
    for s in plan["shots"]:
        if only and s["id"] not in only:
            continue
        prompt = f"NO TEXT ON SCREEN. ERA: {plan['era']}.\n\n{s['brief']}\n\n{look}"
        env = dict(
            os.environ,
            QUALITY="0",
            SIZE="9:16",
            DURATION="6",
            OUT_NAME=f"{s['id']}.mp4",
            NO_OPEN="1",
        )
        (clips / f"{s['id']}.prompt.txt").write_text(prompt)
        jobs.append(" ".join(f"{k}={shlex.quote(v)}" for k, v in env.items() if k in KEEP)
                    + f" {shlex.quote(str(MUSE_VIDEO))} -f {shlex.quote(str(clips / (s['id'] + '.prompt.txt')))} {shlex.quote(str(clips))}")
        print("queue", s["id"])
    (clips / "jobs.txt").write_text("\n".join(jobs) + "\n")
    # one at a time, the next when one finishes (muse-video "Server"): never every shot at once
    subprocess.run([str(MUSE_VIDEO.parent / "render-queue"), str(clips / "jobs.txt")], cwd=clips, check=False)


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    plan = json.loads(Path(path).read_text())
    if cmd == "check":
        shot = float(sys.argv[sys.argv.index("--shot") + 1]) if "--shot" in sys.argv else 2.3
        sys.exit(0 if check(plan, shot) else 1)
    if cmd == "render":
        render(plan, sys.argv[3], set(sys.argv[4:]))
        return
    sys.exit(__doc__)


main()
