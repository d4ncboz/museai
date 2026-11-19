"""The Curious Mechanism: one episode.json -> illustrations, narration, Ken Burns edit, thumbnail, QA.

Usage (run from anywhere):
  cm.py new <id> "<Title>" [--short]   episodes/<id>/episode.json from the template
  cm.py check <id> [--draft]           content gate: length, hook, claims + sources, prompts, title, thumbnail
  cm.py images <id> [--only S03]       illustrations through museai /v1/images/generations (skips existing)
  cm.py voice <id>                     one narrator voice per scene (edge-tts) -> timeline.json
  cm.py anim <id> [--only S03]         muse-video jobs (illustration = first frame) -> anim/jobs.txt
  cm.py build <id>                     muse clips (else Ken Burns stills) + labels + narration -> <id>.mp4
  cm.py thumb <id> [--scene S01]       1280x720 thumbnail (YouTube) -> <id>_thumb.jpg
  cm.py qa <id>                        file checks + the playbook's manual checklist -> RESULT ok|FAIL

Run: uv run --no-project --python 3.12 --with edge-tts --with pillow python scripts/cm.py ...
Env: MUSEAI_HOME (folder holding data/api_key; default the repo, then ~/Work/museai), MUSEAI_BASE
     (default http://127.0.0.1:18610), CM_VOICE (default en-US-AndrewNeural), CM_RATE (default +0%),
     CM_WORK (default <repo>/videos/curious-mechanism).
"""

import asyncio
import base64
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[2]
EPISODES = SKILL / "episodes"
WORK = Path(os.environ.get("CM_WORK", REPO / "videos/curious-mechanism"))
API_BASE = os.environ.get("MUSEAI_BASE", "http://127.0.0.1:18610")
VOICE = os.environ.get("CM_VOICE", "en-US-AndrewNeural")
RATE = os.environ.get("CM_RATE", "+0%")
FPS = 30

FORMATS = {
    # size, words min/max (playbook: ~145 wpm), duration min/max seconds
    "long": {"size": (1920, 1080), "words": (1150, 1750), "secs": (480, 720), "aspect": "16:9"},
    "short": {"size": (1080, 1920), "words": (75, 130), "secs": (20, 60), "aspect": "9:16"},
}
WPS = 145 / 60
# Channel outro after the last scene of every episode: spoken line + on-screen label over the last frame.
CTA = {
    "id": "CTA",
    "section": "cta",
    "say": "If you want to see more stories like this, subscribe.",
    "labels": ["Subscribe for more"],
    "move": "push_in",
}
PAPER, INK, CHARCOAL, RED, BRASS = "#EFE6D2", "#1F3A5F", "#2B2B2B", "#A63D32", "#B08D57"

# The channel look lives in prompt/look.txt and prompt/avoid.txt: change it there, never in one episode.
# CM_LOOK=<name> tries another look (prompt/look-<name>.txt, avoid-<name>.txt) in its own work folder.
LOOK_NAME = os.environ.get("CM_LOOK", "")
_sfx = f"-{LOOK_NAME}" if LOOK_NAME else ""
LOOK = (SKILL / f"prompt/look{_sfx}.txt").read_text().strip()
AVOID = (SKILL / f"prompt/avoid{_sfx}.txt").read_text().strip()
MASTER = (
    "{look} Subject: {subject}. Show: {show}. {variant}Composition: {composition}. Avoid: {avoid}."
)
VARIANTS = {
    "main": "",
    "cutaway": "A clean cutaway that opens the object to show its inner parts, same look. ",
    "closeup": "Close-up, tight framing on the part named above, shallow depth of field. ",
    "map": "An aerial view of the place, as seen from high above, no place names. ",
    "diagram": "A clean explanatory diagram in the same look and palette: simple shapes, glowing flow lines "
    "and arrows, plain dark background. ",
}
COMPOSITION = {
    "16:9": "16:9 landscape, one clear subject filling most of the frame",
    "9:16": "9:16 vertical portrait, one clear subject filling the middle of the frame, "
    "the scene continues to the bottom edge with simple, uncluttered ground or sky there for on-screen labels",
}
MOVES = ("push_in", "pull_out", "pan_left", "pan_right", "pan_up", "pan_down", "still")
BANNED = (
    "since the dawn",
    "throughout history",
    "in today's world",
    "you won't believe",
    "terrified",
    "mind-blowing",
    "smash that",
    "let's dive in",
    "without further ado",
)
TEXT_WORDS = re.compile(r"\b(label(s|led)?|text|caption|written|lettering|title)\b", re.I)


