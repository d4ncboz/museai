"""Idea bank + history for dream-life videos, so no video repeats an earlier one.

Bank: ../ideas.json (1000 ideas, scripts/gen_ideas.py). History: ~/.config/museai/dream-history.json,
one entry per DELIVERED video (idea id or custom idea, title, theme, look, moment, video, date).

  python3 scripts/ideas.py next [--look pastel] [--format day|friends|postcard] [--theme moon] [--moment night] [--n 3]
  python3 scripts/ideas.py show dl-0042
  python3 scripts/ideas.py search "moon"                 # ideas whose title/theme/hook match
  python3 scripts/ideas.py check --theme moon-picker --look pastel --moment "starry night"
  python3 scripts/ideas.py record dl-0042 --video ~/Desktop/dream-x.mp4 [--shots shots.json] [--music m.json]
  python3 scripts/ideas.py record custom --title "..." --theme my-slug --look pastel --moment "golden hour" --video ...
  python3 scripts/ideas.py list [--last 20] ; python3 scripts/ideas.py stats

next: the first unused ideas (bank order) whose theme was not used in the last 12 videos, in the
account's feed looks (FEED_LOOKS: the photoreal film looks, user rule 2026-11-01), alternating
between them; --look pins one, --look any opens all 7. --moment night|day
filters by time of day. check exits 1 DUPLICATE (same theme + look + moment, or the same idea) or
2 SIMILAR (theme in the last 12 videos).
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BANK = SKILL / "ideas.json"
HIST = Path.home() / ".config/museai/dream-history.json"
NIGHT = {"blue hour", "starry night", "snowy night"}
# the account's look: photoreal film, a young-woman lead (dl-0001, dl-0002). The illustrated looks
# (ink, nocturne, anime, porcelain) and workshop only when the user asks for them.
FEED_LOOKS = {"pastel", "lavender"}


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def norm(x):
    return (x or "").strip().lower()


def verdict(idea, hist):
    for h in hist:
        if h.get("id") and h["id"] == idea.get("id"):
            return 1, f"idea {h['id']} already used ({h['date']}, {h['video']})"
        if (norm(h["theme"]), norm(h["look"]), norm(h["moment"])) == (
            norm(idea["theme"]),
            norm(idea["look"]),
            norm(idea["moment"]),
        ):
            return 1, f"same theme + look + moment as {h['date']} {h['title']}"
    for h in hist[-12:]:
        if norm(h["theme"]) == norm(idea["theme"]):
            return 2, f"theme used in the last 12 videos ({h['date']} {h['title']})"
    return 0, "fresh"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next")
    n.add_argument("--look")
    n.add_argument("--format")
    n.add_argument("--theme")
    n.add_argument("--moment", help="a moment name, or day / night")
    n.add_argument("--n", type=int, default=1)
    sub.add_parser("show").add_argument("id")
    sub.add_parser("search").add_argument("words")
    for name in ("check", "record"):
        p = sub.add_parser(name)
        if name == "record":
            p.add_argument("id", help="dl-NNNN or 'custom'")
            p.add_argument("--video", required=True)
            p.add_argument("--shots", help="JSON list of the shot briefs actually used")
            p.add_argument("--music", help="the track's .json from scripts/music (flavour, seed)")
        for f in ("title", "theme", "look", "moment"):
            p.add_argument(f"--{f}")
    sub.add_parser("list").add_argument("--last", type=int, default=20)
    sub.add_parser("stats")
    a = ap.parse_args()
    bank = load(BANK, [])
    hist = load(HIST, [])
    by_id = {i["id"]: i for i in bank}

    if a.cmd == "next":
        out = []
        for i in bank:
            if a.look and a.look != "any" and i["look"] != a.look:
                continue
            if not a.look and i["look"] not in FEED_LOOKS:
                continue
            if a.format and i["format"] != a.format:
                continue
            if a.theme and norm(a.theme) not in norm(i["theme"]) + " " + norm(i["title"]):
                continue
            if a.moment:
                m = norm(a.moment)
                if m == "night" and i["moment"] not in NIGHT or m == "day" and i["moment"] in NIGHT:
                    continue
                if m not in ("day", "night") and m != i["moment"]:
                    continue
            if verdict(i, hist)[0]:
                continue
            if not a.look and hist and hist[-1]["look"] == i["look"]:
                continue
            out.append(i)
            if len(out) >= a.n:
                break
        if not out:
            sys.exit("no fresh idea matches; loosen the filters or add themes (gen_ideas.py)")
        print(json.dumps(out[0] if a.n == 1 else out, indent=1, ensure_ascii=False))
    elif a.cmd == "show":
        print(json.dumps(by_id[a.id], indent=1, ensure_ascii=False))
    elif a.cmd == "search":
        w = norm(a.words)
        used = {h.get("id") for h in hist}
        for i in bank:
            if w in norm(" ".join([i["title"], i["theme"], i["hook"], i["look"], i["moment"]])):
                print(f"{i['id']} {'USED ' if i['id'] in used else ''}{i['title']}")
    elif a.cmd == "check":
        code, why = verdict({"theme": a.theme, "look": a.look, "moment": a.moment}, hist)
        print(("FRESH", "DUPLICATE", "SIMILAR")[code], "-", why)
        sys.exit(code)
    elif a.cmd == "record":
        if a.id == "custom":
            e = {"id": None, "title": a.title, "theme": a.theme, "look": a.look, "moment": a.moment}
        else:
            i = by_id[a.id]
            e = {k: i[k] for k in ("id", "title", "theme", "look", "moment")}
        if a.shots:
            e["shots"] = json.loads(Path(a.shots).read_text())
        if a.music:
            e["music"] = json.loads(Path(a.music).read_text())
        e.update(video=a.video, date=datetime.date.today().isoformat())
        HIST.parent.mkdir(parents=True, exist_ok=True)
        HIST.write_text(json.dumps(hist + [e], indent=1, ensure_ascii=False) + "\n")
        print(f"recorded {e['id'] or 'custom'}: {e['title']}")
    elif a.cmd == "list":
        for h in hist[-a.last :]:
            print(f"{h['date']} {h.get('id') or 'custom':8} {h['title']} -> {h['video']}")
    elif a.cmd == "stats":
        used = {h.get("id") for h in hist}
        print(
            f"bank {len(bank)}, used {len(used & set(by_id))}, custom {sum(1 for h in hist if not h.get('id'))}"
        )
        for look in sorted({i["look"] for i in bank}):
            tot = sum(1 for i in bank if i["look"] == look)
            u = sum(1 for i in bank if i["look"] == look and i["id"] in used)
            print(f"  {look:10} {u}/{tot}")


if __name__ == "__main__":
    main()
