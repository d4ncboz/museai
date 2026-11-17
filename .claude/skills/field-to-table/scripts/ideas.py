#!/usr/bin/env python3
"""Pick the next field-to-table day from a 1000-idea bank, never repeating a subject, setting or thread too soon.

Two banks: cottage (default; ELLIE and Pip in a Western cottage, ideas/cottage.json, ids fc-NNNN, kinds
forage|garden|bake|preserve) and countryside (Chinese countryside, ideas/ideas.json, ids ft-NNNN). Every command takes
--bank cottage|countryside. History is one shared file (ids differ by prefix, so no clash); fresh checks use it as is.

  ideas.py next [--season now|spring|summer|autumn|winter] [--kind KIND] [--n 3] [--bank cottage|countryside]
  ideas.py show ft-0042
  ideas.py stats                        how many ideas per kind / season / subject, how many used
  ideas.py record ft-0042 --video PATH [--slug chestnut-day]
  ideas.py list                         what was delivered

next skips: used ids, any subject of the last 8 videos, the setting of the last 3, the thread of the last 2,
and (for --season now) ideas not in the current season. History: ~/.config/museai/field-to-table-history.json.
"""
import argparse
import collections
import datetime
import json
import sys
from pathlib import Path

BANKS = {"cottage": Path(__file__).resolve().parent.parent / "ideas" / "cottage.json",
         "countryside": Path(__file__).resolve().parent.parent / "ideas" / "ideas.json"}
HISTORY = Path.home() / ".config" / "museai" / "field-to-table-history.json"
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring", 6: "summer", 7: "summer",
           8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}


def load(p, default):
    return json.loads(p.read_text()) if p.exists() else default


def fresh(bank, season=None, kind=None):
    h = load(HISTORY, [])
    used = {e["id"] for e in h}
    subj = {e["subject"] for e in h[-8:]}
    sett = {e["setting"] for e in h[-3:]}
    thr = {e["thread"] for e in h[-2:]}
    return [i for i in bank if i["id"] not in used and i["subject"] not in subj and i["setting"] not in sett
            and i["thread"] not in thr and (not season or i["season"] == season) and (not kind or i["kind"] == kind)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["next", "show", "stats", "record", "list"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--season")
    ap.add_argument("--kind")
    ap.add_argument("--bank", choices=sorted(BANKS), default="cottage")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--video")
    ap.add_argument("--slug")
    a = ap.parse_args()
    bank = load(BANKS[a.bank], [])
    if a.cmd == "next":
        season = SEASONS[datetime.date.today().month] if a.season == "now" else a.season
        got = fresh(bank, season, a.kind)
        if not got:
            sys.exit("no fresh idea: widen --season/--kind or add subjects in gen_ideas.py")
        print(json.dumps(got[: a.n] if a.n > 1 else got[0], indent=1, ensure_ascii=False))
    elif a.cmd == "show":
        print(json.dumps(next(i for i in bank if i["id"] == a.id), indent=1, ensure_ascii=False))
    elif a.cmd == "stats":
        h = load(HISTORY, [])
        for f in ("kind", "season", "setting", "thread"):
            print(f, dict(collections.Counter(i[f] for i in bank)))
        print(f"bank {a.bank}: {len(bank)} ideas, {len({i['subject'] for i in bank})} subjects, {len(h)} used")
    elif a.cmd == "list":
        for e in load(HISTORY, []):
            print(f"{e['date']}  {e['id']}  {e['subject']} · {e['setting']} · {e['thread']}  {e.get('video', '')}")
    else:
        i = next(i for i in bank if i["id"] == a.id)
        h = load(HISTORY, [])
        h.append({k: i[k] for k in ("id", "subject", "setting", "thread", "season")} |
                 {"slug": a.slug, "video": a.video, "date": datetime.date.today().isoformat()})
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(h, indent=1, ensure_ascii=False) + "\n")
        print(f"recorded {i['id']}")


if __name__ == "__main__":
    main()