# ---------- helpers ----------
def ep_path(eid: str) -> Path:
    return EPISODES / eid / "episode.json"


def load(eid: str) -> dict:
    p = ep_path(eid)
    if not p.exists():
        sys.exit(f'no episode {p}; run: cm.py new {eid} "Title"')
    return json.loads(p.read_text())


def work(eid: str) -> Path:
    w = WORK / (f"{eid}--{LOOK_NAME}" if LOOK_NAME else eid)
    w.mkdir(parents=True, exist_ok=True)
    return w


def fmt(ep: dict) -> dict:
    return FORMATS[ep.get("format", "long")]


def words(s: str) -> int:
    return len(re.findall(r"[A-Za-z0-9'’-]+", s))


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"command failed: {' '.join(cmd[:4])} ...\n{r.stderr[-1500:]}")
    return r.stdout + r.stderr


def duration(p: Path) -> float:
    out = run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]
    )
    return float(out.strip())


def font(bold: bool = True, serif: bool = True) -> str:
    name = ("DejaVu Serif" if serif else "DejaVu Sans") + (":bold" if bold else "")
    try:
        return subprocess.run(
            ["fc-match", "-f", "%{file}", name], capture_output=True, text=True
        ).stdout.strip()
    except FileNotFoundError:
        return "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"


def image_of(ep: dict, scene: dict, w: Path) -> Path:
    """A scene may reuse another scene's illustration ("image": "S01") with a different move or labels."""
    src = scene["image"] if isinstance(scene.get("image"), str) else scene["id"]
    return w / "img" / f"{src}.png"


# ---------- new ----------
def cmd_new(eid: str, title: str, short: bool) -> None:
    p = ep_path(eid)
    if p.exists():
        sys.exit(f"{p} exists")
    tpl = json.loads((SKILL / "episode.template.json").read_text())
    tpl.update(id=eid, title=title, format="short" if short else "long")
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(tpl, indent=1, ensure_ascii=False) + "\n")
    print(p)


