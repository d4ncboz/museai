#!/usr/bin/env python3
"""American Everyday Stories: check an episode file, then build its production package.

  python3 scripts/episode.py check  episode.json            # gates; exit 1 on any ERROR
  python3 scripts/episode.py build  episode.json WORK       # prompts, subtitles, package, render.sh
  python3 scripts/episode.py still  KEY WORK [wardrobe]     # JSON body for a character reference still
  python3 scripts/episode.py record episode.json            # append the episode to the ledger

Paths are relative to the skill folder. SERIES=series (default) picks the bible/cast/ledger folder.
Characters always come from cast.json, so a face, outfit or voice is never retyped per shot."""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SERIES = SKILL / os.environ.get("SERIES", "series")
WPS = 145 / 60  # natural American conversational pace, words per second
LEAD, GAP, TAIL = 0.6, 0.5, 0.6  # silence before the first line, between lines, after the last
MAX_SHOT, MIN_SHOT = 10, 3  # one muse render = one shot of at most 10 s
EN_MAX, ZH_MAX, WORDS_MAX = 84, 36, 20  # two subtitle rows per language; longer lines are split


def load(path):
    return json.loads(Path(path).read_text())


def words(text):
    return len(re.findall(r"[A-Za-z0-9'’]+", text))


def line_secs(text):
    return words(text) / WPS


def shot_timeline(shot):
    """[(start, end, line)] inside the shot, at the natural pace with LEAD/GAP before each line."""
    t, out = LEAD, []
    for ln in shot.get("lines", []):
        d = line_secs(ln["en"])
        out.append((t, t + d, ln))
        t += d + GAP
    return out


def episode_cues(ep):
    """Provisional subtitle cues over the whole episode: [[start, end, en, zh, KEY], ...]."""
    cues, off = [], 0.0
    for shot in ep["shots"]:
        for s, e, ln in shot_timeline(shot):
            cues.append([round(off + s, 2), round(off + e, 2), ln["en"], ln["zh"], ln["who"]])
        off += shot["seconds"]
    return cues


FACE_MARKS = re.compile(r"\bscar\b|uneven (front )?teeth|gap in (his|her) teeth|gapped teeth|crooked teeth", re.I)
IN_CAR = re.compile(r"\b(inside|in) the (cab|car)\b|\b(cab|front seat|bench seat) of\b", re.I)


