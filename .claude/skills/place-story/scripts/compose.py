# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "fonttools"]
# ///
"""Compose a place-story: one muse shot per beat, a fact card over each, soft dissolves, one music bed.

  uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/compose.py \
      --story story.json --music track.m4a --out story-<slug>.mp4 [--dry]

story.json (clip paths relative to the story file):
  {"place": "Angkor Wat", "sub": "Siem Reap, Cambodia 🇰🇭",
   "beats": [
     {"kind": "hook", "clip": "s1.mp4", "pos": "low", "title": "Why does the world's biggest temple face west? 🤔"},
     {"kind": "fact", "clip": "s2.mp4", "kicker": "FACT 1/8", "title": "...", "body": "...", "src": "..."},
     {"kind": "end",  "clip": "s10.mp4", "title": "...", "body": "...", "cta": "Follow for part 2"}]}
Kinds `plain` (no card) and `note` ("kicker": title, one small line: body) serve nature-reel.
A beat's `secs` overrides the reading time (READ_*). Prints each beat's window and the total length.
Narration: when vo/b<N>.wav exists next to story.json (scripts/vo.py writes it from the beat's `vo`), the
line starts VO_LEAD after the cut, the beat lasts at least the line plus VO_GAP, and the music ducks under
the voice. `--dry` prints the beat timing and total only (size the music with it before rendering).
"""
import argparse
import io
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from fontTools.ttLib import TTCollection
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 24
XF = 0.7  # dissolve between beats; slower reads as calm documentary, not a reel
# safe zone on 9:16 feeds: TikTok/Reels/Shorts cover ~220 px on top, ~420 px at the bottom
# (caption + music line) and ~150 px on the right (like/comment/share column)
SAFE_TOP, SAFE_BOTTOM, SAFE_RIGHT, MARGIN = 230, 430, 150, 60
# viewers read a card while watching the view: ~3.2 words/s plus 1.4 s to find the card. Angkor test
# (2026-11-09): 2.6 words/s with an 8 s cap put most beats at 8 s, 75 s in all; 6.2 s keeps 8 facts near 55 s
READ_BASE, READ_WPS, READ_MIN, READ_MAX = 1.4, 3.2, 4.5, 6.2
HOOK_SECS = 3.8
# a line starts once the dissolve has mostly settled, and ~0.9 s of music breathes between lines
VO_LEAD, VO_GAP, HOOK_VO_LEAD = 0.5, 0.4, 0.15
MUSIC_UNDER_VO = 0.22  # bed level while narration plays (sidechain ducks it further on each word)
BRIGHT = 110  # same floor as scenic-drop-reel: lift a shot darker than this mean luma
GRADE = "eq=saturation=1.1:contrast=1.03:brightness=0.02,unsharp=5:5:0.4"
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
FONTS = {"heavy": ("/System/Library/Fonts/Avenir Next.ttc", 8),
         "demi": ("/System/Library/Fonts/Avenir Next.ttc", 2)}
YELLOW = (255, 214, 74, 255)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]))


def ydif(path):
    out = run(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
               "scale=270:-2,signalstats,metadata=print:key=lavfi.signalstats.YDIF:file=-", "-an", "-f", "null", "-"])
    return [float(x.split("=")[1]) for x in out.splitlines() if "YDIF=" in x]


def luma(path):
    out = run(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
               "fps=2,scale=270:-2,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-", "-an", "-f", "null", "-"])
    v = [float(x.split("=")[1]) for x in out.splitlines() if "YAVG=" in x]
    return sum(v) / len(v)


