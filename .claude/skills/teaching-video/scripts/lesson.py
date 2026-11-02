"""Usage:
  lesson.py check lesson.json
  lesson.py clips lesson.json timeline.json out_dir --format 9x16|16x9
Run: uv run --no-project --python 3.12 --with pypinyin --with opencc-python-reimplemented python scripts/lesson.py ...

check  content gate before any voice or render: sections in order (hook, explain, demo, fix,
       challenge, reinforce), three demo examples, one wrong + one right card in fix, a challenge
       with a >= 3 s pause and an answer card; simplified characters only (opencc t2s); card pinyin
       matches the characters syllable by syllable with tone marks (pypinyin phrase reading;
       一/不 sandhi and a neutral tone on a word's later syllable are accepted); Vietnamese has no
       "!" (the TTS shouts it) and no sentence over 28 syllables without a comma (no breath point);
       at most 4 language switches per beat (each switch is a voice change).
clips  splits the voiced timeline (voice.py synth) into ~10 s muse clips at phrase boundaries and
       writes one prompt per clip for one format, with the teacher block and that format's framing.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

SECTIONS = ["hook", "explain", "demo", "fix", "challenge", "reinforce"]
HERE = Path(__file__).resolve().parent.parent
TONES = {"ā": 1, "á": 2, "ǎ": 3, "à": 4, "ē": 1, "é": 2, "ě": 3, "è": 4, "ī": 1, "í": 2, "ǐ": 3, "ì": 4,
         "ō": 1, "ó": 2, "ǒ": 3, "ò": 4, "ū": 1, "ú": 2, "ǔ": 3, "ù": 4, "ǖ": 1, "ǘ": 2, "ǚ": 3, "ǜ": 4}


def plain(s):
    return s.replace("[", "").replace("]", "")


def hanzi(s):
    return [c for c in plain(s) if "一" <= c <= "鿿"]


def bare(syl):
    """toneless ascii form: lǜ -> lv, nǚ -> nv"""
    out = ""
    for ch in syl:
        if ch in TONES:
            ch = unicodedata.normalize("NFD", ch)[0]
        out += {"ü": "v"}.get(ch, ch)
    return out.replace("ü", "v")


def tone(chunk):
    return next((TONES[c] for c in chunk if c in TONES), 0)


def check_pinyin(zh, py):
    """Errors for a card's pinyin against its characters, consumed syllable by syllable."""
    from pypinyin import Style, lazy_pinyin, pinyin
    chars = hanzi(zh)
    want = lazy_pinyin("".join(chars), style=Style.TONE)
    alts = [p for p in pinyin("".join(chars), style=Style.TONE, heteronym=True)]
    s = re.sub(r"[^a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüv]", "", unicodedata.normalize("NFC", plain(py)).lower())
    errs, warns, pos = [], [], 0
    for i, (c, w) in enumerate(zip(chars, want, strict=True)):
        if c == "儿" and s[pos:pos + 1] == "r" and not s[pos:pos + 2] == "er":
            pos += 1  # erhua written as -r
            continue
        cands = sorted({bare(w)} | {bare(a) for a in alts[i]}, key=len, reverse=True)
        b = next((x for x in cands if bare(s[pos:pos + len(x)]) == x), None)
        if b is None:
            errs.append(f"{c}: expected {w} at '{s[pos:pos + 8]}'")
            return errs, warns
        chunk, pos = s[pos:pos + len(b)], pos + len(b)
        got, exp = tone(chunk), tone(w)
        if got == exp and b == bare(w):
            continue
        if c in "一不" and got in (2, 4):
            continue  # sandhi written as spoken
        if got == 0 and i > 0:
            warns.append(f"{c}: written neutral '{chunk}', dictionary {w}")
        elif any(bare(a) == b and tone(a) == got for a in alts[i]):
            # 比 bì / 喝 hè exist but are wrong here; a card whose rare reading is right sets "py_ok": true
            errs.append(f"{c}: '{chunk}' is a rarer reading; this phrase reads {w}")
        else:
            errs.append(f"{c}: '{chunk}' but should be {w}")
    if pos != len(s):
        errs.append(f"extra pinyin '{s[pos:]}'")
    return errs, warns


def vi_syllables(text):
    return len(re.findall(r"[^\s,.;:!?“”\"'()…—-]+", text))