def check(ep_path):
    ep, cast, ledger = load(ep_path), load(SERIES / "cast.json"), load(SERIES / "ledger.json")
    banned = {k: v for k, v in load(SKILL / "references/anachronisms.json").items() if not k.startswith("_")}
    errs, warns = [], []
    year = date.fromisoformat(ep["date"]).year
    for f in ("episode", "title_vi", "title_en", "premise", "date", "season", "location", "situation",
              "title_card", "beats", "shots", "continuity_update"):
        if f not in ep:
            errs.append(f"missing field `{f}`")
    for b in ("opening", "goal", "obstacle", "turn", "ending"):
        if not ep.get("beats", {}).get(b):
            errs.append(f"beats.{b} empty: every episode needs opening, goal, obstacle, turn, ending")
    for k, c in cast.items():
        if not k.startswith("_") and (m := FACE_MARKS.search(c.get("identity", ""))):
            errs.append(f"{k}: identity names a {m.group(0)!r}: muse draws it as a mark or crooked teeth "
                        "(references/faces.md 2); use a mole, a dimple or a brow height")
    for s in ep["shots"]:
        if len(s.get("cast", [])) > 1 and IN_CAR.search(s.get("place", "")):
            for need, why in (("of the picture", "say who sits on the LEFT / RIGHT of the picture (a person's own "
                               "left/right mirrors the seating)"), ("dashboard", "name the dashboard and steering "
                               "wheel between camera and people, or the cab floats like a bus")):
                if need not in s.get("framing", ""):
                    errs.append(f"{s.get('id')}: car two-shot framing must {why}; see SKILL.md 'Car scenes'")
    runtime = sum(s["seconds"] for s in ep["shots"])
    if not 120 <= runtime <= 180:
        errs.append(f"runtime {runtime:.0f} s outside 120-180 s")
    spoken = sum(words(ln["en"]) for s in ep["shots"] for ln in s.get("lines", []))
    lo, hi = runtime * 1.45, runtime * 2.2  # 220-330 words for 150 s
    if spoken > runtime * 2.6:
        errs.append(f"{spoken} spoken words in {runtime:.0f} s: too dense (aim {lo:.0f}-{hi:.0f})")
    elif not lo <= spoken <= hi:
        warns.append(f"{spoken} spoken words in {runtime:.0f} s (aim {lo:.0f}-{hi:.0f})")
    t = 0.0
    first_line_at = None
    for shot in ep["shots"]:
        sid, sec = shot.get("id", "?"), shot["seconds"]
        for f in ("id", "seconds", "place", "time", "framing", "action", "camera", "ambience"):
            if not shot.get(f):
                errs.append(f"{sid}: missing `{f}`")
        if not MIN_SHOT <= sec <= MAX_SHOT:
            errs.append(f"{sid}: {sec} s shot (one render = {MIN_SHOT}-{MAX_SHOT} s; split it)")
        keys = shot.get("cast", [])
        for k in keys:
            if k not in cast:
                errs.append(f"{sid}: `{k}` is not in cast.json (add the character to the bible first)")
            elif (w := shot.get("wardrobe", {}).get(k)) and w not in cast[k]["wardrobe"]:
                errs.append(f"{sid}: wardrobe `{w}` not in cast.json for {k} {list(cast[k]['wardrobe'])}")
        tl = shot_timeline(shot)
        if tl and tl[-1][1] + TAIL > sec:
            errs.append(f"{sid}: lines need {tl[-1][1] + TAIL:.1f} s at 145 wpm, shot is {sec} s "
                        "(cut words, split the shot or lengthen it; never speed the voices up)")
        if tl and first_line_at is None:
            first_line_at = t + tl[0][0]
        for _, _, ln in tl:
            who = ln.get("who")
            if who not in keys:
                errs.append(f"{sid}: speaker {who} not in the shot's cast {keys}")
            en, zh = ln.get("en", ""), ln.get("zh", "")
            if not zh:
                errs.append(f"{sid}: no Chinese for {en!r}")
            if words(en) > WORDS_MAX or len(en) > EN_MAX:
                errs.append(f"{sid}: line too long for one subtitle cue, split it: {en!r}")
            if len(zh) > ZH_MAX:
                errs.append(f"{sid}: Chinese too long for two rows ({len(zh)} > {ZH_MAX}): {zh!r}")
            if re.search(r"[A-Za-z]", zh):
                warns.append(f"{sid}: Latin letters in Chinese subtitle (pinyin only on request): {zh!r}")
        text = " ".join([shot.get("action", ""), shot.get("place", ""), shot.get("props", "")]
                        + [ln.get("en", "") for ln in shot.get("lines", [])]).lower()
        for term, (first, note) in banned.items():
            if re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", text):
                if year < first:
                    errs.append(f"{sid}: anachronism '{term}' in {year} (ordinary from ~{first}) {note}".rstrip())
                elif year < first + 3:
                    warns.append(f"{sid}: '{term}' was still new/rare in {year} {note}".rstrip())
        t += sec
    if first_line_at is not None and first_line_at > 20 and not ep.get("beats", {}).get("opening"):
        errs.append("no hook: nothing said in the first 20 s and no opening beat")
    if ep["shots"] and ep["shots"][0]["seconds"] > 10:
        errs.append("first shot over 10 s: the hook must land in 5-10 s")
    recent = ledger["episodes"][-3:]
    for old in recent:
        if old.get("situation", "").lower() == ep.get("situation", "").lower():
            errs.append(f"situation repeats episode {old['episode']}: {old['situation']}")
        if old.get("date", "") > ep["date"]:
            errs.append(f"date {ep['date']} is before episode {old['episode']} ({old['date']}): time runs forward")
    if recent and set(recent[-1].get("places", [])) == {s["place"] for s in ep["shots"]}:
        warns.append("same places as the last episode: vary the setting")
    if any(e["episode"] == ep["episode"] for e in ledger["episodes"]):
        warns.append(f"episode {ep['episode']} already in the ledger (a remake keeps earlier facts)")
    for w in warns:
        print("WARN ", w)
    for e in errs:
        print("ERROR", e)
    print(f"runtime {runtime:.0f} s, {len(ep['shots'])} shots, {spoken} spoken words "
          f"({spoken / runtime * 60:.0f} words/min over the film), {'FAIL' if errs else 'OK'}")
    return not errs