def window(path, need):
    """Start (s) of the steadiest `need`-second stretch: the lowest spread of frame-to-frame change,
    skipping muse's first 0.5 s (it often settles there) and any window with a jump > 3x its median."""
    d = ydif(path)
    n = round(need * FPS)
    if len(d) <= n + 12:
        return max(0.0, (len(d) - n) / FPS), None
    best = None
    for j in range(12, len(d) - n):
        win = d[j:j + n]
        mean = sum(win) / n
        std = (sum((x - mean) ** 2 for x in win) / n) ** 0.5
        med = sorted(win)[n // 2]
        score = std + (100 if max(win) > 3 * med + 5 else 0)
        if best is None or score < best[0]:
            best = (score, j)
    return best[1] / FPS, best[0]


# ---------- text ----------
def font(kind, size):
    path, idx = FONTS[kind]
    if not Path(path).exists():  # Linux (a Colab render): the closest installed sans, bold for "heavy"
        # name the family: Colab's fontconfig answers "sans-serif:bold" with Liberation Mono (2026-11-17)
        style = "bold" if kind == "heavy" else "semibold"
        for fam in ("DejaVu Sans", "Liberation Sans", "Noto Sans"):
            path, idx = run(["fc-match", "-f", "%{file}", f"{fam}:{style}"]).strip(), 0
            if "Mono" not in path:
                break
    return ImageFont.truetype(path, size, index=idx)


def emoji(text, height):
    if not Path(EMOJI_FONT).exists():  # no Apple emoji off macOS: leave the glyph out
        return Image.new("RGBA", (1, height))
    f = TTCollection(EMOJI_FONT, lazy=True).fonts[0]
    name = "_".join(f"u{ord(c):04X}" for c in text if ord(c) != 0xFE0F)
    glyph = f["sbix"].strikes[160].glyphs.get(name)
    if glyph is None or glyph.graphicType != "png ":
        sys.exit(f"no emoji bitmap for {text!r} ({name})")
    img = Image.open(io.BytesIO(glyph.imageData)).convert("RGBA")
    img = img.crop(img.getbbox())
    return img.resize((round(img.width * height / img.height), height), Image.LANCZOS)


def is_emoji(ch):
    return ord(ch) > 0x2500 or ord(ch) == 0xFE0F


def tokens(text):
    """Words, with an emoji run (a flag is two code points) kept as its own token."""
    out = []
    for word in text.split():
        i = len(word)
        while i and is_emoji(word[i - 1]):
            i -= 1
        if word[:i]:
            out.append(word[:i])
        if word[i:]:
            out.append(word[i:])
    return out


def width(d, tok, f):
    return f.size * 0.95 if is_emoji(tok[0]) else d.textlength(tok, font=f)


def wrap(d, text, f, max_w):
    lines, cur = [], []
    space = d.textlength(" ", font=f)
    for tok in tokens(text):
        trial = cur + [tok]
        # an emoji never starts a line alone: it stays with the word before it
        if cur and not is_emoji(tok[0]) and sum(width(d, t, f) for t in trial) + space * (len(trial) - 1) > max_w:
            lines.append(cur)
            cur = [tok]
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def draw_line(img, x, y, toks, f, fill, center_w=None, shadow=True):
    """Draw one wrapped line at baseline y; centred in [x, x+center_w] when center_w is given."""
    d = ImageDraw.Draw(img)
    space = d.textlength(" ", font=f)
    total = sum(width(d, t, f) for t in toks) + space * (len(toks) - 1)
    cx = x + (center_w - total) / 2 if center_w else x
    if shadow:
        sh = Image.new("RGBA", img.size)
        sd = ImageDraw.Draw(sh)
        px = cx
        for t in toks:
            if not is_emoji(t[0]):
                sd.text((px + 3, y + 4), t, font=f, fill=(0, 0, 0, 170), anchor="ls")
            px += width(d, t, f) + space
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(max(2, f.size / 12))))
    px = cx
    for t in toks:
        if is_emoji(t[0]):
            em = emoji(t, round(f.size * 0.85))
            img.alpha_composite(em, (round(px), round(y - em.height + f.size * 0.08)))
        else:
            d.text((px, y), t, font=f, fill=fill, anchor="ls")
        px += width(d, t, f) + space