# ---------- check ----------
def cmd_check(eid: str, draft: bool) -> int:
    ep = load(eid)
    f = fmt(ep)
    res: list[tuple[str, str]] = []

    def add(level: str, msg: str) -> None:
        res.append((level, msg))

    scenes = ep.get("scenes", [])
    ids = [s.get("id") for s in scenes]
    if len(set(ids)) != len(ids):
        add("FAIL", "scene ids repeat")
    total = sum(words(s.get("say", "")) for s in scenes)
    lo, hi = f["words"]
    add(
        "ok" if lo <= total <= hi else "FAIL",
        f"narration {total} words (target {lo}-{hi}, ~{total / WPS:.0f} s)",
    )

    title = ep.get("title", "")
    if not re.match(r"^(why|how|the hidden|what)\b", title, re.I):
        add(
            "WARN",
            f"title '{title}' uses none of the formulas (Why... / How X actually works / The hidden ...)",
        )
    thumb = ep.get("thumbnail", {}).get("text", "")
    if ep.get("format") == "long":
        n = words(thumb)
        if not 2 <= n <= 4:
            add("FAIL", f"thumbnail text '{thumb}' has {n} words (2-4)")
        elif thumb.lower() in title.lower():
            add("FAIL", "thumbnail text repeats the title")

    claims = ep.get("claims", {})
    for cid, c in claims.items():
        srcs = [s for s in c.get("sources", []) if s.strip()]
        if len(srcs) < 2:
            add(
                "WARN" if draft else "FAIL",
                f"claim {cid}: {len(srcs)} source(s), need 2 independent",
            )
        if not c.get("verified"):
            add(
                "WARN" if draft else "FAIL", f"claim {cid} not verified: '{c.get('text', '')[:60]}'"
            )
    used = set()
    for s in scenes:
        sid = s.get("id", "?")
        say = s.get("say", "")
        if not say.strip():
            add("FAIL", f"{sid}: no narration")
        est = words(say) / WPS
        if est > 12:
            add(
                "WARN",
                f"{sid}: ~{est:.0f} s on one picture; split it or reuse the image with a new move (4-8 s)",
            )
        low = say.lower()
        for b in BANNED:
            if b in low:
                add("FAIL", f"{sid}: filler phrase '{b}'")
        if "!" in say:
            add("WARN", f"{sid}: '!' read as shouting; use '.'")
        for c in s.get("claims", []):
            used.add(c)
            if c not in claims:
                add("FAIL", f"{sid}: claim '{c}' not in claims")
        img = s.get("image")
        if isinstance(img, str):
            if img not in ids or ids.index(img) >= ids.index(sid):
                add("FAIL", f"{sid}: reuses image of '{img}', which is not an earlier scene")
        elif isinstance(img, dict):
            if not img.get("subject") or not img.get("show"):
                add("FAIL", f"{sid}: image needs subject and show")
            if img.get("variant", "main") not in VARIANTS:
                add("FAIL", f"{sid}: variant must be one of {', '.join(VARIANTS)}")
            if TEXT_WORDS.search(img.get("subject", "") + " " + img.get("show", "")):
                add(
                    "WARN",
                    f"{sid}: image prompt asks for text; labels go in 'labels', drawn in the edit",
                )
        else:
            add("FAIL", f"{sid}: image missing")
        if s.get("move", "push_in") not in MOVES:
            add("FAIL", f"{sid}: move must be one of {', '.join(MOVES)}")
        for lab in s.get("labels", []):
            if len(lab) > 28:
                add("WARN", f"{sid}: label '{lab}' is long for a phone screen")
    for cid in claims:
        if cid not in used:
            add("WARN", f"claim {cid} is not used by any scene")
    if scenes:
        hook = words(scenes[0].get("say", "")) / WPS
        limit = 3 if ep.get("format") == "short" else 20
        add(
            "ok" if hook <= limit else "FAIL", f"hook {hook:.1f} s (<= {limit} s, no channel intro)"
        )
    unique = sum(isinstance(s.get("image"), dict) for s in scenes)
    add("ok", f"{len(scenes)} scenes, {unique} illustrations")

    fails = 0
    for level, msg in res:
        print(f"{level:4} {msg}")
        fails += level == "FAIL"
    print(
        f"RESULT {'ok' if not fails else 'FAIL'}"
        + (" (draft: unverified claims allowed)" if draft else "")
    )
    return 1 if fails else 0


# ---------- images ----------
def api_key() -> str:
    for home in [os.environ.get("MUSEAI_HOME"), str(REPO), str(Path.home() / "Work/museai")]:
        if home and (Path(home) / "data/api_key").exists():
            return (Path(home) / "data/api_key").read_text().strip()
    sys.exit("no data/api_key; start museai once (python -m museai) or set MUSEAI_HOME")


def prompt_for(ep: dict, img: dict) -> str:
    return MASTER.format(
        look=LOOK,
        avoid=AVOID,
        subject=img["subject"],
        show=img["show"],
        variant=VARIANTS[img.get("variant", "main")],
        composition=COMPOSITION[fmt(ep)["aspect"]],
    )


