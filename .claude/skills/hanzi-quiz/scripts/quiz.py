"""Usage: quiz.py check quizzes/<topic>.json
         quiz.py scenes quizzes/<topic>.json work/<topic>/scenes [--only N]
         quiz.py clips quizzes/<topic>.json work/<topic>/scenes
Run: uv run --no-project --python 3.12 --with pypinyin --with hanzidentifier --with pillow python scripts/quiz.py ...

check   content gate. Prints FAIL/WARN lines and `RESULT ok|fail`:
        5-8 words, simplified hanzi only, pinyin with tone marks that matches the hanzi (pypinyin,
        heteronyms accepted), two decoys per word that differ from the answer, a memory trick, a
        no-text scene, hook text <= 7 words with no greeting / title / invented statistic.
scenes  one 1080x1920 photo per word through museai /v1/images/generations (no text in the frame),
        cover-cropped to 9:16 -> scenes/01.png ... Existing files are kept (delete one to redo it).
        Env: MUSEAI_HOME=~/Work/museai MUSEAI_BASE=http://127.0.0.1:18610
clips   one muse-video prompt per word -> scenes/NN.txt (scene + its `motion`, one slow camera move,
        10 s, no text, no talking); render each from its photo with ../muse-video (SKILL.md step 2).
"""
import base64
import io
import json
import os
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

GREETING = re.compile(r"\b(hi|hello|welcome|today|let's learn|lesson)\b|xin chào|chào các bạn|hôm nay", re.I)
STAT = re.compile(r"\d+\s*%")
TONE = re.compile(r"[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]")
NO_TEXT = "No text, letters, signs, logos, subtitles or watermarks anywhere in the frame."


def strip_tones(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)).replace("ü", "v")


def pinyin_ok(hanzi, py):
    from pypinyin import Style, pinyin
    want = re.sub(r"[\s'·-]", "", py.lower())
    # phrase reading plus every single-character reading (pypinyin reads 照片 as zhàopiān only)
    readings = [{*ph, *pinyin(ch, style=Style.TONE, heteronym=True)[0]}
                for ph, ch in zip(pinyin(hanzi, style=Style.TONE, heteronym=True), hanzi, strict=True)]
    # neutral-tone syllables (李 in 行李) are written toneless; accept toned or toneless per syllable
    options = [""]
    for syl in readings:
        options = [o + r for o in options for r in {*syl, *map(strip_tones, syl)}][:256]
    return want in options


def simplified(text):
    import hanzidentifier
    return hanzidentifier.has_chinese(text) and hanzidentifier.is_simplified(text)


