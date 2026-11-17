#!/usr/bin/env python3
"""story.json -> reference images -> one still per beat -> one clip per `clip` beat, each step idempotent.

  plan.py jobs  story.json          write jobs-refs.txt, jobs-stills.txt, jobs-clips.txt next to story.json
  plan.py ref   story.json NAME     render refs/<NAME>.png (a place or a recurring prop, nobody in it)
  plan.py still story.json N        render stills/sN.png for beat N (place + prop refs + the girl's bank card)
  plan.py clip  story.json N        animate stills/sN.png into sN.mp4 (16:9, DURATION=10) through scripts/shot
  plan.py brief story.json N        print the still and clip briefs of beat N
  plan.py status story.json         which refs, stills and clips exist

Each step skips work already on disk, so a queue killed by muse's 24-hour video limit is re-run as is.
Images are not under that limit: render refs and stills first, clips when quota is there. longform.py
uses the still (a slow push-in) for a clip beat whose clip is missing, so a cut can be watched at any stage.
"""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BANK = SKILL.parent / "character-bank" / "scripts"
LOOK = SKILL / "prompt" / "look.txt"
CAMERA = ("A completely still locked-off frame: the camera never moves, every edge of the frame stays in the same "
          "place from the first frame to the last.")
PY = sys.executable


def load(path):
    p = Path(path).resolve()
    return p, json.loads(p.read_text())


def look(story):
    """The footage rules: the story's `look` (path from .claude/skills/, e.g. field-to-table/prompt/look.txt)."""
    return SKILL.parent / story["look"] if story.get("look") else LOOK


def slug(name):
    return name.lower().replace("the ", "").replace(" ", "-")


def outfit_line(story, b):
    o = b.get("outfit")
    return f" Her clothes: {story['outfits'][o]}." if o and b.get("cast") else ""


def props_of(story, b, root):
    """(name, path) of the place reference and every named prop reference that exists."""
    out = []
    # a close-up gets no place reference: with the whole room attached muse widens the frame to show it
    for name in ([] if close(b) else [b.get("where")]) + b.get("props", []):
        if name and (root / "refs" / f"{slug(name)}.png").exists():
            out.append((name if name in b.get("props", []) else f"the {name}", root / "refs" / f"{slug(name)}.png"))
    return out


def close(b):
    return b["shot"].lower().startswith(("close-up", "top-down"))


def framing(b):
    """Who is in frame. look.txt describes the girl, so without this muse puts her face into every shot."""
    if b.get("cast"):
        return (" She is seen from behind or from the side, her face turned away from the camera or bowed over her "
                "work; she does not look at the camera.")
    if re.search(r"\bher (two )?hands?\b", b["shot"].lower()):
        return (" Only her hands and forearms in their sleeves are in the frame; her face, hair, braid and shoulders "
                "are outside the frame.")
    return " Nobody is in the frame: no person, no face, no hands."


def still_brief(story, b):
    place = story["places"][b["where"]]
    where = "The setting, mostly out of frame" if close(b) else "The place"
    return f"{story['light'][b['time']]} {b['shot']}{framing(b)}{outfit_line(story, b)} {where}: {place}."


def clip_brief(story, b):
    return f"{story['light'][b['time']]} {b['shot']} {b.get('move', '')}{framing(b)}{outfit_line(story, b)} {CAMERA}".strip()


def bank():
    sys.path.insert(0, str(BANK))
    import bank as bk  # noqa: PLC0415  (character-bank's script, loaded only when rendering)
    return bk


def render_still(story, text, cast, props, out_png, n=1):
    bk = bank()
    tmp = out_png.parent / f".{out_png.stem}"
    body = bk.scene_body(text, cast, look(story).read_text().strip(), "1920x1080", n, props)
    paths = bk.post(body, tmp, out_png.stem)
    paths[0].replace(out_png)
    for extra in paths[1:]:
        extra.replace(out_png.with_name(f"{out_png.stem}_alt{extra.stem[-1]}.png"))
    print(out_png)