def cast_block(shot, cast):
    out = []
    for k in shot.get("cast", []):
        c = cast[k]
        wk = shot.get("wardrobe", {}).get(k) or next(iter(c["wardrobe"]))
        out.append(f"- {k}: {c['identity']} Wearing: {c['wardrobe'][wk]}. Voice: {c['voice']}.")
    return out


def dialogue_block(shot, cast):
    tl = shot_timeline(shot)
    if not tl:
        return ["No dialogue: nobody speaks, every mouth stays closed; only the ambient sound below."]
    out = ["Spoken English only, natural American conversational pace (about 145 words per minute), "
           "every line at the same pace. Exact words, timed:"]
    for s, e, ln in tl:
        who = ln["who"]
        others = [k for k in shot.get("cast", []) if k != who]
        listen = ln.get("listener") or (
            f"{' and '.join(others)} listen{(sg := 's' if len(others) == 1 else '')} with lips closed and jaw still, "
            f"eyes on {who}'s face, and never mouth{sg} the words" if others else "")
        voice = "female" if cast[who]["sex"] == "F" else "male"
        out.append(f"{s:.1f}-{e:.1f} s: {who} speaks in {who}'s own {voice} voice, only {who}'s lips move: "
                   f"\"{ln['en']}\"" + (f" {ln['delivery']}." if ln.get("delivery") else "")
                   + (f" {listen}." if listen else ""))
    out.append(f"{tl[-1][1]:.1f}-{shot['seconds']:.1f} s: nobody speaks; small natural movement, mouths closed.")
    return out


def shot_prompt(ep, shot, cast, n):
    when = date.fromisoformat(ep["date"]).strftime("%A %-d %B %Y")
    parts = [
        "NO TEXT ON SCREEN.",
        f"One {shot['seconds']} second shot, 16:9 landscape, shot {n} of a period drama.",
        f"YEAR AND PLACE: {when}, {ep['season']}, {ep['location']}, USA. {shot['place'][:1].upper()}{shot['place'][1:]}. "
        f"{shot['time'][:1].upper()}{shot['time'][1:]}.",
    ]
    if shot.get("cast"):
        parts += ["CAST (each face, hairstyle, outfit and voice identical in every shot):", *cast_block(shot, cast)]
    if shot.get("image_note"):
        parts.append(shot["image_note"])
    parts += [f"FRAMING: {shot['framing']}", f"ACTION: {shot['action']}"]
    if shot.get("props"):
        parts.append(f"PROPS AND SET: {shot['props']}")
    parts += [f"CAMERA: {shot['camera']}. ONE CONTINUOUS TAKE: no cut, no zoom, no change of angle, the same framing "
              "from first to last frame.", "DIALOGUE:", *dialogue_block(shot, cast),
              f"SOUND: {shot['ambience']}. No music in this shot; music is added in editing."]
    if shot.get("continuity"):
        parts.append(f"CONTINUITY: {shot['continuity']}")
    parts.append((SKILL / "prompt/look.txt").read_text().strip())
    return "\n".join(parts) + "\n"


def srt_time(t, sep=","):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02}:{m:02}:{int(s):02}{sep}{int(round(s % 1 * 1000)):03}"


