"""Bẫy Hán-Việt word bank: pick the next word, check the bank, write the episode brief, log what shipped.

Usage (from .claude/skills/hanviet-trap/):
  python3 scripts/trap.py list                  every word, kind, and the date it shipped
  python3 scripts/trap.py next                  the first word never shipped (bank order)
  python3 scripts/trap.py brief <id> <work_dir> muse prompts for the 3 clips (brief.txt) and the overlay
                                                plan for fx.py (plan.json): hook, name tags, trap stamp,
                                                truth card, A/B poll, next-episode teaser, title, file name
  python3 scripts/trap.py done <id> <final.mp4> log a delivered episode in history.json
  uv run --no-project --python 3.12 --with pypinyin --with opencc-python-reimplemented \\
      python scripts/trap.py check             every bank entry: fields, simplified hanzi, pinyin vs
                                                characters (teaching-video lesson.py), the word in its
                                                line/explain/quiz, no "!", hook length;
                                                "py_ok": ["line", ...] accepts a reading checked by hand
"""
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BANK = HERE / "bank.json"
HISTORY = HERE / "history.json"
TEACHING = HERE.parent / "teaching-video"
FIELDS = ("id", "kind", "zh", "py", "hv", "assumed", "real", "say_instead", "partner", "speaker",
          "line", "react", "explain", "replay", "quiz", "hook", "cast", "set")
BLOCKS = ("setup", "line", "react", "explain", "replay", "quiz")
KINDS = {"meaning", "tone", "rude"}
HOOK_WORDS = 8  # muse-video hook rule

# the recurring pair is the EVERYDAY CHINESE EP49 couple in everyday clothes (refs/linh-hao.jpg two-shot,
# refs/linh-solo.jpg Linh alone, same hallway). Not the EP46 party couple: user, 2026-11-02, "normal
# character, not birthday theme please". Same faces and voices every episode.
REFS = HERE / "refs"
LINH = ("Linh, Vietnamese woman, 21, very beautiful in a natural, fresh way: delicate youthful oval face, bright "
        "clear eyes, light natural makeup with rosy lips, long silky black hair in soft waves, small pearl "
        "earrings")
HAO = ("Hạo, Chinese man, 24, handsome, friendly, ordinary everyday look, short neat black hair, clean-shaven, "
       "camera-shy, never looks into the lens")
DRESSES = ["a soft peach silk blouse with a bow at the neck and cream wide-leg trousers", "an emerald satin slip dress with a cream cardigan",
           "a pastel-pink tweed mini dress", "a sky-blue flowy midi dress with puff sleeves",
           "a black velvet dress with a white collar", "a lilac chiffon wrap dress",
           "a red qipao-inspired modern mini dress", "a butter-yellow knit dress"]
REF_SET = ("a bright, plain apartment hallway with white walls, a light wooden door and a small potted plant, "
           "soft natural daylight, exactly as in the first frame")
FITS = ["a navy crew-neck sweater over a white T-shirt", "a navy bomber jacket over a white T-shirt",
        "a camel overcoat over a black turtleneck", "a crisp white shirt with rolled sleeves",
        "a charcoal knit sweater over a collared shirt", "a black leather jacket over a grey T-shirt",
        "a beige trench coat over a white shirt", "a dark-green bomber jacket over a black T-shirt"]


def bank():
    return json.loads(BANK.read_text())


def history():
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def entry(wid):
    e = next((x for x in bank() if x["id"] == wid), None)
    if not e:
        sys.exit(f"no word {wid!r} in bank.json")
    return e