def check(lesson):
    import opencc
    t2s = opencc.OpenCC("t2s").convert
    errs, warns = [], []
    beats = lesson["beats"]
    secs = [b["section"] for b in beats]
    order = [s for i, s in enumerate(secs) if i == 0 or secs[i - 1] != s]
    if order != SECTIONS:
        errs.append(f"sections must run once each in order {SECTIONS}, got {order}")
    cards = [(b["section"], b["card"]) for b in beats if b.get("card")]
    demo = [c for s, c in cards if s == "demo" and c["type"] == "example"]
    if len(demo) != 3:
        errs.append(f"demo needs exactly 3 example cards, has {len(demo)}")
    marks = {c.get("mark") for s, c in cards if s == "fix"}
    if not {"wrong", "right"} <= marks:
        errs.append("fix needs one card with mark wrong and one with mark right")
    pauses = [x["pause"] for b in beats if b["section"] == "challenge" for x in b["say"] if "pause" in x]
    if not pauses or max(pauses) < 3.0:
        errs.append("challenge needs a {\"pause\": >=3, \"countdown\": true} item")
    if not any(s == "challenge" and c["type"] == "example" for s, c in cards):
        errs.append("challenge needs an answer card (type example) after the pause")
    for n, b in enumerate(beats):
        say = b["say"]
        langs = [("vi" if "vi" in x else "zh") for x in say if "pause" not in x]
        switches = sum(1 for a, c in zip(langs, langs[1:], strict=False) if a != c)
        if switches > 4:
            warns.append(f"beat {n}: {switches} language switches (each is a voice change); rephrase")
        for x in say:
            if "zh" in x:
                if t2s(x["zh"]) != x["zh"]:
                    errs.append(f"beat {n}: traditional characters in {x['zh']} -> {t2s(x['zh'])}")
            if "vi" in x:
                if "!" in x["vi"]:
                    errs.append(f"beat {n}: '!' in Vietnamese makes the voice shout; use '.'")
                for sent in re.split(r"[.?:]", x["vi"]):
                    if vi_syllables(sent) > 28 and "," not in sent:
                        warns.append(f"beat {n}: long sentence with no comma: {sent.strip()[:40]}...")
        c = b.get("card")
        if c and c["type"] == "example":
            for k in ("zh", "py", "vi"):
                if not c.get(k):
                    errs.append(f"beat {n}: example card misses {k}")
            if t2s(plain(c["zh"])) != plain(c["zh"]):
                errs.append(f"beat {n}: traditional characters on card {c['zh']}")
            e, w = check_pinyin(c["zh"], c["py"])
            if c.get("py_ok"):
                w, e = w + e, []
            errs += [f"beat {n} pinyin: {x}" for x in e]
            warns += [f"beat {n} pinyin: {x}" for x in w]
            if c["zh"].count("[") != c["zh"].count("]") or c["py"].count("[") != c["py"].count("]"):
                errs.append(f"beat {n}: unbalanced [accent] marks")
        if c and c.get("mark") == "wrong":
            spoken = [x["zh"] for x in say if "zh" in x]
            if plain(c["zh"]) not in spoken:
                warns.append(f"beat {n}: wrong card text is not spoken in this beat")
    return errs, warns


def zh_pinyin(zh, lesson):
    for b in lesson["beats"]:
        c = b.get("card") or {}
        if c.get("zh") and plain(c["zh"]) == zh:
            return plain(c["py"])
    from pypinyin import Style, lazy_pinyin
    return " ".join(lazy_pinyin(zh, style=Style.TONE))


FRAMING = {
    "9x16": ("9:16", "Vertical 9:16 frame. She stands centred, framed from the waist up, facing the lens. Her head sits in "
             "the upper third (top of her hair about 8 % below the frame top). Her face, neck and shoulders stay in the "
             "upper half of the frame and are never covered by her hands. Her hands stay low, resting loosely together "
             "at her waist near the bottom edge, with only small, calm gestures there (text is added over her chest "
             "later)."),
    "16x9": ("16:9", "Horizontal 16:9 frame. She stands in the LEFT third of the frame, her face about 25 % from the left "
             "edge, framed from the waist up, body turned very slightly toward frame right, eyes on the lens. The RIGHT 55 % "
             "of the frame is a calm, softly blurred bright wall with nothing on it (text is added there later). She never "
             "walks, leans or reaches into the right half; her open-palm gestures point toward it from the left half."),
}