def cmd_ref(sp, story, name):
    root = sp.parent
    out = root / "refs" / f"{slug(name)}.png"
    if out.exists():
        print(f"have {out}")
        return
    out.parent.mkdir(exist_ok=True)
    r = story["refs"][name]
    # look.txt describes the woman: without this a ref came back with her in it (field-to-table kitchen, clay pot)
    text = f'{r["brief"]} Nobody is in the frame: no person, no face, no hands.'
    if r["kind"] == "place":
        text = f"{text} The place: {story['places'][name]}."
    render_still(story, text, [], [], out)


def cmd_still(sp, story, n):
    root = sp.parent
    b = story["beats"][n - 1]
    out = root / "stills" / f"s{n}.png"
    if out.exists():
        print(f"have {out}")
        return
    out.parent.mkdir(exist_ok=True)
    render_still(story, still_brief(story, b), b.get("cast", []), props_of(story, b, root), out)


def cmd_clip(sp, story, n):
    root = sp.parent
    b = story["beats"][n - 1]
    out, still = root / f"s{n}.mp4", root / "stills" / f"s{n}.png"
    if out.exists():
        print(f"have {out}")
        return
    if not still.exists():
        sys.exit(f"no {still}: run `plan.py still {sp} {n}` first")
    env = dict(os.environ, IMAGE=str(still), SIZE="16:9", LOOK_FILE=str(look(story)), DURATION=os.environ.get("DURATION", "10"))
    sys.exit(subprocess.run([str(SKILL / "scripts" / "shot"), clip_brief(story, b), str(out)], env=env).returncode)


def cmd_jobs(sp, story):
    root, me = sp.parent, shlex.quote(str(Path(__file__).resolve()))
    s = shlex.quote(str(sp))
    # muse sometimes fails a submit (internal_error, cdp_connection_closed): retry each job a few times
    retry = "for t in 1 2 3; do {cmd} && break; sleep 60; done"
    refs = [retry.format(cmd=f"{PY} {me} ref {s} {shlex.quote(k)}") for k in story["refs"]]
    stills = [retry.format(cmd=f"{PY} {me} still {s} {i}") for i in range(1, len(story["beats"]) + 1)]
    clips = [retry.format(cmd=f"{PY} {me} clip {s} {i}") for i, b in enumerate(story["beats"], 1)
             if b.get("kind") == "clip"]
    for name, lines in (("refs", refs), ("stills", stills), ("clips", clips)):
        (root / f"jobs-{name}.txt").write_text("\n".join(lines) + "\n")
        print(f"jobs-{name}.txt: {len(lines)} jobs")


def cmd_status(sp, story):
    root = sp.parent
    refs = [k for k in story["refs"] if (root / "refs" / f"{slug(k)}.png").exists()]
    stills = [i for i in range(1, len(story["beats"]) + 1) if (root / "stills" / f"s{i}.png").exists()]
    want = [i for i, b in enumerate(story["beats"], 1) if b.get("kind") == "clip"]
    clips = [i for i in want if (root / f"s{i}.mp4").exists()]
    print(f"refs {len(refs)}/{len(story['refs'])}  stills {len(stills)}/{len(story['beats'])}  clips {len(clips)}/{len(want)}")
    print("missing clips:", " ".join(str(i) for i in want if i not in clips) or "-")


def main(a):
    if len(a) < 2:
        sys.exit(__doc__)
    sp, story = load(a[1])
    if a[0] == "jobs":
        cmd_jobs(sp, story)
    elif a[0] == "ref":
        cmd_ref(sp, story, a[2])
    elif a[0] == "still":
        cmd_still(sp, story, int(a[2]))
    elif a[0] == "clip":
        cmd_clip(sp, story, int(a[2]))
    elif a[0] == "brief":
        b = story["beats"][int(a[2]) - 1]
        print("STILL:", still_brief(story, b), "\nCAST:", b.get("cast"), "PROPS:", [p for p, _ in props_of(story, b, sp.parent)])
        print("CLIP:", clip_brief(story, b))
    elif a[0] == "status":
        cmd_status(sp, story)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