def check():
    sys.path.insert(0, str(TEACHING / "scripts"))
    import opencc
    from lesson import check_pinyin
    t2s = opencc.OpenCC("t2s").convert
    errs, warns, ids = [], [], set()
    for e in bank():
        wid = e.get("id", "?")
        for k in FIELDS:
            if not e.get(k):
                errs.append(f"{wid}: missing {k}")
        if wid in ids:
            errs.append(f"{wid}: duplicate id")
        ids.add(wid)
        if e.get("kind") not in KINDS:
            errs.append(f"{wid}: kind {e.get('kind')!r} not in {sorted(KINDS)}")
        if e.get("speaker") not in ("partner", "linh"):
            errs.append(f"{wid}: speaker must be partner or linh")
        if e.get("speaker") == "linh" and not e.get("setup"):
            errs.append(f"{wid}: speaker linh needs a partner setup line")
        if len(e["hook"].split()) > HOOK_WORDS:
            errs.append(f"{wid}: hook has {len(e['hook'].split())} words, keep <= {HOOK_WORDS}")
        if e["zh"] not in e["hook"]:
            errs.append(f"{wid}: hook must show {e['zh']}")
        pairs = [("word", e["zh"], e["py"]), ("say_instead", e["say_instead"]["zh"], e["say_instead"]["py"])]
        for k in BLOCKS:
            if k not in e:
                continue
            pairs.append((k, e[k]["zh"], e[k]["py"]))
            if "!" in e[k]["vi"]:
                errs.append(f"{wid}: '!' in {k} Vietnamese makes the voice shout")
        for k in ("line", "explain", "quiz"):
            if e["zh"] not in e[k]["zh"]:
                errs.append(f"{wid}: {k} does not use {e['zh']}")
        for what, zh, py in pairs:
            if t2s(zh) != zh:
                errs.append(f"{wid} {what}: traditional characters {zh} -> {t2s(zh)}")
            e_, w_ = check_pinyin(zh, py)
            if what in e.get("py_ok", []):  # reading checked by hand; pypinyin's phrase guess is wrong here
                w_, e_ = w_ + e_, []
            errs += [f"{wid} {what} pinyin: {x}" for x in e_]
            warns += [f"{wid} {what} pinyin: {x}" for x in w_]
    for x in warns:
        print("WARN ", x)
    for x in errs:
        print("FAIL ", x)
    print(f"{len(ids)} words")
    print("RESULT", "FAIL" if errs else "ok")
    return not errs


def say(who, b):
    return f"{who}:\n{b['zh']}\n{b['py']}\n{b['vi']}\n"


def script(e):
    """(speaker, block) in spoken order; clip A ends on the misreading, clip B fixes it"""
    p, w = "PARTNER", "LINH"
    a = ([(p, e["setup"]), (w, e["line"]), (p, e["react"])] if e["speaker"] == "linh"
         else [(p, e["line"]), (w, e["react"])])
    b = [(p, e["explain"]), (w, e["replay"])]
    return a, b


