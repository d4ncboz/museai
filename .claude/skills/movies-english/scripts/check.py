#!/usr/bin/env python3
"""Lint the script library: python3 scripts/check.py [batch.json ...] -> exit 1 on any ERROR."""
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CAST = json.loads((SKILL / "series/cast.json").read_text())
FRAMINGS = {"wide", "medium", "close", "ecu", "two-shot"}


def words(s):
    return re.findall(r"[a-z']+", s.lower())


def stem(w):
    return re.sub(r"(ing|ed|es|s)$", "", w.replace("'s", ""))


def has_phrase(line, phrase):
    lw, pw = [stem(w) for w in words(line)], [stem(w) for w in words(phrase)]
    pw = [w for w in pw if w not in ("someone", "something", "one's", "sb", "sth")]
    return all(w in lw for w in pw)


def main(files):
    files = files or sorted(str(p) for p in (SKILL / "library").glob("batch_*.json"))
    errs, ids, phrases, n = [], set(), {}, 0
    for f in files:
        for s in json.loads(Path(f).read_text()):
            n += 1
            sid = s.get("id", "?")

            def e(m, f=f, sid=sid):
                errs.append(f"{Path(f).name} {sid}: {m}")

            if sid in ids:
                e("duplicate id")
            ids.add(sid)
            ph = s["phrase"]["en"].lower().strip()
            if ph in phrases:
                e(f"phrase {ph!r} also in {phrases[ph]}")
            phrases[ph] = sid
            for k in ("title_en", "title_vi", "genre", "level", "cast", "setting", "phrase", "shots", "twist"):
                if k not in s:
                    e(f"missing {k}")
            for k in s["cast"]:
                if k not in CAST:
                    e(f"unknown cast {k}")
                elif s.get("wardrobe", {}).get(k) and s["wardrobe"][k] not in CAST[k]["wardrobe"]:
                    e(f"unknown wardrobe {k}.{s['wardrobe'][k]}")
            shots = s["shots"]
            total = sum(x["sec"] for x in shots)
            lines = [x["line"] for x in shots if x.get("line")]
            if not 4 <= len(shots) <= 12:
                e(f"{len(shots)} shots")
            if not 14 <= total <= 32:
                e(f"{total} s total")
            if not 2 <= len(lines) <= 6:
                e(f"{len(lines)} lines")
            for w in s.get("words", []):
                if not w.get("en") or not w.get("vi"):
                    e(f"word {w} needs en and vi")
            for x in shots:
                if not 0.5 <= x["sec"] <= 9:
                    e(f"{x['id']} {x['sec']} s")
                if x.get("framing") not in FRAMINGS:
                    e(f"{x['id']} framing {x.get('framing')}")
                ln = x.get("line")
                if ln:
                    if len(ln["en"].split()) > 8:
                        e(f"{x['id']} line over 8 words")
                    if ln["who"] not in x.get("cast", []):
                        e(f"{x['id']} speaker {ln['who']} not in shot cast")
                    if x.get("framing") == "wide":
                        e(f"{x['id']} line in a wide shot")
            if not any(has_phrase(ln["en"], ph) for ln in lines):
                e(f"phrase {ph!r} not spoken")
    for m in errs:
        print("ERROR", m)
    print(f"{n} scripts, {len(phrases)} phrases, {len(errs)} errors")
    return not errs


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