def cmd_images(eid: str, only: str | None) -> None:
    ep = load(eid)
    out = work(eid) / "img"
    out.mkdir(exist_ok=True)
    w, h = fmt(ep)["size"]
    size = f"{w}x{h}"
    key = api_key()
    for s in ep["scenes"]:
        img = s.get("image")
        if not isinstance(img, dict) or (only and s["id"] != only):
            continue
        p = out / f"{s['id']}.png"
        if p.exists() and not only:
            print(f"skip {p.name} (exists)")
            continue
        body = {"prompt": prompt_for(ep, img), "n": 1, "size": size, "response_format": "b64_json"}
        req = urllib.request.Request(
            f"{API_BASE}/v1/images/generations",
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "X-Muse-Session": os.environ.get("MUSE_SESSION", f"cm-{eid}"),
            },
        )
        try:
            with urllib.request.urlopen(
                req, timeout=float(os.environ.get("STILL_TIMEOUT", 3600))
            ) as r:
                data = json.load(r)["data"]
        except urllib.error.HTTPError as e:
            sys.exit(f"{s['id']}: museai {e.code}: {e.read()[:300]!r}")
        except urllib.error.URLError as e:
            sys.exit(f"museai at {API_BASE} not reachable ({e}); start it: python -m museai")
        p.write_bytes(base64.b64decode(data[0]["b64_json"]))
        print(p)


# ---------- animation ----------
MOVE_WORDS = {
    "push_in": "slow steady push-in",
    "pull_out": "slow steady pull-out",
    "pan_left": "slow steady pan to the left",
    "pan_right": "slow steady pan to the right",
    "pan_up": "slow steady tilt up",
    "pan_down": "slow steady tilt down",
    "still": "locked camera, no camera move",
}
MUSE_VIDEO = SKILL.parent / "muse-video/scripts/muse-video"


def anim_of(ep: dict, scene: dict, w: Path) -> Path:
    """The muse clip of a scene, or of the scene whose picture it reuses."""
    src = scene["image"] if isinstance(scene.get("image"), str) else scene["id"]
    return w / "anim" / f"{src}.mp4"


def cmd_anim(eid: str, only: str | None) -> None:
    """Write one muse-video job per scene (its illustration as first frame) for render-queue."""
    ep = load(eid)
    w = work(eid)
    tl_path = w / "timeline.json"
    if not tl_path.exists():
        sys.exit("run cm.py voice first: clip lengths follow the narration")
    tl = {x["id"]: x for x in json.loads(tl_path.read_text())}
    out = w / "anim"
    out.mkdir(exist_ok=True)
    jobs = []
    for s in ep["scenes"]:
        if not isinstance(s.get("image"), dict) or (only and s["id"] != only):
            continue
        if (out / f"{s['id']}.mp4").exists() and not only:
            print(f"skip {s['id']}.mp4 (exists)")
            continue
        if not s.get("motion"):
            sys.exit(f"{s['id']}: no 'motion' (what moves in the clip)")
        img = image_of(ep, s, w)
        if not img.exists():
            sys.exit(f"{s['id']}: missing {img}; run cm.py images {eid}")
        prompt = out / f"{s['id']}.prompt.txt"
        prompt.write_text(
            "NEW STANDALONE REQUEST. Ignore any earlier versions, drafts, images or projects. "
            "Use ONLY the image attached to this message as the first frame.\n\n"
            f"SCENE: {s['image']['subject']}.\n"
            f"MOTION: {s['motion']}.\n"
            f"CAMERA: {MOVE_WORDS[s.get('move', 'push_in')]}.\n"
        )
        secs = max(5, math.ceil(tl[s["id"]]["dur"] + 0.5))
        env = (
            f"MUSE_SKILL_DEV=1 STYLE=animation SIZE={fmt(ep)['aspect']} DURATION={secs} "
            f"IMAGE={shlex.quote(str(img))} OUT_NAME={s['id']}.mp4 NO_OPEN=1 "
            f"MUSE_SESSION=cm-{eid}{' RETAKE=1' if only else ''}"
        )
        jobs.append(
            f"{env} {shlex.quote(str(MUSE_VIDEO))} -f {shlex.quote(str(prompt))} "
            f"{shlex.quote(str(out))}"
        )
    if not jobs:
        print("nothing to render")
        return
    q = out / "jobs.txt"
    q.write_text("\n".join(jobs) + "\n")
    print(f"{len(jobs)} clips -> {q}\nrun in one background call (one clip at a time):")
    print(f"  {MUSE_VIDEO.parent / 'render-queue'} {q}")


