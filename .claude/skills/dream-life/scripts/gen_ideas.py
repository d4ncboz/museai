"""Build the idea bank: ideas.json (machine) + ideas.md (one line per idea) in the skill folder.

Usage: python3 scripts/gen_ideas.py [--count 1000] [--seed 23]

Every idea = one theme (scripts/themes.py: an impossible little life as 8-10 beats) x one look
(looks.json: the reference styles) x one moment of the day, with one character from the look's cast,
6 of the theme's beats (kept in story order) as the shot list, a hook line and a music style.
Deterministic: the same seed rebuilds the same bank. Uniqueness: no two ideas share theme + look +
moment, no two ideas of one theme share the same 6 beats, every theme gets an even share, and the
bank is interleaved so neighbouring ideas differ in theme and look.
To widen the bank: append themes to themes.py (or looks to looks.json) and rerun.
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from themes import THEMES  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent
LOOKS = json.loads((SKILL / "looks.json").read_text())

# name, day|night, what it looks like (goes into every shot brief), music flavour
MOMENTS = {
    "spring morning": (
        "day",
        "a fresh spring morning, blossom on the trees, soft clear light",
        "light and hopeful",
    ),
    "summer day": (
        "day",
        "a bright summer day, deep blue sky, big soft white clouds, gentle shadows",
        "sunny and carefree",
    ),
    "golden hour": (
        "day",
        "late golden hour, warm low sun, long soft shadows, peach-tinted clouds",
        "warm and nostalgic",
    ),
    "autumn afternoon": (
        "day",
        "a mild autumn afternoon, amber leaves drifting, honey-coloured light",
        "cosy and wistful",
    ),
    "first snow": (
        "day",
        "the first snow day, soft white flakes falling, bright and cosy",
        "soft sleigh bells, cosy",
    ),
    "blue hour": (
        "night",
        "blue hour at dusk, periwinkle sky, the first lamps and windows glowing warm",
        "tender and slow",
    ),
    "starry night": (
        "night",
        "a clear starry night, deep navy sky full of stars, warm lamp light",
        "lullaby, hushed",
    ),
    "snowy night": (
        "night",
        "a snowy night, flakes drifting slowly through warm lamp light",
        "lullaby, soft sleigh bells",
    ),
}
LOOK_MOMENTS = {
    "pastel": list(MOMENTS),
    "lavender": ["spring morning", "summer day", "golden hour", "blue hour"],
    "workshop": list(MOMENTS),
    "ink": ["spring morning", "autumn afternoon", "first snow", "blue hour", "snowy night"],
    "nocturne": ["autumn afternoon", "first snow", "blue hour", "starry night", "snowy night"],
    "anime": [
        "spring morning",
        "summer day",
        "golden hour",
        "autumn afternoon",
        "blue hour",
        "starry night",
    ],
    "porcelain": ["golden hour", "blue hour", "starry night", "snowy night"],
}
SHOTS = 6

# extra hook lines, rotated as caption_alt so a series of posts does not repeat one phrasing
HOOKS = [
    "the life I'd choose if dreams were real",
    "pov: you wake up in my dream",
    "imagine living here",
    "if I could live anywhere",
    "a life that only exists when I sleep",
    "my dream life, frame by frame",
    "somewhere only we know",
    "pov: reality is optional",
    "the softest life",
    "this is where I go when I close my eyes",
    "a quiet life in a world that isn't real",
    "save this for when life feels heavy",
    "pov: everything is gentle here",
    "the world I'd build for you",
    "if the world were made of clouds",
    "tell me this isn't your dream too",
    "a little life, a little magic",
    "where would you live: here or here?",
    "pov: magic is just a job here",
    "living slowly, dreaming loudly",
]


def fits(theme_time, moment):
    return theme_time == "any" or MOMENTS[moment][0] == theme_time


def combos(theme, rng):
    slug, fmt, time, looks = theme[:4]
    out = [(look, m) for look in looks for m in LOOK_MOMENTS[look] if fits(time, m)]
    rng.shuffle(out)
    # spread looks: take one per look in turn, so a theme's first ideas cover all its looks
    by_look = {look: [c for c in out if c[0] == look] for look in looks}
    spread = []
    while any(by_look.values()):
        for look in looks:
            if by_look[look]:
                spread.append(by_look[look].pop(0))
    return spread


def pick_beats(beats, used, rng):
    for _ in range(200):
        idx = tuple(sorted(rng.sample(range(len(beats)), SHOTS)))
        if idx not in used:
            used.add(idx)
            return [beats[i] for i in idx]
    raise SystemExit("ran out of beat subsets; add beats to the theme")


def idea(n, theme, look, moment, k, beats, rng):
    slug, fmt, time, looks, title, hook, _ = theme
    L = LOOKS[look]
    who = None if fmt == "postcard" else L["cast"][k % len(L["cast"])]
    mom = MOMENTS[moment][1]
    shots = []
    for b in beats:
        text = b.replace("{who}", who) if who else b
        shots.append(f"{text[0].upper()}{text[1:]}. {mom[0].upper()}{mom[1:]}.")
    return {
        "id": f"dl-{n:04d}",
        "title": f"{title} ({L['name']}, {moment})",
        "theme": slug,
        "format": fmt,
        "look": look,
        "moment": moment,
        "character": who,
        "hook": hook,
        "caption_alt": HOOKS[n % len(HOOKS)],
        "palette": L["palette"],
        "music": f"{L['music']}, {MOMENTS[moment][2]}",
        "shots": shots,
    }


def bank(count, seed):
    rng = random.Random(seed)
    order = list(THEMES)
    queues = {t[0]: combos(t, rng) for t in order}
    used = {t[0]: set() for t in order}
    taken = {t[0]: 0 for t in order}
    ideas, last_look = [], None
    while len(ideas) < count and any(queues.values()):
        rng.shuffle(order)
        for t in order:
            if len(ideas) >= count or not queues[t[0]]:
                continue
            q = queues[t[0]]
            # prefer a combo whose look differs from the previous idea's
            j = next((i for i, c in enumerate(q) if c[0] != last_look), 0)
            look, moment = q.pop(j)
            k = taken[t[0]]
            taken[t[0]] += 1
            ideas.append(
                idea(len(ideas) + 1, t, look, moment, k, pick_beats(t[6], used[t[0]], rng), rng)
            )
            last_look = look
    return ideas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=23)
    a = ap.parse_args()
    ideas = bank(a.count, a.seed)
    if len(ideas) < a.count:
        print(f"only {len(ideas)} unique combos; add themes/looks/moments", file=sys.stderr)
    (SKILL / "ideas.json").write_text(json.dumps(ideas, indent=1, ensure_ascii=False) + "\n")
    lines = [
        "# Dream-life video ideas",
        "",
        f"{len(ideas)} ideas, built by `scripts/gen_ideas.py` from {len(THEMES)} themes x {len(LOOKS)} looks x "
        f"{len(MOMENTS)} moments. Used ones are in `~/.config/museai/dream-history.json` (`scripts/ideas.py list`).",
        "",
    ]
    for i in ideas:
        lines.append(f'- **{i["id"]}** [{i["format"]}] {i["title"]} · "{i["hook"]}"')
    (SKILL / "ideas.md").write_text("\n".join(lines) + "\n")
    print(f"{len(ideas)} ideas -> ideas.json, ideas.md")


if __name__ == "__main__":
    main()
