"""Usage: compose.py quizzes/<topic>.json work/<topic> out.mp4
Run: uv run --no-project --python 3.12 --with pillow --with numpy --with soundfile python scripts/compose.py ...

Builds the whole 9:16 quiz from work/<topic>/scenes/NN.(mp4|png) and work/<topic>/voice/ (voice.py).
A scene NN.mp4 (muse clip) plays as-is; NN.png gets a slow push-in. Frames are drawn in Python and
piped to ffmpeg; the sound (voice, synthesised SFX, optional MUSIC=track.m4a ducked under the voice)
is mixed in numpy and loudness-normalised to -14 LUFS.

Timeline (6 words ~ 57 s):
  HOOK 0-3.0 s     three hooks stacked in the first second, never a title card or black frame:
                   1 visual  - the BOSS word's scene (the last, hardest word) with a punch-in + flash
                   2 text    - hook.text as a big sticker, on frame 0
                   3 open loop - the boss hanzi huge with "?" (frame 0) + hook.boss_teaser and 0/N dots by 0.5 s:
                     the viewer sees the question they can only answer by staying to the end
                   + sound: bass hit + whoosh at 0, hook.say from 0.25 s
  WORD x N  8.5 s  cue 0-1.2 (meaning + 3 hanzi choices A/B/C; rehook sticker on some words)
                   countdown 1.2-5.2 (draining ring 4..1, tick per second, fast ticks in the last)
                   reveal 5.2-8.5 (right choice turns green, answer card: hanzi, tone-coloured pinyin,
                   meaning, memory trick; chime, slow then natural Mandarin read; score dot fills)
  OUTRO 3.5 s      boss scene again (the last frame flows into the first: replay loop), outro.text,
                   full score row, outro.cta, outro.say
Second language: `"sub": "vi"` puts a smaller Vietnamese line under every English one (cue, meaning,
trick, stickers), read from the `<key>_vi` fields (meaning_vi, trick_vi, hook.text_vi, ...).
Safe zones: nothing above y 200 (platform tabs), below y 1480 (caption / UI) or right of x 960
between y 900-1480 (like / comment buttons).
"""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SR = 1080, 1920, 30, 48000
HOOK, CUE, COUNT, REVEAL, OUTRO = 3.0, 1.2, 4.0, 3.3, 3.5
WORD = CUE + COUNT + REVEAL
PINGFANG = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
            ".asset/AssetData/PingFang.ttc")
CJK = PINGFANG if Path(PINGFANG).exists() else "/System/Library/Fonts/Hiragino Sans GB.ttc"
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"  # Latin + Vietnamese + pinyin tone marks
WHITE, INK, GREEN, DIM = (255, 255, 255), (20, 20, 26), (38, 196, 110), (255, 255, 255, 110)
TONES = {1: (255, 86, 86), 2: (255, 170, 50), 3: (80, 210, 120), 4: (90, 160, 255), 0: (200, 200, 210)}
UI = {"en": {"cue": "What's this in Chinese?", "boss": "BOSS WORD", "score": "Your score?"},
      "vi": {"cue": "Tiếng Trung là gì?", "boss": "TỪ KHÓ NHẤT", "score": "Bạn được mấy điểm?"}}


def font(face, size):
    if face == "zh":
        return ImageFont.truetype(CJK, size, index=11 if CJK == PINGFANG else 0)
    return ImageFont.truetype(AVENIR, size, index={"bold": 0, "demi": 2, "medium": 5}[face])


def hexrgb(h):
    return tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def pop(t, dur=0.28):
    """Scale for a sticker popping in (ease-out-back 0.6 -> ~1.06 -> 1.0); 0 = not shown yet."""
    if t <= 0:
        return 0.0
    x = min(t / dur, 1.0) - 1
    return 0.6 + 0.4 * (1 + 2.70158 * x ** 3 + 1.70158 * x ** 2)


# ---------- layers (RGBA images, cached) ----------

def text_size(draw, text, f):
    b = draw.textbbox((0, 0), text, font=f)
    return b[2] - b[0], b[3] - b[1], b[1]


def panel(w, h, fill=(14, 14, 20, 200), r=36):
    im = Image.new("RGBA", (w, h))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill)
    return im