# ---------- voice ----------
async def _tts(text: str, path: Path) -> None:
    import edge_tts

    # The free Edge endpoint throttles (503 or "No audio was received") in bursts; back off exponentially.
    for attempt in range(6):
        try:
            await edge_tts.Communicate(text.replace("!", "."), VOICE, rate=RATE).save(str(path))
            return
        except Exception as e:
            if attempt == 5:
                sys.exit(f"edge-tts failed 6 times: {e}")
            await asyncio.sleep(5 * 2**attempt)


def cmd_voice(eid: str) -> None:
    ep = load(eid)
    vdir = work(eid) / "voice"
    vdir.mkdir(exist_ok=True)
    timeline, t = [], 0.0
    scenes = ep["scenes"] + [CTA]
    sections = [s.get("section", "") for s in scenes]
    for i, s in enumerate(scenes):
        mp3, wav = vdir / f"{s['id']}.mp3", vdir / f"{s['id']}.wav"
        stamp = vdir / f"{s['id']}.txt"
        said = f"{VOICE}|{RATE}|{s['say']}"
        if not wav.exists() or not stamp.exists() or stamp.read_text() != said:
            asyncio.run(_tts(s["say"], mp3))
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-i",
                    str(mp3),
                    "-ar",
                    "48000",
                    "-ac",
                    "1",
                    str(wav),
                ]
            )
            stamp.write_text(said)
        d = duration(wav)
        # Longer pause where the story moves to a new section, a breath inside one; a hold on the last image.
        nxt = sections[i + 1] if i + 1 < len(sections) else None
        gap = 1.2 if nxt is None else (0.7 if nxt != sections[i] else 0.3)
        timeline.append(
            {"id": s["id"], "start": round(t, 3), "speech": round(d, 3), "dur": round(d + gap, 3)}
        )
        t += d + gap
    (work(eid) / "timeline.json").write_text(json.dumps(timeline, indent=1))
    print(
        f"{len(timeline)} scenes, {t:.1f} s, voice {VOICE} {RATE} -> {work(eid) / 'timeline.json'}"
    )


# ---------- build ----------
def zoompan(move: str, n: int, w: int, h: int) -> str:
    z0, z1 = {"push_in": (1.0, 1.08), "pull_out": (1.08, 1.0)}.get(move, (1.06, 1.06))
    if move == "still":
        z0 = z1 = 1.0
    z = f"{z0}+({z1 - z0})*on/{max(n - 1, 1)}"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    p = f"on/{max(n - 1, 1)}"
    x, y = {
        "pan_left": (f"(iw-iw/zoom)*(1-{p})", cy),
        "pan_right": (f"(iw-iw/zoom)*{p}", cy),
        "pan_up": (cx, f"(ih-ih/zoom)*(1-{p})"),
        "pan_down": (cx, f"(ih-ih/zoom)*{p}"),
    }.get(move, (cx, cy))
    # Zoom on a 2x canvas so the slow move does not shimmer.
    return (
        f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={w}x{h}:fps={FPS},format=yuv420p"
    )


def label_png(labels: list[str], w: int, h: int, path: Path) -> None:
    """Editorial labels (uppercase, letter-spaced, ink on paper) drawn in the edit, never in the image."""
    from PIL import Image, ImageDraw, ImageFont

    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    base = int(h * (0.028 if w > h else 0.022))
    x = int(w * 0.06)
    y = int(h * (0.08 if w > h else 0.78))
    for lab in labels:
        txt = lab.upper()
        size = base
        # Shrink a long label until it fits the frame width (9:16 is narrow).
        while (
            size > 14
            and spaced_width(d, txt, ImageFont.truetype(font(True, False), size)) > w * 0.86
        ):
            size -= 2
        f = ImageFont.truetype(font(True, False), size)
        tw = spaced_width(d, txt, f)
        pad = size * 0.5
        d.rounded_rectangle(
            [x - pad, y - pad, x + tw + pad, y + size + pad],
            radius=6,
            fill=PAPER + "E6",
            outline=INK,
            width=2,
        )
        cx = x
        for ch in txt:
            d.text((cx, y), ch, font=f, fill=INK)
            cx += d.textlength(ch, font=f) + f.size * 0.08
        y += int(base * 2.4)
    im.save(path)