def check(path):
    q = json.loads(Path(path).read_text())
    fails, warns = [], []
    words = q.get("words", [])
    if not 5 <= len(words) <= 8:
        fails.append(f"{len(words)} words; use 5-8 (6 fits 55-60 s)")
    hook = q.get("hook", {})
    ht = hook.get("text", "")
    if not ht or len(ht.split()) > 7:
        fails.append(f"hook.text must be 1-7 words: {ht!r}")
    for k in ("text", "say"):
        if GREETING.search(hook.get(k, "")):
            fails.append(f"hook.{k} opens with a greeting / title: {hook.get(k)!r} (open on the challenge)")
        if STAT.search(hook.get(k, "")):
            fails.append(f"hook.{k} quotes a percentage we cannot back: {hook.get(k)!r}")
    if q.get("sub"):
        sub = q["sub"]
        for obj, k in ((hook, "text"), (hook, "boss_teaser"), (q.get("outro", {}), "text"), (q.get("outro", {}), "cta")):
            if obj.get(k) and not obj.get(f"{k}_{sub}"):
                fails.append(f"sub {sub!r} set but {k}_{sub} missing")
        if len(q.get(f"rehooks_{sub}", [])) != len(q.get("rehooks", [])):
            fails.append(f"rehooks_{sub} must match rehooks one to one")
    if "!" in hook.get("say", "") + q.get("outro", {}).get("say", ""):
        fails.append("'!' in spoken text (TTS shouts it); use '.' or '?'")
    seen = set()
    for i, w in enumerate(words, 1):
        h, py = w.get("hanzi", ""), w.get("pinyin", "")
        tag = f"#{i} {h}"
        if h in seen:
            fails.append(f"{tag}: duplicate word")
        seen.add(h)
        if not re.fullmatch(r"[一-鿿]{1,4}", h):
            fails.append(f"{tag}: hanzi must be 1-4 CJK characters")
        if not simplified(h):
            fails.append(f"{tag}: traditional characters; use simplified")
        if not TONE.search(py):
            fails.append(f"{tag}: pinyin {py!r} has no tone marks")
        elif not pinyin_ok(h, py):
            fails.append(f"{tag}: pinyin {py!r} does not match the hanzi")
        for k in ("meaning", "trick", "scene"):
            if not w.get(k):
                fails.append(f"{tag}: missing {k}")
        if q.get("sub"):
            for k in ("meaning", "trick"):
                if not w.get(f"{k}_{q['sub']}"):
                    fails.append(f"{tag}: sub {q['sub']!r} set but {k}_{q['sub']} missing")
        d = w.get("decoys", [])
        if len(d) != 2:
            fails.append(f"{tag}: needs exactly 2 decoys [[hanzi, pinyin], ...]")
        for dh, dpy in d:
            if dh == h:
                fails.append(f"{tag}: decoy equals the answer")
            elif not pinyin_ok(dh, dpy):
                fails.append(f"{tag}: decoy pinyin {dpy!r} does not match {dh}")
        if len(w.get("trick", "")) > 48:
            warns.append(f"{tag}: trick > 48 chars wraps to 3 lines")
        if re.search(r"\b(sign|text|menu|label|written)\b", w.get("scene", ""), re.I) and "no readable" not in w["scene"]:
            warns.append(f"{tag}: scene mentions text; muse will draw garbled letters")
    for f in fails:
        print("FAIL", f)
    for w in warns:
        print("WARN", w)
    print("RESULT", "fail" if fails else "ok")
    return 1 if fails else 0


def scenes(path, out, only=None):
    from PIL import Image
    q = json.loads(Path(path).read_text())
    home = Path(os.environ.get("MUSEAI_HOME", Path.home() / "Work/museai"))
    key = (home / "data/api_key").read_text().strip()
    base = os.environ.get("MUSEAI_BASE", "http://127.0.0.1:18610")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for i, w in enumerate(q["words"], 1):
        dst = out / f"{i:02d}.png"
        if (only and i != only) or dst.exists():
            continue
        prompt = (f"Vertical 9:16 photo, real camera, natural light, vivid but true colours. {w['scene']} "
                  f"The subject fills the middle of the frame; the top fifth is calm sky, wall or soft "
                  f"background. {NO_TEXT}")
        body = json.dumps({"prompt": prompt, "n": 1, "size": "1080x1920", "response_format": "b64_json"}).encode()
        req = urllib.request.Request(f"{base}/v1/images/generations", body,
                                     {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.load(r)["data"][0]["b64_json"]
        im = Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")
        s = max(1080 / im.width, 1920 / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        x, y = (im.width - 1080) // 2, (im.height - 1920) // 2
        im.crop((x, y, x + 1080, y + 1920)).save(dst)
        print(dst)


def clips(path, out):
    q = json.loads(Path(path).read_text())
    for i, w in enumerate(q["words"], 1):
        dst = Path(out) / f"{i:02d}.txt"
        dst.write_text(
            f"Vertical 9:16, 10 seconds, one continuous shot, real footage look, natural light. {w['scene']} "
            f"Motion: {w.get('motion', 'one slow, level push-in; the scene lives gently (light, wind, people far away)')}. "
            f"Keep the first frame's composition; the subject stays in the middle, the top fifth calm. "
            f"Slow, smooth, steady camera; no cuts, no zoom jumps. Nobody speaks to camera. {NO_TEXT}\n")
        print(dst)


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:]
    if cmd == "check":
        sys.exit(check(rest[0]))
    if cmd == "scenes":
        only = int(rest[rest.index("--only") + 1]) if "--only" in rest else None
        scenes(rest[0], rest[1], only)
    elif cmd == "clips":
        clips(rest[0], rest[1])
    else:
        sys.exit(__doc__)
