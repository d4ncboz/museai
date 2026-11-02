"""Idea bank + history for gown-run videos, so no video repeats an earlier gown + place.

Bank: ../ideas.json (100 ideas, scripts/gen_ideas.py). History: ~/.config/museai/gown-run-history.json,
one entry per DELIVERED video (idea id or custom idea, title, gown, colour, place, shots, video, date).

  python3 scripts/ideas.py next [--gown cape] [--colour red] [--place Iceland] [--music disco] [--n 3]
  python3 scripts/ideas.py show gr-042
  python3 scripts/ideas.py check --gown "..." --colour red --place "..."
  python3 scripts/ideas.py record gr-042 --video ~/Desktop/gown-x.mp4 [--shots shots.json]
  python3 scripts/ideas.py record custom --title "..." --gown "..." --colour ... --place "..." --video ...
  python3 scripts/ideas.py list [--last 20]
  python3 scripts/ideas.py stats

next: the first unused ideas (bank order) that also differ from the last 5 videos in gown and place and
from the last 2 in colour and the last 3 in music style, so a run of posts never looks or sounds samey.
check exits 1 (DUPLICATE) when an earlier video has the same gown + place, 2 (SIMILAR) on the same gown or
place in the last 5, the same colour in the last 2 or the same music style in the last 3.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BANK = SKILL / "ideas.json"
HIST = Path.home() / ".config/museai/gown-run-history.json"
FIELDS = ("title", "gown", "colour", "place", "music")
REQUIRED = ("title", "gown", "colour", "place")


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def norm(x):
    return (x or "").strip().lower()


def verdict(idea, hist):
    """(code, reason): 0 fresh, 1 duplicate, 2 too similar to recent videos."""
    for h in hist:
        if h.get("id") and h["id"] == idea.get("id"):
            return 1, f"idea {h['id']} already used ({h['date']}, {h['video']})"
        if norm(h["gown"]) == norm(idea["gown"]) and norm(h["place"]) == norm(idea["place"]):
            return 1, f"same gown + place as {h['date']} {h['title']}"
    for h in hist[-5:]:
        if norm(h["gown"]) == norm(idea["gown"]):
            return 2, f"gown used in the last 5 videos ({h['date']} {h['title']})"
        if norm(h["place"]) == norm(idea["place"]):
            return 2, f"place used in the last 5 videos ({h['date']} {h['title']})"
    for h in hist[-2:]:
        if idea.get("colour") and norm(h.get("colour")) == norm(idea["colour"]):
            return 2, f"colour used in the last 2 videos ({h['date']} {h['title']})"
    for h in hist[-3:]:
        if idea.get("music") and norm(h.get("music")) == norm(idea["music"]):
            return 2, f"music style {idea['music']} used in the last 3 videos ({h['date']} {h['title']})"
    return 0, "fresh"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next")
    for f in ("gown", "colour", "place", "music"):
        n.add_argument(f"--{f}")
    n.add_argument("--n", type=int, default=1)
    sub.add_parser("show").add_argument("id")
    for name in ("check", "record"):
        p = sub.add_parser(name)
        if name == "record":
            p.add_argument("id", help="gr-NNN or 'custom'")
            p.add_argument("--video", required=True)
            p.add_argument("--shots", help="JSON list of the shot briefs actually used")
        for f in FIELDS:
            p.add_argument(f"--{f}")
    sub.add_parser("list").add_argument("--last", type=int, default=20)
    sub.add_parser("stats")
    a = ap.parse_args()

    bank = load(BANK, [])
    by_id = {i["id"]: i for i in bank}
    hist = load(HIST, [])

    if a.cmd == "next":
        out = []
        for idea in bank:
            if any(getattr(a, f) and norm(getattr(a, f)) not in norm(idea[f]) for f in ("gown", "colour", "place", "music")):
                continue
            if verdict(idea, hist)[0] == 0:
                out.append(idea)
            if len(out) == a.n:
                break
        if not out:
            sys.exit("no fresh idea matches; loosen the filters or add gowns/places to gen_ideas.py")
        print(json.dumps(out if a.n > 1 else out[0], ensure_ascii=False, indent=1))
    elif a.cmd == "show":
        print(json.dumps(by_id.get(a.id) or sys.exit(f"no idea {a.id}"), ensure_ascii=False, indent=1))
    elif a.cmd == "check":
        code, why = verdict({k: getattr(a, k) for k in FIELDS}, hist)
        print(["FRESH", "DUPLICATE", "SIMILAR"][code] + f": {why}")
        sys.exit(code)
    elif a.cmd == "record":
        if a.id == "custom":
            idea = {k: getattr(a, k) for k in FIELDS}
            missing = [k for k in REQUIRED if not idea[k]]
            if missing:
                sys.exit(f"custom record needs --{' --'.join(missing)}")
            idea["id"] = None
        else:
            idea = dict(by_id.get(a.id) or sys.exit(f"no idea {a.id}"))
            if a.music:  # another style than the bank's was used
                idea["music"] = a.music
        code, why = verdict(idea, hist)
        if code == 1:
            print(f"warning: recording a duplicate ({why})", file=sys.stderr)
        entry = {k: idea.get(k) for k in ("id", *FIELDS)}
        entry["shots"] = json.loads(Path(a.shots).read_text()) if a.shots else idea.get("shots", [])
        entry["video"] = str(Path(a.video).expanduser().resolve())
        entry["date"] = datetime.date.today().isoformat()
        hist.append(entry)
        HIST.parent.mkdir(parents=True, exist_ok=True)
        HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=1) + "\n")
        print(f"recorded {entry['id'] or 'custom'}: {entry['title']} ({len(hist)} videos in history)")
    elif a.cmd == "list":
        for h in hist[-a.last:]:
            print(f"{h['date']}  {h['id'] or 'custom':7}  {h['title']}  → {h['video']}")
        if not hist:
            print("no videos yet")
    elif a.cmd == "stats":
        used = {h["id"] for h in hist if h.get("id")}
        print(f"{len(hist)} videos delivered, {len(used)}/{len(bank)} bank ideas used, "
              f"{sum(verdict(i, hist)[0] == 0 for i in bank)} fresh now")


if __name__ == "__main__":
    main()