def spaced_width(d, txt: str, f) -> float:
    """Width with the brand's +8 % letter spacing for labels."""
    return sum(d.textlength(ch, font=f) for ch in txt) + f.size * 0.08 * max(len(txt) - 1, 0)


def cmd_build(eid: str) -> None:
    ep = load(eid)
    w = work(eid)
    tl_path = w / "timeline.json"
    if not tl_path.exists():
        sys.exit("run cm.py voice first")
    tl = {x["id"]: x for x in json.loads(tl_path.read_text())}
    W, H = fmt(ep)["size"]
    clips = w / "clips"
    clips.mkdir(exist_ok=True)
    parts, audio = [], []
    for s in ep["scenes"] + [CTA]:
        if s is CTA:
            # The outro holds the last frame of the story, so the picture does not jump.
            img = clips / "CTA.png"
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-sseof",
                    "-0.1",
                    "-i",
                    str(parts[-1]),
                    "-frames:v",
                    "1",
                    "-update",
                    "1",
                    str(img),
                ]
            )
        else:
            img = image_of(ep, s, w)
        if not img.exists():
            sys.exit(f"{s['id']}: missing {img}; run cm.py images {eid}")
        t = tl[s["id"]]
        n = max(1, round(t["dur"] * FPS))
        clip = clips / f"{s['id']}.mp4"
        anim = anim_of(ep, s, w)
        if s is not CTA and anim.exists():
            # muse clip, muted (narration only); a clip shorter than the scene holds its last frame.
            vf = (
                f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
                f"tpad=stop_mode=clone:stop_duration={t['dur']:.3f},format=yuv420p"
            )
            cmd = ["ffmpeg", "-y", "-v", "error", "-an", "-i", str(anim)]
        else:
            vf = zoompan(s.get("move", "push_in"), n, W, H)
            cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(img)]
        if s.get("labels"):
            lp = clips / f"{s['id']}_labels.png"
            label_png(s["labels"], W, H, lp)
            # The label still is looped so its fade-in has frames to work on.
            cmd += [
                "-loop",
                "1",
                "-framerate",
                str(FPS),
                "-t",
                f"{t['dur']:.3f}",
                "-i",
                str(lp),
                "-filter_complex",
                f"[0:v]{vf}[bg];[1:v]format=rgba,fade=in:st=0.6:d=0.4:alpha=1[lb];"
                f"[bg][lb]overlay=0:0,format=yuv420p[v]",
                "-map",
                "[v]",
            ]
        else:
            cmd += ["-vf", vf]
        cmd += [
            "-frames:v",
            str(n),
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ]
        run(cmd)
        parts.append(clip)
        audio.append((w / "voice" / f"{s['id']}.wav", t["dur"]))
        print(
            f"{s['id']} {t['dur']:.1f} s {'muse clip' if s is not CTA and anim.exists() else s.get('move', 'push_in')}"
        )

    lst = clips / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    video = clips / "video.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(video),
        ]
    )

    # Narration: each scene's speech padded to its picture's length, so sound and picture never drift.
    nar = w / "narration.wav"
    ins, flt = [], []
    for i, (wav, d) in enumerate(audio):
        ins += ["-i", str(wav)]
        flt.append(f"[{i}:a]apad=whole_dur={d:.3f},atrim=0:{d:.3f}[a{i}]")
    flt.append("".join(f"[a{i}]" for i in range(len(audio))) + f"concat=n={len(audio)}:v=0:a=1[a]")
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            *ins,
            "-filter_complex",
            ";".join(flt),
            "-map",
            "[a]",
            "-ar",
            "48000",
            "-ac",
            "1",
            str(nar),
        ]
    )

    out = w / f"{eid}.mp4"
    tmp = w / f"{eid}.part.mp4"
    music = ep.get("music", {}).get("file")
    mix = "[1:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    ins = ["-i", str(nar)]
    if music:
        mp = Path(music) if Path(music).is_absolute() else SKILL / music
        if not mp.exists():
            sys.exit(f"music file {mp} missing")
        ins += ["-stream_loop", "-1", "-i", str(mp)]
        # Music ducks under the voice (sidechain) and sits about 20 dB down: narration always stays clear.
        mix = (
            "[1:a]highpass=f=70,acompressor=threshold=-20dB:ratio=3,asplit[v1][v2];"
            "[2:a]volume=0.12,afade=in:d=1.5[m];[m][v2]sidechaincompress=threshold=0.05:ratio=6[md];"
            "[v1][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
        )
    run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(video),
            *ins,
            "-filter_complex",
            mix,
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-shortest",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
    )
    tmp.replace(out)
    write_srt(ep, tl, w / f"{eid}.srt")
    print(out)