def scrim(img, top, alpha=175):
    """Dark gradient from `top` to the bottom so white text reads on bright sky or sand."""
    g = Image.new("L", (1, H - top))
    for y in range(H - top):
        g.putpixel((0, y), round(alpha * min(1, (y / (H - top)) * 1.6) ** 1.3))
    layer = Image.new("RGBA", (W, H - top), (0, 0, 0, 255))
    layer.putalpha(g.resize((W, H - top)))
    img.alpha_composite(layer, (0, top))


def card(beat, place, sub):
    """RGBA overlay for one beat."""
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    max_w = W - MARGIN - SAFE_RIGHT - 40
    if beat["kind"] == "note":
        fk, fb = font("heavy", 38), font("demi", 44)
        body = wrap(d, beat.get("body", ""), fb, W - MARGIN - SAFE_RIGHT - 60)
        lh = round(fb.size * 1.3)
        h = 52 + len(body) * lh
        base = H - SAFE_BOTTOM - 20
        top = base - h - 40
        g = Image.new("L", (1, 520))
        for y in range(520):
            g.putpixel((0, y), round(170 * math.sin(math.pi * y / 520)))
        band = Image.new("RGBA", (W, 520), (0, 0, 0, 255))
        band.putalpha(g.resize((W, 520)))
        img.alpha_composite(band, (0, H - SAFE_BOTTOM - 440))
        y = top + 40
        draw_line(img, MARGIN, y, tokens(beat["title"]), fk, YELLOW)
        for ln in body:
            y += lh
            draw_line(img, MARGIN, y, ln, fb, (255, 255, 255, 255))
        return img
    if beat["kind"] == "plain":
        return img
    if beat["kind"] == "hook":
        # big centred hook, readable from frame 0 (the first 2 s decide). "pos": "low" puts it over the lower
        # half (calm water, sky reflection) when the landmark fills the top: Angkor test (2026-11-09), the
        # hook at the top covered the five towers
        low = beat.get("pos") == "low"
        top = Image.new("RGBA", (W, 900))
        g = Image.new("L", (1, 900))
        for y in range(900):
            g.putpixel((0, y), round(190 * math.sin(math.pi * y / 900)) if low else round(200 * (1 - y / 900) ** 1.2))
        top.paste((0, 0, 0, 255), (0, 0, W, 900))
        top.putalpha(g.resize((W, 900)))
        img.alpha_composite(top, (0, H // 2) if low else (0, 0))
        f, fs = font("heavy", 92), font("demi", 46)
        lines = wrap(d, beat["title"], f, W - 2 * MARGIN - 40)
        y = H // 2 + 200 if low else SAFE_TOP + 100
        for ln in lines:
            draw_line(img, MARGIN, y, ln, f, (255, 255, 255, 255), center_w=W - 2 * MARGIN)
            y += round(f.size * 1.14)
        draw_line(img, MARGIN, y + 30, tokens(f"{place} · {sub}"), fs, YELLOW, center_w=W - 2 * MARGIN)
        return img

    fk, ft, fb = font("heavy", 40), font("heavy", 70), font("demi", 46)
    title = wrap(d, beat["title"], ft, max_w)
    body = wrap(d, beat.get("body", ""), fb, max_w) if beat.get("body") else []
    cta = beat.get("cta")
    h = 58 + len(title) * round(ft.size * 1.12) + (18 + len(body) * round(fb.size * 1.32) if body else 0)
    h += 120 if cta else 0
    bottom = H - SAFE_BOTTOM
    y0 = bottom - h
    scrim(img, max(SAFE_TOP, y0 - 380))
    # yellow accent bar beside the text, like a documentary lower third
    d.rounded_rectangle((MARGIN, y0 - 6, MARGIN + 8, y0 + h - (120 if cta else 0) - 10), radius=4, fill=YELLOW)
    x = MARGIN + 34
    y = y0 + 34
    kicker = beat.get("kicker", "")
    if kicker:
        d.text((x, y), kicker.upper(), font=fk, fill=YELLOW, anchor="ls")
    y += 24 + round(ft.size * 0.95)
    for ln in title:
        draw_line(img, x, y, ln, ft, (255, 255, 255, 255))
        y += round(ft.size * 1.12)
    if body:
        y += 18 - round(ft.size * 0.12) + round(fb.size * 0.2)
        for ln in body:
            draw_line(img, x, y, ln, fb, (240, 240, 240, 255))
            y += round(fb.size * 1.32)
    if cta:
        fc = font("heavy", 46)
        toks = tokens(cta)
        tw = sum(width(d, t, fc) for t in toks) + d.textlength(" ", font=fc) * (len(toks) - 1)
        py = y + 30
        d.rounded_rectangle((x, py, x + tw + 64, py + 84), radius=42, fill=YELLOW)
        draw_line(img, x + 32, py + 58, toks, fc, (20, 20, 20, 255), shadow=False)
    return img


def vo_path(base, i):
    p = base / "vo" / f"b{i + 1}.wav"
    return p if p.exists() else None


def lead(beat):
    return HOOK_VO_LEAD if beat["kind"] == "hook" else VO_LEAD


def read_secs(beat):
    if beat.get("secs"):
        return float(beat["secs"])
    if beat["kind"] == "hook":
        return HOOK_SECS
    words = len((beat.get("title", "") + " " + beat.get("body", "") + " " + beat.get("cta", "")).split())
    return min(READ_MAX, max(READ_MIN, READ_BASE + words / READ_WPS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", required=True)
    ap.add_argument("--music", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    story_path = Path(a.story).resolve()
    story = json.loads(story_path.read_text())
    base = story_path.parent
    beats = story["beats"]
    tmp = Path(tempfile.mkdtemp(prefix="story-"))
    vos = [vo_path(base, i) for i in range(len(beats))]
    plan = []
    for i, b in enumerate(beats):
        secs = read_secs(b)
        if vos[i] and not b.get("secs"):
            secs = max(secs, lead(b) + duration(vos[i]) + VO_GAP)
        plan.append(secs)
    if a.dry:
        print(" ".join(f"{s:.1f}" for s in plan), f"total {sum(plan):.1f} s,",
              f"music --body-beats {math.ceil(sum(plan) * 84 / 60) + 4} at 84 BPM")
        return
    segs, t, starts = [], 0.0, []
    for i, b in enumerate(beats):
        secs = plan[i]
        starts.append(t)
        last = i == len(beats) - 1
        seg_len = secs + (0 if last else XF)
        clip = base / b["clip"]
        d = duration(clip)
        speed = 1.0
        if d < seg_len + 0.3:
            speed = (d - 0.3) / seg_len  # slow the clip a little rather than freeze it
            if speed < 0.75:  # slow drone motion still reads as calm; slower starts to look like a still
                print(f"warning: {clip.name} is {d:.1f} s, needs {seg_len:.1f} s: re-render longer", file=sys.stderr)
            start = 0.15
        else:
            start, _ = window(clip, seg_len)
        m = luma(clip)
        lift = ""
        if m < BRIGHT and "sunset" not in b.get("light", ""):
            g = min(1.6, math.log(m / 255) / math.log(BRIGHT / 255))
            lift = f"eq=gamma={g:.2f},"
            print(f"note: {clip.name} mean luma {m:.0f}: lifted gamma {g:.2f}", file=sys.stderr)
        ov = tmp / f"card{i}.png"
        card(b, story["place"], story.get("sub", "")).save(ov)
        fade_in = 0 if b["kind"] == "hook" else 0.45
        out_at = secs - 0.35
        vf = (f"[0:v]trim=start={start:.3f},setpts=(PTS-STARTPTS)/{speed:.4f},fps={FPS},"
              f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{lift}{GRADE},format=yuv420p[v];"
              f"[1:v]format=rgba,fade=t=in:st={fade_in}:d=0.4:alpha=1,fade=t=out:st={out_at:.2f}:d=0.35:alpha=1[o];"
              f"[v][o]overlay=0:0:format=auto,trim=duration={seg_len:.3f},format=yuv420p[out]")
        if b["kind"] == "hook":  # hook text on frame 0, no fade-in
            vf = vf.replace("fade=t=in:st=0:d=0.4:alpha=1,", "")
        seg = tmp / f"seg{i}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-loop", "1", "-framerate", str(FPS),
                        "-t", f"{seg_len + 0.5:.2f}", "-i", str(ov), "-filter_complex", vf, "-map", "[out]",
                        "-an", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-r", str(FPS), str(seg)],
                       check=True)
        segs.append((seg, seg_len))
        print(f"beat {i + 1:2d} {b['kind']:4s} {clip.name:8s} window {start:4.1f}+{seg_len:.1f}s "
              f"x{speed:.2f}  on screen {t:5.1f}-{t + secs:5.1f}s  {b.get('title', '')[:50]}")
        t += secs
    total = t
    # dissolve chain
    inputs, fc, prev, off = [], [], "0:v", 0.0
    for i, (seg, ln) in enumerate(segs):
        inputs += ["-i", str(seg)]
        if i == 0:
            off = ln - XF
            continue
        lab = f"x{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[{lab}]")
        prev, off = lab, off + ln - XF
    n = len(segs)
    music_len = duration(a.music)
    if music_len < total:
        print(f"warning: music {music_len:.1f} s < story {total:.1f} s: it fades out early; "
              f"render it longer (--body-beats)", file=sys.stderr)
    fade_out = max(0, min(total, music_len) - 3.0)
    bed = (f"[{n}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.3,"
           f"afade=t=out:st={fade_out:.2f}:d=3,apad,atrim=0:{total:.3f}")
    lines = [(i, p) for i, p in enumerate(vos) if p]
    if not lines:
        fc.append(f"{bed}[a]")
    else:
        # each line placed after its cut, mixed into one voice track; the bed sits low and a sidechain
        # compressor dips it further on every word, so the voice is always on top
        for k, (i, p) in enumerate(lines):
            inputs += ["-i", str(p)]
            ms = round((starts[i] + lead(beats[i])) * 1000)
            fc.append(f"[{n + 1 + k}:a]aresample=48000,aformat=channel_layouts=mono,highpass=f=80,loudnorm=I=-17:TP=-2:LRA=7,aresample=48000,"
                      f"adelay={ms}:all=1[l{k}]")
        fc.append("".join(f"[l{k}]" for k in range(len(lines)))
                  + f"amix=inputs={len(lines)}:normalize=0,apad,atrim=0:{total:.3f},asplit[vo][key]")
        fc.append(f"{bed},aresample=48000,volume={MUSIC_UNDER_VO}[bed]")
        fc.append("[bed][key]sidechaincompress=threshold=0.02:ratio=4:attack=30:release=500[duck]")
        fc.append("[vo][duck]amix=inputs=2:normalize=0[a]")
    music_in = ["-i", a.music]
    # music must be input n, so voice inputs (appended above) go after it
    vo_in = inputs[2 * n:]
    inputs = inputs[:2 * n]
    vfc = [x for x in fc if "xfade" in x]
    afc = [x for x in fc if "xfade" not in x]
    # audio first, then a measured (two-pass, linear) loudnorm: one-pass loudnorm is dynamic and lifts
    # the music in every pause between lines up to the voice's level
    mix = tmp / "mix.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, *music_in, *vo_in, "-filter_complex", ";".join(afc),
                    "-map", "[a]", "-ar", "48000", str(mix)], check=True)
    m = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mix), "-af", "loudnorm=I=-14:TP=-1.5:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    norm = (f"loudnorm=I=-14:TP=-1.5:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    vfc.append(f"[{n}:a]{norm}[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-i", str(mix), "-filter_complex", ";".join(vfc),
                    "-map", f"[{prev}]", "-map", "[a]", "-c:v", "libx264", "-crf", "17", "-preset", "slow",
                    "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                    "-t", f"{total:.3f}", a.out], check=True)
    print(f"{a.out}: {total:.1f} s, {n} beats")


if __name__ == "__main__":
    main()