def clips(lesson, timeline, out, fmt, max_len=9.0):
    out.mkdir(parents=True, exist_ok=True)
    teacher = (HERE / "prompt" / "teacher.txt").read_text()
    size, framing = FRAMING[fmt]
    items = timeline["items"]

    def end(it):  # a repeat pause belongs to the phrase before it: she waits silently in that clip
        return it["end"] + (it.get("repeat") or 0)

    def length(g):
        return end(g[-1]) - g[0]["start"]

    def opens(i):  # a breath group starts here: >= 0.4 s of silence before it in the master
        return i == 0 or items[i]["start"] - end(items[i - 1]) >= 0.4

    groups, cur = [], []
    for i, it in enumerate(items):
        if cur and end(it) - cur[0]["start"] > max_len:
            # cut at the last breath group inside the clip, so a lead-in ("Nói tự nhiên:") stays with its sentence
            k = len(cur) if opens(i) else max((j for j in range(1, len(cur)) if opens(i - len(cur) + j)
                                               and end(cur[j - 1]) - cur[0]["start"] >= 4), default=len(cur))
            groups.append(cur[:k])
            cur = cur[k:]
        cur.append(it)
    if cur:
        if groups and length(cur) < 4 and length(groups[-1]) + length(cur) < max_len:
            groups[-1] += cur
        else:
            groups.append(cur)
    plan = []
    for n, g in enumerate(groups, 1):
        t0 = g[0]["start"] - 0.4
        lines = []
        for it in g:
            a, b = it["start"] - t0, it["end"] - t0
            if it["kind"] == "pause":
                lines.append(f"{a:4.1f}-{b:4.1f} s  SILENT: lips closed in a soft smile, eyebrows raised, small encouraging nod, "
                             "waiting for the viewer to answer. She says nothing.")
            elif it["lang"] == "vi":
                lines.append(f"{a:4.1f}-{b:4.1f} s  says in natural Northern Vietnamese: \"{it['text']}\"")
            else:
                lines.append(f"{a:4.1f}-{b:4.1f} s  says in clear Standard Mandarin{' slowly, syllable by syllable' if it.get('slow') else ''}: "
                             f"\"{it['text']}\" ({zh_pinyin(it['text'], lesson)})")
            if it.get("repeat"):
                r = it["end"] - t0
                lines.append(f"{r:4.1f}-{r + it['repeat']:4.1f} s  SILENT: lips closed, small nod and an inviting open palm, "
                             "letting the viewer repeat. She says nothing.")
        last = g[-1]["end"] + (g[-1].get("repeat") or 0) - t0
        first = ("FIRST FRAME: The attached image is the exact first frame (still.sh). Keep her face, hair, outfit, "
                 "framing, camera position, lighting and background exactly as in it.\n\n") if n == 1 else ""
        prompt = (first + f"TEACHING CLIP - PART {n} of {len(groups)} ({lesson['grammar']}), 10 seconds\n\n"
                  f"CAST: {lesson['teacher']['cast']} Keep her face, hairstyle, outfit and voice identical in every part.\n\n"
                  f"SETTING: {lesson['teacher']['set']}\n\n"
                  f"FRAMING: {framing}\n\n"
                  "SCRIPT (she is alone and speaks to the viewer through the lens; times are seconds into this clip):\n"
                  + "\n".join(lines)
                  + f"\n{last:4.1f}-10.0 s  calm resting pose, mouth closed, soft smile, looking into the lens.\n\n"
                  + teacher)
        f = out / f"clip{n:02d}.txt"
        f.write_text(prompt)
        plan.append({"clip": n, "file": str(f), "items": [it["id"] for it in g], "start": round(t0, 2),
                     "speech": round(last, 2)})
        print(f"clip{n:02d}  {len(g)} items  speech+pauses {last:4.1f} s  (master {t0:6.2f}-{t0 + last:6.2f})")
    (out / "clips.json").write_text(json.dumps({"format": fmt, "size": size, "clips": plan}, indent=1))
    print(f"{len(groups)} clips -> {out}/clips.json; render with SIZE={size} DURATION=10 QUALITY=0")


if __name__ == "__main__":
    cmd, lesson = sys.argv[1], json.load(open(sys.argv[2]))
    if cmd == "check":
        e, w = check(lesson)
        for x in w:
            print("WARN ", x)
        for x in e:
            print("FAIL ", x)
        print("RESULT", "FAIL" if e else "ok")
        sys.exit(1 if e else 0)
    if cmd == "clips":
        fmt = sys.argv[sys.argv.index("--format") + 1]
        clips(lesson, json.load(open(sys.argv[3])), Path(sys.argv[4]), fmt)
