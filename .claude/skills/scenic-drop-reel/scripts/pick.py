"""Pick a travel-reel template at random and print the plan for it.

Usage:
  python3 scripts/pick.py --place "Amalfi Coast" --scope region --setting coast [--country italy] [--id ID] [--n 6]

scope   = what the user named: country | region | city | place
setting = main landscape: coast island mountain lake city oldtown nature desert snow
Chooses uniformly among templates whose scope and setting fit, skipping the last 5 used
(history in ~/.config/scenic-drop-reel/history.json), and prints JSON: the template plus, per
shot, the camera move and light to put in each brief, the transition after it, and the music
tags/lyrics with the place filled in. --id forces a template; --list prints all ids.

Length is random per reel, in a range that suits the template's pace (a template may set
"length": [min, max] seconds): slow dreamy templates run longer and may hold each shot 1.5-2x
the pattern, fast cut templates stay short. No shot is held under MIN_SHOT_S: a faster pattern
is doubled until it is. The shot count follows from the length, at most MAX_REEL_S (18 s). --length
forces seconds, --n the rendered shot count. Each shot gets a render "duration" (6-10 s) long enough
for its window. The last shot is a reprise ("reprise": 1, nothing to render): compose.py plays the
frames of clip 1 just before the hook's window, so the reel loops seamlessly.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
GREEN_SETTINGS = ("mountain", "nature", "island", "lake")
HISTORY = Path.home() / ".config/scenic-drop-reel/history.json"
CARD_INTROS = ("countdown", "black-title", "coords")
MAX_SHOTS = 12  # every shot is one muse render
MAX_SHOT_S = 5.5  # longest window a 6-10 s muse clip gives at a calm, even pace
MIN_SHOT_S = 1.6  # shorter holds flash past before the eye settles (Svalbard reel: 0.97 s shots felt too fast)
SLOW_MIN_SHOT_S = 2.4  # calm music (< 100 BPM) wants the view to breathe with it
MAX_REEL_S = 18  # 10-18 s reels get watched to the end and replayed (user rule 2026-10-29)
MAX_HOLD_S = 4.0  # 3 shots + the reprise still fit in MAX_REEL_S
HOOK_BEATS = 4  # card intros sit on shot 1 for at most 4 beats: the wow view shows from frame 0


def length_range(t, shot_s):
    if "length" in t:
        return t["length"]
    if shot_s >= 2.4:  # slow holds: room to breathe
        return 12, 18
    if shot_s >= 1.4:
        return 10, 18
    return 10, 16  # one-beat bursts tire fast


def cycle(seq, i):
    return seq[i % len(seq)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--place", default="")
    ap.add_argument("--scope", choices=["country", "region", "city", "place"], default="place")
    ap.add_argument("--setting", default="any")
    ap.add_argument("--country", default="", help="country/region key for local-flavour music")
    ap.add_argument("--id", help="use this template")
    ap.add_argument("--n", type=int, help="override shot count")
    ap.add_argument("--length", type=float, help="reel seconds (default: random for the template)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    data = json.loads((SKILL / "templates.json").read_text())
    temps = data["templates"]
    if a.list:
        for t in temps:
            print(f"{t['id']:20} {t['name']:26} {','.join(t['scope']):28} {','.join(t['setting'])}")
        return

    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    if a.id:
        t = next((t for t in temps if t["id"] == a.id), None) or sys.exit(f"no template {a.id}")
    else:
        fit = [t for t in temps if a.scope in t["scope"]
               and ("any" in t["setting"] or a.setting in t["setting"] or a.setting == "any")]
        fresh = [t for t in fit if t["id"] not in history[-5:]] or fit
        t = random.choice(fresh)
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps((history + [t["id"]])[-50:]))

    # the setting brings its own music and adds its own moves/transitions to the template's signature ones,
    # so a snowy reel and a beach reel on the same template still look and sound different
    scen = data["sceneries"].get(a.setting)
    fast = "fpv" in t["moves"]
    music = dict(t["music"])
    if scen and not fast and t["id"] != "local-flavour":
        style = random.choice(scen["music"])
        music["tags"], music["bpm"] = style["tags"], random.randint(*style["bpm"])
    moves, transitions = list(t["moves"]), list(t["transitions"])
    if scen and not fast:
        own_moves = random.sample(scen["moves"], len(scen["moves"]))
        own_trans = random.sample(scen["transitions"], len(scen["transitions"]))
        moves = [m for pair in zip(moves * len(own_moves), own_moves, strict=False) for m in pair]
        transitions = [x for pair in zip(transitions * len(own_trans), own_trans, strict=False) for x in pair]

    beat = 60 / music["bpm"]
    pattern = list(t["pattern"])
    if min(pattern) >= 4 and music["bpm"] <= 104 and not a.n:  # slow template: sometimes hold each shot longer
        hold = random.choice([b for b in (4, 6, 8) if b * beat <= min(MAX_SHOT_S, MAX_HOLD_S)] or [4])
        pattern = [hold] * len(pattern)
    min_s = SLOW_MIN_SHOT_S if music["bpm"] < 100 else MIN_SHOT_S
    while min(pattern) * beat < min_s:  # double the hold, keeping cuts on the beat and the pattern's rhythm
        pattern = [b * 2 for b in pattern]
    while sum(pattern) / len(pattern) * beat > MAX_HOLD_S and all(b % 2 == 0 for b in pattern) \
            and min(pattern) // 2 * beat >= min_s:
        pattern = [b // 2 for b in pattern]
    shot_s = sum(pattern) / len(pattern) * beat
    intro = dict(t["intro"])
    if intro["type"] in CARD_INTROS:
        intro["beats"] = min(intro.get("beats", 0), HOOK_BEATS)
    intro_s = intro.get("beats", 0) * beat if intro["type"] in CARD_INTROS else 0
    lo, hi = length_range(t, shot_s)
    hi = min(hi, intro_s + (MAX_SHOTS + 1) * shot_s, MAX_REEL_S)
    lo = min(lo, 0.6 * hi)
    length = a.length or random.uniform(lo, max(lo, hi))
    # n rendered shots + one reprise: the last shot replays the frames just before shot 1 (no render),
    # so the reel's end flows into its start and the loop replays seamlessly
    n = a.n or max(3, min(MAX_SHOTS, round((length - intro_s) / shot_s) - 1))
    if "times" in t:
        n = min(n, len(t["times"]))
    place = a.place
    local = data["local_sounds"].get(a.country.lower() or place.lower(), data["local_sounds"]["default"])
    if "{local}" in music["tags"]:
        music["tags"] = music["tags"].replace("{local}", local)
    elif a.country.lower() in data["local_sounds"]:
        # a Japan reel with generic dreamy pop sounded like nowhere (Fuji reel, 2026-11-02): every template
        # carries the country's own instruments
        music["tags"] = f"{local}, {music['tags']}"
    music["lyrics"] = music["lyrics"].replace("{place}", place)
    cap = max(min(pattern), math.floor(MAX_HOLD_S / beat))  # slow patterns: no hold over MAX_HOLD_S
    if not a.n and not a.length:  # min 3 shots of a slow pattern can still overrun the reel cap
        while n > 3 and intro_s + (sum(min(cycle(pattern, i), cap) for i in range(n)) + min(pattern)) * beat > MAX_REEL_S:
            n -= 1
    shots = []
    for i in range(n):
        light = cycle(t["lights"], i) if "lights" in t else t["light"]
        beats = min(cycle(pattern, i), cap)
        shots.append({
            "shot": i + 1,
            "beats": beats,
            "duration": max(6, min(10, math.ceil(beats * beat + 3))),
            "move": data["moves"][cycle(moves, i)],
            "light": data["lights"].get(light, light),
            "transition_after": cycle(transitions, i),
            "time_label": cycle(t["times"], i) if "times" in t else None,
        })
    # short: one 10 s render of shot 1 holds the reprise, the hook card and shot 1's own beats
    rep = min(pattern + [cap])
    while (rep + shots[0]["beats"]) * beat + intro_s > 8.5 and (rep - 1) * beat >= min_s:
        rep -= 1
    shots.append({"shot": n + 1, "beats": rep, "reprise": 1, "duration": None, "transition_after": None,
                  "move": shots[0]["move"], "light": shots[0]["light"], "time_label": shots[0]["time_label"]})
    # shot 1 carries the hook card and the reprise's frames too
    shots[0]["duration"] = max(6, min(10, math.ceil((rep + shots[0]["beats"]) * beat + intro_s + 2)))
    if "text" in intro:
        intro["text"] = intro["text"].replace("{place}", place).replace("{PLACE}", place.upper()).replace("{n}", str(n))
    # warm/teal grades turn forests olive; green landscapes get the vivid grade (Zhangjiajie reel, 2026-10-31:
    # "I need something greener that looks fantastic")
    grade = "vivid" if a.setting in GREEN_SETTINGS and t["grade"] in ("warm-film", "teal-orange", "moody") else t["grade"]
    print(json.dumps({"template": t["id"], "name": t["name"], "vibe": t["vibe"], "place": place,
                      "seconds": round(intro_s + sum(x["beats"] for x in shots) * beat, 1),
                      "intro": intro, "text": t["text"], "grade": grade, "target": t["target"],
                      "ramp": t["ramp"], "fast": fast, "music": music, "shots": shots}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
