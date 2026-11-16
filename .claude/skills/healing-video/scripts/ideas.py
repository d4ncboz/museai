"""Idea bank + history for healing videos, so no video repeats an earlier one.

Bank: ../ideas.json (1000 ideas, scripts/gen_ideas.py). History: ~/.config/museai/healing-history.json,
one entry per DELIVERED video (idea id or custom idea, title, home, season, task, animal, shots, video, date).

  python3 scripts/ideas.py next [--season autumn|now] [--home Kyoto] [--animal cat] [--no-animal] [--n 3]
  python3 scripts/ideas.py show hv-0042
  python3 scripts/ideas.py check --title "..." --home "..." --season autumn --task "..." [--animal cat]
  python3 scripts/ideas.py record hv-0042 --video ~/Desktop/healing-x.mp4 [--shots shots.json]
  python3 scripts/ideas.py record custom --title "..." --home "..." --season ... --task ... --video ...
  python3 scripts/ideas.py list [--last 20]
  python3 scripts/ideas.py stats
  python3 scripts/ideas.py hook      # the hook format used longest ago (SKILL.md "Hook formats")

next: the first unused ideas (bank order) that also differ from the last 10 videos in home and task and
from the last 3 in animal and caption, so a run of posts never looks samey. "--season now" = the month's
season (northern hemisphere). check exits 1 (DUPLICATE) when an earlier video has the same home +
season + task, or the same task + animal in the same home; 2 (SIMILAR) on the same home or task in
the last 10.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BANKS = [SKILL / "ideas.json", SKILL / "ideas-garden.json", SKILL / "ideas-ritual.json"]
STYLES = ["classic", "garden", "harvest-asmr", "pov-ritual"]  # rotation order for `style`
HIST = Path.home() / ".config/museai/healing-history.json"
MONTH_SEASON = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
                6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def norm(x):
    return (x or "").strip().lower()


def verdict(idea, hist):
    """(code, reason): 0 fresh, 1 duplicate, 2 too similar to recent videos."""
    for h in hist:
        if h.get("id") and h["id"] == idea.get("id"):
            return 1, f"idea {h['id']} already used ({h['date']}, {h['video']})"
        same_home = norm(h["home"]) == norm(idea["home"])
        if same_home and norm(h["season"]) == norm(idea["season"]) and norm(h["task"]) == norm(idea["task"]):
            return 1, f"same home + season + task as {h['date']} {h['title']}"
        if same_home and norm(h["task"]) == norm(idea["task"]) and norm(h.get("animal")) == norm(idea.get("animal")):
            return 1, f"same home + task + animal as {h['date']} {h['title']}"
    for h in hist[-10:]:
        if norm(h["home"]) == norm(idea["home"]):
            return 2, f"home used in the last 10 videos ({h['date']} {h['title']})"
        if norm(h["task"]) == norm(idea["task"]):
            return 2, f"task used in the last 10 videos ({h['date']} {h['title']})"
    for h in hist[-3:]:
        if idea.get("animal") and norm(h.get("animal")) == norm(idea["animal"]):
            return 2, f"animal used in the last 3 videos ({h['date']} {h['title']})"
        if idea.get("caption") and norm(h.get("caption")) == norm(idea["caption"]):
            return 2, f"caption used in the last 3 videos ({h['date']} {h['title']})"
    return 0, "fresh"


OUTFITS = [
    "a red gingham cotton sundress with puff sleeves", "a pale blue linen pinafore dress over a white blouse",
    "a yellow cotton sundress with small white flowers", "a sage-green linen dress with rolled sleeves",
    "a white broderie-anglaise dress", "a faded pink striped cotton dress",
    "a mustard-yellow knit sweater over a cream skirt", "a navy and white striped breton top with linen trousers",
    "a terracotta linen shirt-dress with the sleeves rolled", "denim dungarees over a white t-shirt",
    "a dusty-blue cotton blouse with a long floral skirt", "an oatmeal wool cardigan over a green linen dress",
    "a rust-orange corduroy pinafore over a cream blouse", "a lavender gingham shirt tucked into a long cotton skirt",
    "a forest-green knit jumper with the sleeves pushed up", "a soft pink linen smock dress",
    "a rose-print prairie dress with a ribbon at the waist", "a charcoal fisherman sweater with jeans",
    "a butter-yellow cardigan over a white tee and a denim skirt", "an olive utility shirt dress with a belt",
]


# Hook formats (SKILL.md "Hook formats", studied 2026-11-16): the STRUCTURE of the first seconds rotates
# like the style, so two videos in a row never open the same way even when their subjects differ.
HOOKS = {
    "sound-first": "shot 1 is a close-up of one action whose sound is heard as it happens, started mid-action",
    "result-first": "shot 1 is the finished, striking result held 1-1.5 s; then how it was made; the last shot "
                    "shows the result in its place in the home",
    "same-frame": "every shot keeps the exact same locked-off framing and only time changes it (bare to bloom, "
                  "empty to laid, morning to dusk); render shot 1, then IMAGE=<its first frame> for the rest",
    "one-take": "one continuous satisfying process from start to finish (pouring a pattern, icing, folding), "
                "the payoff only in the last 1.5 s; 2-3 shots at most",
    "twist": "shot 1 shows a familiar thing made in an unexpected shape or size (a bowl of dried citrus slices, "
             "bread twisted like a branch); then how",
    "with-me": "an invitation montage ('harvest with me'): one item per ~1 s shot, each with a tiny lower-case "
               "label naming it",
}


def hook_of(h):
    return h.get("hook") or "sound-first"


def next_hook(hist):
    last = [hook_of(h) for h in hist][::-1]
    return max(HOOKS, key=lambda k: last.index(k) if k in last else 99)


def with_outfit(idea):
    import random
    old = idea.get("outfit")
    new = random.choice([o for o in OUTFITS if o != old])
    idea["outfit"] = new
    pat = re.compile(r"\b(girl|woman)\b", re.I)
    shots = []
    for sh in idea.get("shots", []):
        if old and old in sh:
            sh = sh.replace(old, new)
        elif pat.search(sh) and new not in sh:
            sh = sh.rstrip() + f" She wears {new}."
        shots.append(sh)
    idea["shots"] = shots
    return idea


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next")
    n.add_argument("--season")
    n.add_argument("--home")
    n.add_argument("--animal")
    n.add_argument("--no-animal", action="store_true")
    n.add_argument("--n", type=int, default=1)
    n.add_argument("--style", help="garden = montage bank (gm-*), pov-ritual = ritual bank (pr-*); "
                   "default: the original bank")
    sub.add_parser("show").add_argument("id")
    for name in ("check", "record"):
        p = sub.add_parser(name)
        if name == "record":
            p.add_argument("id", help="hv-NNNN or 'custom'")
            p.add_argument("--video", required=True)
            p.add_argument("--shots", help="JSON list of the shot briefs actually used")
            p.add_argument("--hook", choices=list(HOOKS), help="hook format used (default: the idea's, else sound-first)")
        for f in ("title", "home", "season", "task", "animal", "caption"):
            p.add_argument(f"--{f}")
    sub.add_parser("list").add_argument("--last", type=int, default=20)
    sub.add_parser("stats")
    sub.add_parser("style")
    sub.add_parser("hook")
    a = ap.parse_args()

    bank = [i for b in BANKS for i in load(b, [])]
    by_id = {i["id"]: i for i in bank}
    hist = load(HIST, [])

    if a.cmd == "next":
        season = MONTH_SEASON[datetime.date.today().month] if a.season == "now" else a.season
        out = []
        for idea in bank:
            if (idea.get("style") or "classic") != (a.style or "classic"):
                continue
            if season and norm(idea["season"]) != norm(season):
                continue
            if a.home and norm(a.home) not in norm(idea["home"]):
                continue
            if a.animal and norm(a.animal) not in norm(idea.get("animal")):
                continue
            if a.no_animal and idea.get("animal"):
                continue
            if verdict(idea, hist)[0] == 0:
                out.append(idea)
            if len(out) == a.n:
                break
        if not out:
            sys.exit("no fresh idea matches; loosen the filters or add homes/tasks to gen_ideas.py")
        out = [with_outfit(dict(i)) for i in out]
        hook = next_hook(hist)
        for i in out:
            i["hook"], i["hook_rule"] = hook, HOOKS[hook]
        print(json.dumps(out if a.n > 1 else out[0], ensure_ascii=False, indent=1))
    elif a.cmd == "show":
        print(json.dumps(by_id.get(a.id) or sys.exit(f"no idea {a.id}"), ensure_ascii=False, indent=1))
    elif a.cmd == "check":
        code, why = verdict({k: getattr(a, k) for k in ("title", "home", "season", "task", "animal", "caption")}, hist)
        print(["FRESH", "DUPLICATE", "SIMILAR"][code] + f": {why}")
        sys.exit(code)
    elif a.cmd == "record":
        if a.id == "custom":
            idea = {k: getattr(a, k) for k in ("title", "home", "season", "task", "animal", "caption")}
            missing = [k for k in ("title", "home", "season", "task") if not idea[k]]
            if missing:
                sys.exit(f"custom record needs --{' --'.join(missing)}")
            idea["id"] = None
        else:
            idea = dict(by_id.get(a.id) or sys.exit(f"no idea {a.id}"))
        code, why = verdict(idea, hist)
        if code == 1:
            print(f"warning: recording a duplicate ({why})", file=sys.stderr)
        entry = {k: idea.get(k) for k in ("id", "title", "home", "season", "task", "animal", "caption", "style")}
        entry["hook"] = a.hook or idea.get("hook") or "sound-first"
        entry["shots"] = json.loads(Path(a.shots).read_text()) if a.shots else idea.get("shots", [])
        entry["video"] = str(Path(a.video).expanduser().resolve())
        entry["date"] = datetime.date.today().isoformat()
        hist.append(entry)
        HIST.parent.mkdir(parents=True, exist_ok=True)
        HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=1) + "\n")
        print(f"recorded {entry['id'] or 'custom'}: {entry['title']} ({len(hist)} videos in history)")
    elif a.cmd == "list":
        for h in hist[-a.last:]:
            print(f"{h['date']}  {h['id'] or 'custom':9}  {h['title']}  → {h['video']}")
        if not hist:
            print("no videos yet")
    elif a.cmd == "style":
        # rotation: the style used longest ago (never used = first); postcard/ode/story count as "classic"
        def style_of(h):
            cap = h.get("caption") or ""
            return h.get("style") or (cap[6:] if cap.startswith("style:") else "classic")
        last = [style_of(h) for h in hist][::-1]
        print(max(STYLES, key=lambda st: last.index(st) if st in last else 99))
    elif a.cmd == "hook":
        print(next_hook(hist))
    elif a.cmd == "stats":
        used = {h["id"] for h in hist if h.get("id")}
        print(f"{len(hist)} videos delivered, {len(used)}/{len(bank)} bank ideas used, "
              f"{sum(verdict(i, hist)[0] == 0 for i in bank)} fresh now")


if __name__ == "__main__":
    main()