def brief(e, out):
    shipped = history()
    n = len(shipped) + 1
    later = [x for x in bank() if x["id"] not in {h["id"] for h in shipped} and x["id"] != e["id"]]
    hao = e["cast"] == "hao"
    # The image API takes no reference image, so Hạo episodes start from the EP49 frame itself:
    # its clothes and set, not the rotation.
    dress = DRESSES[0] if hao else DRESSES[(n - 1) % len(DRESSES)]
    set_ = REF_SET if hao else e["set"]
    partner = f"{HAO}, wearing {FITS[0]}" if hao else e["cast"]
    a, b = script(e)
    react_mood = ("Linh looks puzzled, then confidently wrong" if e["speaker"] == "partner"
                  else "the partner looks shocked, eyebrows up, then laughs kindly")
    cast = (f"{LINH}, wearing {dress}. Pleasant young female Mandarin voice with a light, natural "
            f"learner's warmth.\nPARTNER: {partner}. {'Warm male' if hao else 'Natural native'} Mandarin voice.\n"
            + ("The first frame shows Linh (screen left) and Hạo (screen right): keep their faces, hair, clothes "
               "and the place exactly as in it.\n" if hao else
               "The woman is the same woman as in the attached reference image: identical face, age and hairstyle; "
               "only the dress and the place change.\n")
            + "Clothing stays consistent within this episode.\n"
            f"Set: {set_}. Linh SCREEN LEFT, partner SCREEN RIGHT. No moving background people. "
            "No object exchanges.")
    rules = (
        "VOICE AND LIP SYNC\n"
        "Natural Standard Mandarin (Putonghua), accurate tones, normal conversational speed throughout. "
        "Speak ONLY the Chinese dialogue; never read pinyin, Vietnamese or instructions. Replies follow within "
        "0.15-0.3 s. Each line is spoken exactly once, as written: nobody adds, repeats or rephrases a line, and after the last line both hold a silent smile until the end. Strict speaker assignment: only the speaker's mouth moves; the listener's mouth stays "
        "relaxed and closed.\n\n"
        "ACTING AND CAMERA\n"
        "Locked medium two-shot, both framed from the waist up with headroom (head tops below 25 % of the frame). "
        "Faces three-quarter to the camera, never side profile; eyes on each other. Expressive faces: "
        f"{react_mood}. Still hands, no nodding, pointing or waving. No cuts, zooms or pans.\n\n"
        "AUDIO\nClean voices only. No music, no sound effects, no ambience (added in post).")
    head = ("NO TEXT ON SCREEN\nCreate a 10s vertical 9:16 video, 1080x1920. Photorealistic adults, natural "
            "skin, soft flattering light.\n\nCAST AND SET\n" + cast + "\n\n" + rules + "\n\nSCRIPT\n")
    clip_a = head + "The first speaker starts within 0.2 s of the first frame.\n\n" + "\n".join(say(w, x) for w, x in a)
    clip_b = head + "\n".join(say(w, x) for w, x in b)
    clip_c = (f"NO TEXT ON SCREEN\nCreate a 6s vertical 9:16 video, 1080x1920.\n{LINH}, wearing {dress}, "
              f"alone in the same set ({set_}), centered, facing the camera with eyes on the lens from the first frame, head top below 20 % of the frame. "
              "She is alone for all 6 seconds; nobody else enters. Playful small smile, raises one eyebrow, "
              "asks the viewer:\n"
              f"{e['quiz']['zh']}什么意思？\n{e['quiz']['py'].rstrip('.。')}, shénme yìsi?\n"
              "She says only this one line, nothing before or after it. After the last syllable she holds a closed-mouth smile, eyes on the lens, until the end. Clean voice, no music.")
    out.mkdir(parents=True, exist_ok=True)
    (out / "A.txt").write_text(clip_a + "\n")
    (out / "B.txt").write_text(clip_b + "\n")
    (out / "C.txt").write_text(clip_c + "\n")
    title = f"{e['zh']} không phải {e['hv']}"
    plan = {
        "episode": n, "id": e["id"], "speaker": e["speaker"],
        "hook": e["hook"],
        "tags": [{"name": "Linh", "flag": "VN", "role": "du học sinh Việt"},
                 {"name": e["partner"].split(" (")[0], "flag": "CN", "role": "bạn Trung Quốc" if hao else "người bản xứ"}],
        "ref": str(REFS / "linh-hao.jpg"), "ref_solo": str(REFS / "linh-solo.jpg"),
        "stamp": {"zh": e["zh"], "py": e["py"], "hv": e["hv"], "assumed": e["assumed"]},
        "truth": {"zh": e["zh"], "py": e["py"], "real": e["real"],
                  "instead": e["say_instead"], "assumed": e["assumed"].split(",")[0]},
        "poll": {"zh": e["quiz"]["zh"], "py": e["quiz"]["py"], "a": e["assumed"].split(",")[0],
                 "b": e["real"].split(";")[0].split(",")[0], "answer": e["quiz"]["vi"]},
        "teaser": f"Tập sau: {later[0]['zh']} ≠ {later[0]['hv']}" if later else "",
        "cues": [[w.lower(), x["zh"], x["py"], x["vi"]] for w, x in a + b],
        "title": f"Bẫy Hán-Việt {n:02d} | {e['hook']}",
        "file": f"Bẫy Hán-Việt {n:02d} - {title}.mp4",
        "dress": dress,
    }
    if e.get("note"):
        plan["note"] = e["note"]
    (out / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {out}/A.txt B.txt C.txt plan.json  (episode {n:02d}, {e['zh']}, Linh in {dress})")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "next"
    shipped = {h["id"]: h["date"] for h in history()}
    if cmd == "list":
        for e in bank():
            print(f"{e['id']:12s} {e['kind']:8s} {e['zh']:5s} {e['hv']:16s} -> {e['real']:38s} {shipped.get(e['id'], '')}")
    elif cmd == "next":
        e = next((x for x in bank() if x["id"] not in shipped), None)
        if not e:
            sys.exit("every bank word has shipped: add new ones to bank.json (then run check)")
        print(json.dumps(e, ensure_ascii=False, indent=1))
    elif cmd == "check":
        sys.exit(0 if check() else 1)
    elif cmd == "brief":
        e = entry(sys.argv[2])
        if e["id"] in shipped:
            print(f"WARN {e['id']} already shipped on {shipped[e['id']]}")
        brief(e, Path(sys.argv[3]).expanduser())
    elif cmd == "done":
        e, final = entry(sys.argv[2]), sys.argv[3]
        h = [x for x in history() if x["id"] != e["id"]]
        h.append({"id": e["id"], "zh": e["zh"], "date": datetime.date.today().isoformat(), "file": Path(final).name})
        HISTORY.write_text(json.dumps(h, ensure_ascii=False, indent=1) + "\n")
        print(f"logged {e['id']} ({len(h)} shipped)")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