def sticker(text, size, bg, fg=WHITE, tilt=0, sub=None):
    f, sf = font("bold", size), font("demi", max(30, int(size * 0.6)))
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    rows = [(ln, f, int(size * 1.18)) for ln in wrap(d, text, f, 860)]
    if sub:  # second language: smaller line(s) under the first
        rows += [(ln, sf, int(sf.size * 1.27)) for ln in wrap(d, sub, sf, 860)]
    w = max(text_size(d, ln, rf)[0] for ln, rf, _ in rows) + 64
    im = panel(w, sum(lh for *_, lh in rows) + 40, fill=(*bg, 245), r=26)
    dr = ImageDraw.Draw(im)
    y = 20
    for ln, rf, lh in rows:
        tw = text_size(dr, ln, rf)[0]
        dr.text(((w - tw) // 2, y - rf.size * 0.12), ln, font=rf, fill=fg if rf is f else (*fg[:3], 215))
        y += lh
    return im.rotate(tilt, expand=True, resample=Image.BICUBIC) if tilt else im


def is_cjk(ch):
    return "\u3000" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef"


def mixed(d, xy, text, f, fill=None, measure=False):
    """Latin face for Latin, PingFang for hanzi inside the same line (Avenir draws tofu for CJK)."""
    zf = font("zh", round(f.size * 1.05))
    x, y = xy
    for ch in text:
        g = zf if is_cjk(ch) else f
        if not measure:
            d.text((x, y - (f.size * 0.08 if g is zf else 0)), ch, font=g, fill=fill)
        x += d.textlength(ch, font=g)
    return x - xy[0]


def wrap(d, text, f, width):
    out, cur = [], ""
    for word in text.split():
        nxt = f"{cur} {word}".strip()
        if cur and mixed(d, (0, 0), nxt, f, measure=True) > width:
            out.append(cur)
            cur = word
        else:
            cur = nxt
    return out + [cur]


V = "aeiouüvāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ"
SYL = re.compile(rf"(?:zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])?[{V}]+(?:ng(?![{V}])|n(?![{V}])|r(?![{V}]))?", re.I)
MARKS = {c: t for t, cs in enumerate(["", "āēīōūǖ", "áéíóúǘ", "ǎěǐǒǔǚ", "àèìòùǜ"]) for c in cs}


def syllables(py):
    """Tone-marked pinyin -> [(syllable, tone)], tone 0 = neutral."""
    return [(m, next((MARKS[c] for c in m.lower() if c in MARKS), 0)) for m in SYL.findall(py)]


def choice(letter, hanzi, py, state):
    """state: plain | right | wrong (dimmed)."""
    w, h = 760, 132
    fill = {"plain": (255, 255, 255, 235), "right": (*GREEN, 250), "wrong": (255, 255, 255, 90)}[state]
    im = panel(w, h, fill=fill, r=30)
    d = ImageDraw.Draw(im)
    ink = WHITE if state == "right" else INK
    d.ellipse((24, 26, 104, 106), fill=(*INK, 230) if state != "right" else WHITE)
    lf = font("bold", 46)
    lw = text_size(d, letter, lf)[0]
    d.text((64 - lw / 2, 34), letter, font=lf, fill=WHITE if state != "right" else GREEN)
    d.text((136, 14), hanzi, font=font("zh", 72), fill=ink)
    zw = text_size(d, hanzi, font("zh", 72))[0]
    d.text((136 + zw + 28, 44), py, font=font("medium", 44), fill=ink)
    if state == "right":
        d.line((680, 66, 700, 88, 734, 44), fill=WHITE, width=12, joint="curve")
    return im


def answer_card(w, accent, sub=None):
    cw = 880
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    tf, sf = font("medium", 36), font("medium", 32)
    trick = [(ln, tf, (220, 220, 230)) for ln in wrap(d, w["trick"], tf, cw - 80)[:2]]
    if sub and w.get(f"trick_{sub}"):
        trick += [(ln, sf, (170, 200, 255)) for ln in wrap(d, w[f"trick_{sub}"], sf, cw - 80)[:2]]
    im = panel(cw, 410 + 42 * len(trick), fill=(12, 12, 18, 215))
    d = ImageDraw.Draw(im)
    zf = font("zh", 190)
    zw = text_size(d, w["hanzi"], zf)[0]
    d.text(((cw - zw) / 2, -6), w["hanzi"], font=zf, fill=WHITE)
    pf = font("demi", 64)
    syl = syllables(w["pinyin"])
    total = sum(text_size(d, s, pf)[0] for s, _ in syl) + 10 * (len(syl) - 1)
    x = (cw - total) / 2
    for s, t in syl:
        d.text((x, 236), s, font=pf, fill=TONES[t])
        x += text_size(d, s, pf)[0] + 10
    mf = font("bold", 56)
    tail = f"  ·  {w[f'meaning_{sub}']}" if sub and w.get(f"meaning_{sub}") else ""  # "train · tàu hỏa"
    mw, tw_ = text_size(d, w["meaning"], mf)[0], text_size(d, tail, mf)[0] if tail else 0
    x = (cw - mw - tw_) / 2
    d.text((x, 322), w["meaning"], font=mf, fill=accent)
    if tail:
        d.text((x + mw, 322), tail, font=mf, fill=WHITE)
    for i, (ln, f_, col) in enumerate(trick):
        lw = mixed(d, (0, 0), ln, f_, measure=True)
        mixed(d, ((cw - lw) / 2, 396 + i * 42), ln, f_, col)
    return im


def cue_card(text, meaning, sub_text=None, sub_meaning=None):
    cw = 880
    rows = [(text, font("demi", 40), (210, 210, 220), 52)]
    if sub_text:
        rows.append((sub_text, font("demi", 32), (170, 200, 255), 44))
    rows.append((meaning, font("bold", 104), WHITE, 128))
    if sub_meaning:
        rows.append((sub_meaning, font("bold", 58), (170, 200, 255), 70))
    im = panel(cw, sum(r[3] for r in rows) + 48, fill=(12, 12, 18, 205))
    d = ImageDraw.Draw(im)
    y = 30
    for t_, f_, col, lh in rows:
        tw = text_size(d, t_, f_)[0]
        d.text(((cw - tw) / 2, y - (f_.size * 0.12 if f_.size > 60 else 0)), t_, font=f_, fill=col)
        y += lh
    return im


def dots(n, done, accent, current=None):
    im = Image.new("RGBA", (n * 48 + 140, 60))
    d = ImageDraw.Draw(im)
    for i in range(n):
        x = 10 + i * 48
        fill = (*accent, 255) if i < done else (255, 255, 255, 90)
        d.ellipse((x, 14, x + 32, 46), fill=fill, outline=WHITE if i == current else None, width=4)
    d.text((n * 48 + 20, 6), f"{done}/{n}", font=font("bold", 42), fill=WHITE)
    return im


def ring(left, total, accent):
    """Countdown ring: arc drains as `left` seconds run out, red with a pulse in the last second."""
    s = 220
    im = Image.new("RGBA", (s, s))
    d = ImageDraw.Draw(im)
    hot = left <= 1.0
    col = (255, 70, 70) if hot else accent
    d.ellipse((10, 10, s - 10, s - 10), fill=(12, 12, 18, 200))
    d.arc((14, 14, s - 14, s - 14), -90, -90 + 360 * left / total, fill=col, width=18)
    n = str(max(1, math.ceil(left)))
    f = font("bold", 110 + (12 if hot and (left % 1) > 0.7 else 0))
    tw, th, top = text_size(d, n, f)
    d.text(((s - tw) / 2, (s - th) / 2 - top), n, font=f, fill=WHITE)
    return im


def shadowed(im, blur=12, strength=200):
    """Soft dark halo behind white text so it reads on any photo."""
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, v * strength // 100))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(a)
    return Image.alpha_composite(sh, im)


def scaled(im, k, alpha=1.0):
    if k <= 0 or alpha <= 0:
        return None
    if abs(k - 1) > 0.01:
        im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.BICUBIC)
    if alpha < 0.99:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy()
        im.putalpha(a)
    return im


def put(frame, im, cx, cy):
    if im is not None:
        frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


# ---------- backgrounds ----------

class Scene:
    def __init__(self, path, zoom_from=1.0, zoom_to=1.12):
        self.path, self.z0, self.z1 = Path(path), zoom_from, zoom_to
        self.proc = None
        if self.path.suffix == ".png":
            self.img = Image.open(self.path).convert("RGB").resize((W, H), Image.LANCZOS)

    def frame(self, t, dur, z=None):
        if self.path.suffix == ".png":
            z = z or self.z0 + (self.z1 - self.z0) * (t / dur)
            cw, ch = W / z, H / z
            x, y = (W - cw) / 2, (H - ch) / 2.2
            return self.img.resize((W, H), Image.BILINEAR, box=(x, y, x + cw, y + ch))
        if self.proc is None:
            self.proc = subprocess.Popen(
                ["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", str(self.path), "-vf",
                 f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        raw = self.proc.stdout.read(W * H * 3)
        return Image.frombytes("RGB", (W, H), raw)

    def close(self):
        if self.proc:
            self.proc.kill()
            self.proc = None


def scene_path(work, i):
    for ext in (".mp4", ".png"):
        p = work / "scenes" / f"{i:02d}{ext}"
        if p.exists():
            return p
    sys.exit(f"missing scene {i:02d}.mp4/png in {work / 'scenes'} (quiz.py scenes)")


# ---------- sound ----------

def tone(freq, dur, decay, amp, sweep=None):
    t = np.arange(int(dur * SR)) / SR
    f = freq if sweep is None else np.linspace(freq, sweep, t.size)
    ph = 2 * np.pi * np.cumsum(f) / SR if sweep is not None else 2 * np.pi * freq * t
    return amp * np.sin(ph) * np.exp(-t / decay)


def noise(dur, amp, rise=True):
    n = int(dur * SR)
    rng = np.random.default_rng(7)
    x = np.cumsum(rng.standard_normal(n)) * 0.02
    x = np.diff(x, prepend=0) + rng.standard_normal(n) * 0.3
    env = np.sin(np.linspace(0, np.pi, n)) ** (0.6 if rise else 2)
    return amp * x * env


def layer(*ys):
    out = np.zeros(max(y.size for y in ys))
    for y in ys:
        out[:y.size] += y
    return out


SFX = {
    "hit": lambda: layer(tone(55, 0.6, 0.18, 0.9, sweep=40), tone(110, 0.3, 0.06, 0.3)),
    "whoosh": lambda: noise(0.45, 0.35),
    "tick": lambda: tone(2600, 0.04, 0.008, 0.35),
    "tock": lambda: tone(1900, 0.04, 0.008, 0.35),
    "pop": lambda: tone(700, 0.08, 0.03, 0.4, sweep=320),
    "chime": lambda: layer(tone(880, 0.9, 0.3, 0.3), tone(1318.5, 0.9, 0.25, 0.22), tone(1760, 0.6, 0.15, 0.12)),
    "swish": lambda: noise(0.25, 0.22, rise=False),
}


def add(bus, t, y, gain=1.0):
    i = int(t * SR)
    if i >= bus.size:
        return
    y = y[: bus.size - i]
    bus[i:i + y.size] += y * gain


def wav(path):
    y, sr = sf.read(path, dtype="float32")
    assert sr == SR, f"{path}: {sr} Hz"
    return y if y.ndim == 1 else y.mean(axis=1)


# ---------- main ----------

def main(quiz_path, work, out):
    q = json.loads(Path(quiz_path).read_text())
    work = Path(work)
    voice = work / "voice"
    words = q["words"]
    n = len(words)
    accent = hexrgb(q.get("accent", "#FF3B5C"))
    ui = UI[q.get("lang", "en")]
    sub = q.get("sub")  # second language under every English line, e.g. "vi"
    sui = UI[sub] if sub else {}

    def sv(obj, key):
        return obj.get(f"{key}_{sub}") if sub else None
    total = HOOK + n * WORD + OUTRO
    rehooks = q.get("rehooks", [])
    rehook_at = dict(zip([2, 4, n - 1, n][-len(rehooks):] if rehooks else [], rehooks, strict=False))
    rehook_sub = dict(zip(rehook_at, q.get(f"rehooks_{sub}", []), strict=False)) if sub else {}

    # static layers
    boss = words[-1]
    hook_sticker = sticker(q["hook"]["text"], 76, accent, tilt=-3, sub=sv(q["hook"], "text"))
    boss_big = Image.new("RGBA", (900, 380))
    d = ImageDraw.Draw(boss_big)
    zf = font("zh", 250)
    zw = text_size(d, boss["hanzi"] + "?", zf)[0]
    d.text(((900 - zw) / 2, 20), boss["hanzi"] + "?", font=zf, fill=WHITE)
    boss_big = shadowed(boss_big, 16, 260)
    teaser = sticker(q["hook"].get("boss_teaser", "Can you read this?"), 50, INK, sub=sv(q["hook"], "boss_teaser"))
    series = sticker(f"{q.get('series', 'Chinese')} · {q.get('level', '')}".strip(" ·"), 34, INK)
    outro_s = sticker(q["outro"]["text"], 84, accent, tilt=-2, sub=sv(q["outro"], "text"))
    cta = sticker(q["outro"]["cta"], 44, INK, sub=sv(q["outro"], "cta"))
    letters = "ABC"
    per = []
    for i, w in enumerate(words, 1):
        opts = [(w["hanzi"], w["pinyin"])] + [tuple(x) for x in w["decoys"]]
        seed = int(hashlib.md5(w["hanzi"].encode()).hexdigest(), 16)
        right = seed % 3
        order = [opts[1], opts[2]]
        order.insert(right, opts[0])
        per.append(dict(
            cue=cue_card(ui["cue"], w["meaning"], sui.get("cue"), sv(w, "meaning")), ans=answer_card(w, accent, sub),
            right=right,
            plain=[choice(letters[k], h, p, "plain") for k, (h, p) in enumerate(order)],
            shown=[choice(letters[k], h, p, "right" if k == right else "wrong") for k, (h, p) in enumerate(order)],
            rehook=sticker(ui["boss"] if i == n else rehook_at[i], 52, (255, 210, 0), INK, tilt=4,
                           sub=sui.get("boss") if i == n else rehook_sub.get(i))
            if (i == n or i in rehook_at) else None))
    dot_cache, veils = {}, {}

    def veil(a, rgb=(0, 0, 0)):
        k = (int(a), rgb)
        if k not in veils:
            veils[k] = Image.new("RGBA", (W, H), (*rgb, int(a)))
        return veils[k]

    def dotrow(done, cur):
        k = (done, cur)
        if k not in dot_cache:
            dot_cache[k] = dots(n, done, accent, cur)
        return dot_cache[k]

    scenes = [Scene(scene_path(work, i)) for i in range(1, n + 1)]
    boss_scene = Scene(scene_path(work, n), 1.25, 1.06)
    outro_scene = Scene(scene_path(work, n), 1.12, 1.25)
    # outro zooms back toward the hook's first framing so the loop seam is soft

    tmp = Path(out).with_suffix(".video.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    frames = round(total * FPS)
    for fi in range(frames):
        t = fi / FPS
        if t < HOOK:
            bg = boss_scene.frame(t, HOOK, 1.25 - 0.15 * ease(t / 0.6) - 0.04 * t / HOOK)  # punch-in, then drift
            fr = bg.convert("RGBA")
            fr.alpha_composite(veil(70))
            if 0 < t < 0.15:  # flash right after frame 0: a pattern break; frame 0 (the cover) stays clean
                fr.alpha_composite(veil(120 * (1 - t / 0.15), (255, 255, 255)))
            put(fr, scaled(series, 1, ease(t / 0.3)), 540, 250)
            put(fr, scaled(hook_sticker, pop(t + 0.12)), 540, 420)  # already on frame 0
            put(fr, scaled(boss_big, pop(t + 0.08, 0.35)), 540, 860)
            put(fr, scaled(teaser, pop(t - 0.3)), 540, 1110)
            put(fr, scaled(dotrow(0, None), 1, ease((t - 0.45) / 0.3)), 540, 1290)
            if t > HOOK - 0.25:  # swish out
                fr.alpha_composite(veil(int(160 * (t - HOOK + 0.25) / 0.25), (255, 255, 255)))
        elif t < HOOK + n * WORD:
            i = int((t - HOOK) // WORD)
            lt = t - HOOK - i * WORD
            p = per[i]
            if lt < 1 / FPS and i:
                scenes[i - 1].close()
            fr = scenes[i].frame(lt, WORD).convert("RGBA")
            fr.alpha_composite(veil(60 if lt < CUE + COUNT else 95))
            if lt < 0.15:
                fr.alpha_composite(veil(160 * (1 - lt / 0.15), (255, 255, 255)))
            put(fr, dotrow(i + (lt >= CUE + COUNT), i), 540, 240)
            reveal = lt - CUE - COUNT
            if reveal < 0:
                put(fr, scaled(p["cue"], pop(lt - 0.05)), 540, 690)
                if p["rehook"] is not None and lt < CUE:
                    put(fr, scaled(p["rehook"], pop(lt - 0.1), ease((CUE - lt) / 0.25)), 540, 440)
                elif lt >= CUE:
                    put(fr, ring(COUNT - (lt - CUE), COUNT, accent), 540, 440)
                for k in range(3):
                    put(fr, scaled(p["plain"][k], pop(lt - 0.35 - 0.12 * k)), 480, 1000 + k * 156)
            else:
                put(fr, scaled(p["ans"], pop(reveal, 0.3)), 540, 640)
                for k in range(3):
                    put(fr, p["shown"][k], 480, 1000 + k * 156)
        else:
            ot = t - HOOK - n * WORD
            fr = outro_scene.frame(ot, OUTRO).convert("RGBA")
            fr.alpha_composite(veil(int(110 * ease(ot / 0.4))))
            put(fr, scaled(outro_s, pop(ot)), 540, 600)
            put(fr, dotrow(n, None), 540, 820)
            put(fr, scaled(cta, pop(ot - 0.3)), 540, 980)
            if ot > OUTRO - 0.35:  # fade the cards out so the last frame ~ the hook's first scene
                seam = outro_scene.frame(ot, OUTRO).convert("RGBA")
                seam.alpha_composite(veil(70))  # the hook's scrim
                fr = Image.blend(fr, seam, (ot - OUTRO + 0.35) / 0.35)
        enc.stdin.write(fr.convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()

    # sound
    bus = np.zeros(int(total * SR) + SR, np.float32)
    vox = np.zeros_like(bus)
    add(bus, 0, SFX["hit"]())
    add(bus, 0, SFX["whoosh"]())
    add(vox, 0.25, wav(voice / "hook.wav"))
    for at in (0.0, 0.3, 0.45):
        add(bus, at, SFX["pop"](), 0.7)
    for k in range(int(HOOK / 0.25)):  # clock ticking under the hook: urgency, and no dead air between lines
        add(bus, 0.5 + k * 0.25, SFX["tick" if k % 2 == 0 else "tock"](), 0.55)
    add(bus, HOOK - 0.25, SFX["swish"]())
    for i in range(n):
        s = HOOK + i * WORD
        add(bus, s, SFX["swish"](), 0.8)
        for k in range(3):
            add(bus, s + 0.35 + 0.12 * k, SFX["pop"](), 0.5)
        for sec in range(int(COUNT) - 1):
            add(bus, s + CUE + sec, SFX["tick" if sec % 2 == 0 else "tock"]())
        for q4 in range(4):  # last second: double-time ticks
            add(bus, s + CUE + COUNT - 1 + q4 * 0.25, SFX["tick"](), 1.1)
        r = s + CUE + COUNT
        add(bus, r, SFX["chime"]())
        slow = wav(voice / f"{i + 1:02d}_slow.wav")
        add(vox, r + 0.3, slow)
        add(vox, r + 0.3 + slow.size / SR + 0.45, wav(voice / f"{i + 1:02d}.wav"))
    o = HOOK + n * WORD
    add(bus, o, SFX["whoosh"](), 0.8)
    add(vox, o + 0.3, wav(voice / "outro.wav"))
    mix = bus * 0.8 + vox
    music = os.environ.get("MUSIC")
    if music:
        m = subprocess.run(["ffmpeg", "-v", "error", "-i", music, "-t", str(total), "-ac", "1", "-ar", str(SR),
                            "-f", "f32le", "-"], capture_output=True, check=True).stdout
        m = np.frombuffer(m, np.float32)[: bus.size]
        env = np.convolve(np.abs(vox) > 0.01, np.ones(SR // 5) / (SR // 5), mode="same")  # voice present
        duck = 1 - 0.65 * np.clip(env * 4, 0, 1)
        mix[: m.size] += m * 0.28 * duck[: m.size]
    mix = mix[: int(total * SR)]
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    audio = Path(out).with_suffix(".audio.wav")
    sf.write(audio, mix, SR)
    # tame tick / chime peaks first, or the true-peak ceiling keeps linear loudnorm under target
    limited = audio.with_suffix(".lim.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(audio), "-af",
                    "acompressor=threshold=-20dB:ratio=3:attack=3:release=120,alimiter=limit=0.35:level=false",
                    str(limited)], check=True)
    limited.replace(audio)
    # two-pass loudnorm: one pass undershoots on sparse quiz audio (-16 instead of -14 LUFS)
    ln = "loudnorm=I=-14:TP=-1.5:LRA=11"
    st = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(audio), "-af", ln + ":print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    m = json.loads(st[st.rindex("{"):st.rindex("}") + 1])
    ln += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-i", str(audio), "-c:v", "copy",
                    "-af", ln, "-ar", str(SR), "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    tmp.unlink()
    audio.unlink()
    print(f"{out} {total:.1f}s {n} words")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