def build(ep_path, work):
    if not check(ep_path):
        sys.exit("fix the errors before building")
    ep, cast = load(ep_path), load(SERIES / "cast.json")
    work = Path(work)
    (work / "shots").mkdir(parents=True, exist_ok=True)
    tag = f"aes-ep{ep['episode']:02}"
    render = ["#!/usr/bin/env bash",
              "# Renders the shots one at a time through render-queue (JOBS=N for more; never all at once).",
              "RQ=\"$HOME/Work/museai-main/.claude/skills/muse-video/scripts/render-queue\"",
              "# A shot with stills/<ID>.png renders from that first frame; without one it renders from text.",
              'MV="$HOME/Work/museai-main/.claude/skills/muse-video/scripts/muse-video"',
              'cd "$(dirname "$0")"; mkdir -p clips']
    for n, shot in enumerate(ep["shots"], 1):
        sid = shot["id"]
        (work / "shots" / f"{sid}.prompt.txt").write_text(shot_prompt(ep, shot, cast, n))
        (work / "shots" / f"{sid}.lines.txt").write_text(
            "".join(f"{ln['who']}: {ln['en']}\n" for ln in shot.get("lines", [])))
        dur = max(5, int(-(-shot["seconds"] // 1)))
        render.append(f'IMAGE=$( [ -f stills/{sid}.png ] && echo "$PWD/stills/{sid}.png" ) SIZE=16:9 DURATION={dur} '
                      f'OUT_NAME={tag}-{sid}.mp4 NO_OPEN=1 MUSE_SESSION={tag} "$MV" -f shots/{sid}.prompt.txt '
                      f'&& cp ~/Movies/museai/{tag}-{sid}.mp4 clips/')
    jobs, render = render[6:], render[:6]
    (work / "jobs.txt").write_text("\n".join(jobs) + "\n")
    render.append('export MV; "$RQ" jobs.txt; ls -l clips/*.mp4')
    (work / "render.sh").write_text("\n".join(render) + "\n")
    os.chmod(work / "render.sh", 0o755)

    cues = episode_cues(ep)
    (work / "cues.provisional.json").write_text(json.dumps(cues, ensure_ascii=False, indent=1))
    (work / "speakers.txt").write_text(
        "".join(cast[c[4]]["letter"] for c in cues) + "\n"
        + "".join("W" if cast[c[4]]["sex"] == "F" else "M" for c in cues) + "\n")
    srt, vtt = [], ["WEBVTT", ""]
    for i, (s, e, en, zh, _) in enumerate(cues, 1):
        srt += [str(i), f"{srt_time(s)} --> {srt_time(e + 0.4)}", en, zh, ""]
        vtt += [f"{srt_time(s, '.')} --> {srt_time(e + 0.4, '.')}", en, zh, ""]
    (work / "subs.provisional.srt").write_text("\n".join(srt))
    (work / "subs.provisional.vtt").write_text("\n".join(vtt))
    series = (SERIES / "bible.md").read_text().splitlines()[0].split(":", 1)[-1].strip()
    title = {**ep["title_card"], "series": f"{series} · Episode {ep['episode']}",
             "episode": {"en": ep["title_en"], "zh": ep.get("title_zh", "")}}
    if ep.get("next_title"):    # the storyline's next episode, teased on the end card
        title["next"] = ep["next_title"]
    (work / "title.json").write_text(json.dumps(title, ensure_ascii=False, indent=1))
    (work / "package.md").write_text(package(ep, cast, cues, tag))
    refs = SERIES / "refs"
    missing = sorted({k for s in ep["shots"] for k in s.get("cast", []) if not (refs / f"{k}.jpg").exists()})
    print(f"built {work}: {len(ep['shots'])} shot prompts, render.sh, cues/SRT/VTT (provisional), package.md")
    if missing:
        print(f"MISSING REFS {missing}: make them first (references/faces.md); shots then need stills/<ID>.png")


def package(ep, cast, cues, tag):
    featured = sorted({k for s in ep["shots"] for k in s.get("cast", [])})
    runtime = sum(s["seconds"] for s in ep["shots"])
    L = [f"# {ep['title_vi']}", "", f"*{ep['premise']}*", "",
         f"**Episode {ep['episode']}** · {ep['title_en']} · {date.fromisoformat(ep['date']).strftime('%A %-d %B %Y')}"
         f" · {ep['location']} · target {runtime:.0f} s · featuring "
         + ", ".join(cast[k]["name"] for k in featured), "",
         "Fiction: invented people and events in a historically plausible setting.", "",
         "## Beats", *[f"- **{k}**: {v}" for k, v in ep["beats"].items()], "",
         "## Scene plan", "| shot | time | place / framing | action | dialogue (EN / 中文) |", "|---|---|---|---|---|"]
    t = 0.0
    for s in ep["shots"]:
        dlg = "<br>".join(f"**{ln['who']}**: {ln['en']}<br>{ln['zh']}" for ln in s.get("lines", [])) or "—"
        L.append(f"| {s['id']} | {t:.0f}-{t + s['seconds']:.0f} s | {s['place']}; {s['framing']} | {s['action']} | {dlg} |")
        t += s["seconds"]
    L += ["", "## Shot prompts", f"Ready to copy: `shots/<ID>.prompt.txt` (render: `./render.sh`, files `{tag}-<ID>.mp4`).", ""]
    for n, s in enumerate(ep["shots"], 1):
        L += [f"### {s['id']}", "```", shot_prompt(ep, s, cast, n).split("\nPERIOD LOOK")[0].strip(),
              "(+ prompt/look.txt + muse-video quality block)", "```", ""]
    L += ["## Subtitles (provisional: realign to the final audio)", "```"]
    for s, e, en, zh, who in cues:
        L.append(f"{srt_time(s)} --> {srt_time(e + 0.4)}  [{who}]  {en}  /  {zh}")
    L += ["```", "", "## Sound and editing", ep.get("sound_notes", "Music bed under all shots, ducked under speech."), "",
          "## Continuity update"]
    cu = ep["continuity_update"]
    L += [*[f"- NEW: {x}" for x in cu.get("new_facts", [])], *[f"- OPEN: {x}" for x in cu.get("threads", [])]]
    return "\n".join(L) + "\n"


SIDES = ("LEFT and RIGHT always mean the person's own left and right, so a mark on their LEFT is on the "
         "viewer's right when they face the camera.")


def still(key, work, wardrobe=None):
    cast = load(SERIES / "cast.json")
    c = cast[key]
    wk = wardrobe or next(iter(c["wardrobe"]))
    prompt = (f"Candid frame from a 1985 American feature film shot on 35 mm Kodak colour negative, autumn. "
              f"Medium shot, waist up, of one young person {c.get('still', 'in a sunny 1985 room')}, caught "
              f"mid-moment, glancing just past the camera with a relaxed natural expression, mouth closed, "
              f"not posing. {c['identity']} {SIDES} Looks exactly {c['age']} years old, young and fresh: skin, "
              f"hair and posture of that age. Wearing: {c['wardrobe'][wk]}. An original face that does not "
              f"resemble any actor, celebrity or public figure. Real unretouched skin with pores, faint "
              f"unevenness and peach fuzz, natural asymmetry, the described marks visible on the named side, "
              f"once each. Saturated warm 1980s film colour: burnt orange, camel, cream and rust against teal "
              f"and powder blue, golden daylight, soft lens with gentle halation, visible fine film grain, "
              f"slightly soft focus overall. Not a digital photo: no HDR, no over-sharpening, no airbrushed or "
              f"plastic skin, no glossy CGI look, no studio portrait lighting. No text, no logos, no watermark.")
    Path(work).mkdir(parents=True, exist_ok=True)
    print(json.dumps({"prompt": prompt, "n": 2, "size": "1920x1080", "response_format": "b64_json"}))


def record(ep_path):
    ep, ledger_path = load(ep_path), SERIES / "ledger.json"
    ledger = load(ledger_path)
    ledger["episodes"] = [e for e in ledger["episodes"] if e["episode"] != ep["episode"]] + [{
        "episode": ep["episode"], "date": ep["date"], "title_en": ep["title_en"], "title_vi": ep["title_vi"],
        "situation": ep["situation"], "places": sorted({s["place"] for s in ep["shots"]}),
        "featured": sorted({k for s in ep["shots"] for k in s.get("cast", [])}),
        "summary": ep["premise"], **ep["continuity_update"]}]
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    print(f"recorded episode {ep['episode']} in {ledger_path}")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["-h"]
    if cmd == "check":
        sys.exit(0 if check(*args) else 1)
    {"build": build, "still": still, "record": record}.get(cmd, lambda *_: sys.exit(__doc__))(*args)
