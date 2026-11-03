#!/usr/bin/env python3
"""Turn one library script into still prompts, shot prompts and a render script.

  python3 scripts/build.py ME-0001 WORK      # WORK/stills/*.json, WORK/shots/*.prompt.txt, WORK/render.sh,
                                             # WORK/script.json, WORK/stills.sh

Stills: one first frame per (framing, cast, wardrobe, state) group, so all close-ups of one person in
one episode start from the same face (image generation takes no reference image; sharing the still is
what keeps a face identical across cuts). A shot may set "still": "<name>" to share or split a group,
and "state" (e.g. "soaked") to change the look mid-episode.
Shots: one muse render per shot, first frame = its still, one line at most, timed so the line starts
at 0.6 s (a line at 0 s fails SOUND WITHOUT LIPS) and the clip runs `sec + 1` s for trimming room.
"""
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CAST = json.loads((SKILL / "series/cast.json").read_text())
LOOK = (SKILL / "prompt/look.txt").read_text().strip()
FRAMING = {
    "wide": "Wide shot, the whole scene and the people full-length, the place clearly established",
    "medium": "Medium shot from the waist up, the speaker large in the upper half of the frame",
    "close": "Close-up from the chest up, the face large in the upper half of the frame, both eyes and the whole mouth clearly visible, front three-quarter view, never profile",
    "two-shot": "Medium two-shot from the waist up, both bodies facing the camera squarely, each turning only the head partway toward the other, both faces in front three-quarter view, both mouths visible",
}


def load_script(sid):
    for f in sorted((SKILL / "library").glob("batch_*.json")):
        for s in json.loads(f.read_text()):
            if s["id"] == sid:
                return s
    sys.exit(f"{sid} not in library/")


def person(key, sc, state=""):
    c = CAST[key]
    wk = sc.get("wardrobe", {}).get(key) or next(iter(c["wardrobe"]))
    extra = f" Right now: {state}." if state else ""
    return f"{c['identity']} Wearing: {c['wardrobe'][wk]}.{extra}"


def still_key(shot, sc):
    if shot.get("still"):
        return shot["still"]
    who = "-".join(shot["cast"])
    state = "-".join(re.findall(r"[a-z]+", shot.get("state", "").lower())[:2])
    return f"{shot['framing']}-{who}" + (f"-{state}" if state else "") \
        if shot["framing"] in ("close", "medium") else shot["id"]


def still_prompt(shot, sc):
    people = " ".join(person(k, sc, shot.get("state", "")) for k in shot["cast"])
    pose = shot.get("still_pose") or shot["action"]
    return (f"Vertical 9:16 frame from a late-1990s Hollywood romantic comedy shot on 35 mm colour negative. "
            f"{FRAMING[shot['framing']]}. Place: {sc['setting']}. The moment: {pose} Mouths closed, natural "
            f"expressions, caught mid-moment, not posing. {people} LEFT and RIGHT mean the person's own side. "
            f"Original faces that resemble no actor, celebrity or public figure; very attractive in a natural, "
            f"unretouched way: real skin texture, soft lens, gentle halation, fine film grain, warm creamy "
            f"colour, shallow depth of field. Everyone looks in their early twenties, fresh and youthful. "
            f"Bright, airy, high-key: soft diffused light, faces evenly lit, low contrast, milky lifted "
            f"shadows, pale cream-and-pastel palette; even night or rain is bright and warm like a lit studio "
            f"set, never dark or moody, never teal-and-orange. No HDR, no airbrushed or plastic skin, no CGI look. "
            f"No text, no logos, no watermark.")


def shot_prompt(shot, sc):
    dur = shot["sec"] + 1
    people = "\n".join(f"- {CAST[k]['name'].split()[0]}: {person(k, sc, shot.get('state', ''))} "
                       f"Voice: {CAST[k]['voice']}." for k in shot["cast"])
    p = [f"NO TEXT ON SCREEN. One continuous {dur}-second shot of a short film. The attached image is the exact "
         f"first frame: keep every face, hairstyle, outfit, the framing and the camera position.",
         f"CAST (keep faces, hair, outfits and voices identical for the whole clip):\n{people}",
         f"SETTING: {sc['setting']}.",
         f"CAMERA: {FRAMING[shot['framing']]}. Steady, locked, eye-level; ONE CONTINUOUS TAKE, no cuts, no zoom.",
         f"ACTION: {shot['action']}"]
    ln = shot.get("line")
    if ln:
        who = CAST[ln["who"]]["name"].split()[0].strip("'")
        others = [CAST[k]["name"].split()[0] for k in shot["cast"] if k != ln["who"]]
        listen = (f" {', '.join(others)} listens with lips closed and still, reacting only with the eyes."
                  if others else "")
        sex = "her" if CAST[ln["who"]]["sex"] == "F" else "his"
        p.append(f"SCRIPT (natural American English, normal conversational pace, the exact words, nothing added):\n"
                 f"0.0-0.6 s: silence, {who} holds the look, lips closed.\n"
                 f"0.6 s: {who} speaks, only {sex} lips move, in {sex} own voice: \"{ln['en']}\"{listen}\n"
                 f"After the line: {who} closes {sex} mouth and holds the expression to the end of the shot. "
                 f"Nobody says anything else.")
    else:
        p.append("SOUND: no dialogue at all, nobody speaks or moves their lips as if talking; only natural "
                 "ambient sound of the place.")
    p.append(LOOK)
    return "\n\n".join(p), dur


def build(sid, work):
    sc, work = load_script(sid), Path(work)
    for d in ("stills", "shots", "clips"):
        (work / d).mkdir(parents=True, exist_ok=True)
    (work / "script.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1))
    stills, lines = {}, ["#!/usr/bin/env bash", "# render every shot in parallel, one muse call each",
                         "set -u", f"cd {work}", f"MV=${{MUSE_VIDEO:-$HOME/Work/museai-main/.claude/skills/muse-video/scripts/muse-video}}"]
    for shot in sc["shots"]:
        k = still_key(shot, sc)
        stills.setdefault(k, still_prompt(shot, sc))
        text, dur = shot_prompt(shot, sc)
        (work / "shots" / f"{shot['id']}.prompt.txt").write_text(text)
        out = f"{sid.lower()}-{shot['id']}.mp4"
        lines.append(f"( [ -f clips/{out} ] || {{ SIZE=9:16 DURATION={dur} IMAGE=stills/{k}.png OUT_NAME={out} "
                     f"NO_OPEN=1 \"$MV\" -f shots/{shot['id']}.prompt.txt && cp ~/Movies/museai/{out} clips/; }} "
                     f"> clips/{shot['id']}.log 2>&1; echo \"{shot['id']} $?\" ) &")
    lines.append("wait")
    for k, p in stills.items():
        (work / "stills" / f"{k}.json").write_text(json.dumps(
            {"prompt": p, "n": 2, "size": "1080x1920", "response_format": "b64_json"}))
    (work / "render.sh").write_text("\n".join(lines) + "\n")
    (work / "render.sh").chmod(0o755)
    print(f"{sid}: {len(sc['shots'])} shots, {len(stills)} stills -> {work}")
    for k in stills:
        print(f"  still {k}")


if __name__ == "__main__":
    build(*sys.argv[1:3])