def write_srt(ep: dict, tl: dict, path: Path) -> None:
    def ts(x: float) -> str:
        ms = round(x * 1000)
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"

    rows = []
    for i, s in enumerate(ep["scenes"] + [CTA], 1):
        t = tl[s["id"]]
        rows.append(f"{i}\n{ts(t['start'])} --> {ts(t['start'] + t['speech'])}\n{s['say']}\n")
    path.write_text("\n".join(rows))


# ---------- thumbnail ----------
def cmd_thumb(eid: str, scene: str | None) -> None:
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    ep = load(eid)
    w = work(eid)
    th = ep.get("thumbnail", {})
    sid = scene or th.get("scene") or ep["scenes"][0]["id"]
    s = next((x for x in ep["scenes"] if x["id"] == sid), None)
    if not s:
        sys.exit(f"no scene {sid}")
    src = Image.open(image_of(ep, s, w)).convert("RGB")
    W, H = 1280, 720
    im = Image.new("RGB", (W, H), PAPER)
    art = ImageOps.fit(src, (int(W * 0.55), H))
    im.paste(art, (W - art.width, 0))
    d = ImageDraw.Draw(im)
    text = th.get("text") or ep["title"]
    fsize = 96
    f = ImageFont.truetype(font(True, True), fsize)
    room = W - art.width - 48 - 32
    lines = wrap(d, text.upper(), f, room)
    while (len(lines) > 3 or max(d.textlength(x, font=f) for x in lines) > room) and fsize > 40:
        fsize -= 6
        f = ImageFont.truetype(font(True, True), fsize)
        lines = wrap(d, text.upper(), f, room)
    y = (H - len(lines) * fsize * 1.15) / 2
    for i, line in enumerate(lines):
        d.text(
            (48, y + i * fsize * 1.15),
            line,
            font=f,
            fill=RED if i == len(lines) - 1 else INK,
            stroke_width=3,
            stroke_fill=CHARCOAL,
        )
    fm = ImageFont.truetype(font(True, True), 34)
    d.text((W - 70, H - 58), "CM", font=fm, fill=BRASS, stroke_width=1, stroke_fill=CHARCOAL)
    out = w / f"{eid}_thumb.jpg"
    im.save(out, quality=92)
    print(out)


def wrap(d, text: str, f, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        t = f"{cur} {word}".strip()
        if d.textlength(t, font=f) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


# ---------- qa ----------
MANUAL = [
    "Every important claim has 2 reliable sources (listed in the description)",
    "Uncertain claims are said as uncertain; no invented quotes or scenes",
    "First 20 s (Shorts: 2 s) create curiosity; one central question, answered at the end",
    "Illustrations match the channel look (prompt/look.txt); no photoreal frame, no garbled AI text",
    "Mechanical parts are drawn correctly (checked against a real reference photo)",
    "Narration is natural; technical terms and names are pronounced right",
    "Title is true to the video; thumbnail readable on a phone and shows what the video shows",
    "Music and SFX are licensed and logged (playbook/templates/asset-license-log.md)",
    "YouTube 'altered or synthetic content' assessed; description says AI-assisted visuals and voice",
]


def cmd_qa(eid: str) -> int:
    ep = load(eid)
    w = work(eid)
    f = fmt(ep)
    out = w / f"{eid}.mp4"
    fails = 0

    def say(level: str, msg: str) -> None:
        nonlocal fails
        fails += level == "FAIL"
        print(f"{level:4} {msg}")

    if not out.exists():
        say("FAIL", f"{out} missing; run cm.py build {eid}")
    else:
        info = json.loads(
            run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=codec_type,width,height",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "json",
                    str(out),
                ]
            )
        )
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        size = (v["width"], v["height"])
        say(
            "ok" if size == f["size"] else "FAIL",
            f"frame {size[0]}x{size[1]} (want {f['size'][0]}x{f['size'][1]})",
        )
        dur = float(info["format"]["duration"])
        lo, hi = f["secs"]
        say("ok" if lo <= dur <= hi else "FAIL", f"duration {dur:.1f} s (target {lo}-{hi})")
        say(
            "ok" if any(s["codec_type"] == "audio" for s in info["streams"]) else "FAIL",
            "audio track",
        )
        loud = run(["ffmpeg", "-v", "info", "-i", str(out), "-af", "ebur128", "-f", "null", "-"])
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", loud)
        if m:
            lufs = float(m[-1])
            say("ok" if -16 <= lufs <= -12 else "WARN", f"loudness {lufs} LUFS (YouTube -14)")
    tl_path = w / "timeline.json"
    if tl_path.exists():
        for t in json.loads(tl_path.read_text()):
            if t["dur"] > 10:
                say(
                    "WARN",
                    f"{t['id']}: {t['dur']:.1f} s on one picture (playbook: new composition every 4-8 s)",
                )
    for s in ep["scenes"]:
        if isinstance(s.get("image"), dict):
            p = w / "img" / f"{s['id']}.png"
            if p.exists():
                from PIL import Image

                with Image.open(p) as im:
                    if min(im.size) < 720:
                        say(
                            "FAIL",
                            f"{p.name} is {im.size[0]}x{im.size[1]}: too small (mock driver?)",
                        )
    thumb = w / f"{eid}_thumb.jpg"
    if ep.get("format") == "long":
        say("ok" if thumb.exists() else "FAIL", f"thumbnail {thumb.name}")
    print("\nManual checks (playbook/templates/qa-checklist.md); confirm each before publishing:")
    for m in MANUAL:
        print(f"  [ ] {m}")
    print(f"RESULT {'ok' if not fails else 'FAIL'}")
    return 1 if fails else 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, eid, rest = argv[0], argv[1], argv[2:]

    def opt(name: str) -> str | None:
        return (
            rest[rest.index(name) + 1]
            if name in rest and rest.index(name) + 1 < len(rest)
            else None
        )

    if cmd == "new":
        if not rest:
            sys.exit('cm.py new <id> "Title" [--short]')
        cmd_new(eid, rest[0], "--short" in rest)
    elif cmd == "check":
        return cmd_check(eid, "--draft" in rest)
    elif cmd == "images":
        cmd_images(eid, opt("--only"))
    elif cmd == "voice":
        cmd_voice(eid)
    elif cmd == "anim":
        cmd_anim(eid, opt("--only"))
    elif cmd == "build":
        if not shutil.which("ffmpeg"):
            sys.exit("ffmpeg not found")
        cmd_build(eid)
    elif cmd == "thumb":
        cmd_thumb(eid, opt("--scene"))
    elif cmd == "qa":
        return cmd_qa(eid)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
