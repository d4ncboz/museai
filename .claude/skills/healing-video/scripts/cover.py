"""Soft 9:16 cover for a healing video: one calm frame, a hook line in a large white italic serif, a
small cream label above it (place · season). The video's own line is already burned into the frame
(compose.py, 55 % down), so the scrim band reaches down over it and no second line is drawn. Calm, never the
thumbnail skill's travel shock style: no rings, arrows or red banners. What makes it readable on a
bright frame is a soft dark scrim behind the text block (a blurred band, strengthened until the frame
under the text is dark enough for white) plus a soft shadow; the frame outside the band stays bright.
Text stays in the 9:16 safe box (x80-960, y300-1560) so platform crops and UI never cover it.
The text block (label + title) is centred on the frame (user 2026-11-12); `--size 16:9` makes the
horizontal cover for Story-mode videos (deliver.sh wants both *_9x16.jpg and *_16x9.jpg).

Usage: python3 scripts/cover.py --at healing-<slug>.mp4@auto --eyebrow "Scottish Highlands · autumn" \
           --title "slow down with me" --out thumbs/healing-<slug>_9x16.jpg
`@auto` takes the brightest sharp frame of the clip (sampled every 0.5 s); `@2.0` a fixed second.
deliver.sh takes THUMB_DIR=thumbs (it looks for *_9x16.jpg).
"""
import argparse
import datetime
import json
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

ITALIC = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
REGULAR = "/System/Library/Fonts/Supplemental/Georgia.ttf"
W, H = 1080, 1920
MAX_W = 900  # text width inside the safe box
SCRIM_L = 95  # mean luminance (0-255) allowed under the title once the scrim is on: white reads at ~5:1


def wrap(draw, text, path, size, max_w, max_lines=2):
    """Largest font at or under ``size`` that fits ``text`` in ``max_lines`` lines of ``max_w``."""
    while size >= 60:
        f = ImageFont.truetype(path, size)
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=f) <= max_w:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) <= max_lines and all(draw.textlength(ln, font=f) <= max_w for ln in lines):
            return f, lines
        size -= 6
    return f, lines


def frame_at(clip: str, t: str) -> Image.Image:
    tmp = Path(tempfile.mkdtemp())
    if t != "auto":
        out = tmp / "f.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", t or "1", "-i", clip, "-frames:v", "1", str(out)], check=True)
        return Image.open(out).convert("RGB")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-vf", "fps=2", str(tmp / "f%03d.png")], check=True)
    best, score = None, -1.0
    for p in sorted(tmp.glob("f*.png")):
        im = Image.open(p).convert("RGB")
        g = im.convert("L")
        bright = ImageStat.Stat(g).mean[0]
        sharp = ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).stddev[0]
        s = bright + 2 * sharp  # bright AND sharp: no blurred pan, no dark corner
        if s > score and bright < 215:  # not a blown-out white frame
            best, score = im, s
    return best


STYLES = ["scrim", "card", "frame", "caps"]
HISTORY = Path.home() / ".config/museai/cover-history.json"


def record(out: str, style: str, title: str):
    hist = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    hist.append({"date": datetime.date.today().isoformat(), "slug": re.sub(r"_(9x16|16x9)$", "", Path(out).stem),
                 "out": str(Path(out).resolve()), "style": style, "title": title})
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(hist, indent=1))


def spaced(d, xy, text, font, fill, gap):
    """Centred letter-spaced line at xy=(centre x, middle y)."""
    tw = sum(d.textlength(c, font=font) for c in text) + gap * (len(text) - 1)
    x = xy[0] - tw / 2
    for c in text:
        d.text((x, xy[1]), c, font=font, fill=fill, anchor="lm")
        x += d.textlength(c, font=font) + gap
    return tw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", required=True, help="clip.mp4@seconds or clip.mp4@auto")
    ap.add_argument("--eyebrow", default="", help="small cream label above the title: place · season")
    ap.add_argument("--title", required=True, help="the hook line, large italic serif, up to two lines")
    ap.add_argument("--sub", default="", help="small line under the title (normally none: the video's line is in the frame)")
    ap.add_argument("--y", type=float, default=0.50, help="centre of the text block, fraction of the height")
    ap.add_argument("--size", choices=["9:16", "16:9"], default="9:16")
    ap.add_argument("--style", choices=STYLES, default="scrim",
                    help="scrim (default; user 2026-11-17, later: every healing cover like healing-korean-harvest, one look across the feed): dark band, white italic, cream pill; card: cream card, brown italic; "
                         "frame: thin cream border, spaced label between rules; caps: dimmed frame, spaced capitals")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    global W, H, MAX_W
    if a.size == "16:9":
        W, H, MAX_W = 1920, 1080, 1500
    style = a.style

    clip, _, t = a.at.partition("@")
    img = frame_at(clip, t)
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    img = ImageEnhance.Brightness(ImageEnhance.Color(img).enhance(1.05)).enhance(1.04)  # bright, never dark

    d = ImageDraw.Draw(Image.new("RGBA", (W, H)))
    title = a.title.upper() if style == "caps" else a.title
    tgap = 8 if style == "caps" else 0
    tfont = REGULAR if style == "caps" else ITALIC
    tf, tlines = wrap(d, title, tfont, 96 if style == "caps" else 136, MAX_W * (0.8 if style == "caps" else 1))
    ef = ImageFont.truetype(ITALIC if style == "caps" else REGULAR, 38 if style == "caps" else 34)
    sf = ImageFont.truetype(REGULAR, 44)
    lh = tf.size * (1.25 if style == "caps" else 1.08)
    eyebrow_h = 110 if a.eyebrow else 0
    block_h = eyebrow_h + lh * len(tlines) + (sf.size * 1.6 if a.sub else 0)
    block_top = H * a.y - block_h / 2
    top = block_top + eyebrow_h
    block_bot = block_top + block_h
    if a.size == "9:16" and style != "card":
        block_bot = max(block_bot, H * 0.605)  # the in-frame line too

    base = img.convert("RGBA")
    regions = [(0, int(block_top), W, int(top + lh * len(tlines)))]
    if a.size == "9:16":
        regions.append((0, int(H * 0.53), W, int(H * 0.605)))
    alpha, lum, dark = 0, 0.0, base
    if style != "card":
        # Scrim: a blurred dark band over the text block (caps: the whole frame, softer at the edges),
        # stronger until white text reads on it. The title band and the in-frame line's band are judged
        # on their own: a bright wall under the small line must darken even when the sky is fine.
        alpha = 70 if style == "caps" else 90
        while True:
            scrim = Image.new("L", (W, H), 0)
            box = (0, 0, W, H) if style == "caps" else (0, block_top - 60, W, block_bot + 60)
            ImageDraw.Draw(scrim).rectangle(box, fill=alpha)
            if style == "caps":
                ImageDraw.Draw(scrim).rectangle((0, block_top - 80, W, block_bot + 80), fill=alpha + 40)
            scrim = scrim.filter(ImageFilter.GaussianBlur(70))
            dark = Image.composite(Image.new("RGBA", (W, H), (20, 14, 10, 255)), base, scrim)
            lum = max(ImageStat.Stat(dark.convert("L").crop(r)).mean[0] for r in regions)
            if lum <= SCRIM_L or alpha >= 190:
                break
            alpha += 20

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    d = ImageDraw.Draw(layer)
    ink = (255, 252, 245, 250)
    if style == "card":  # soft cream card behind the block, dark brown text, no shadow
        ink = (66, 46, 32, 255)
        tw = max(sum(d.textlength(c, font=tf) for c in ln) for ln in tlines)
        if a.eyebrow:
            tw = max(tw, sum(d.textlength(c, font=ef) + 5 for c in a.eyebrow.upper()))
        pad_x, pad_y = 70, 50
        d.rounded_rectangle(((W - tw) / 2 - pad_x, block_top - pad_y,
                             (W + tw) / 2 + pad_x, block_bot + pad_y), radius=28, fill=(250, 244, 233, 228))
    if style == "frame":  # thin cream inset border round the picture
        m = 44
        d.rectangle((m, m, W - m, H - m), outline=(248, 240, 226, 230), width=3)
    y = top + tf.size
    for ln in tlines:
        if tgap:
            spaced(sd, (W / 2, y - tf.size * 0.35 + 4), ln, tf, (0, 0, 0, 200), tgap)
            spaced(d, (W / 2, y - tf.size * 0.35), ln, tf, ink, tgap)
        else:
            x = (W - d.textlength(ln, font=tf)) / 2
            if style != "card":
                sd.text((x, y + 4), ln, font=tf, fill=(0, 0, 0, 200), anchor="ls")
            d.text((x, y), ln, font=tf, fill=ink, anchor="ls")
        y += lh
    if a.sub:
        y += sf.size * 0.3
        x = (W - d.textlength(a.sub, font=sf)) / 2
        sd.text((x, y + 3), a.sub, font=sf, fill=(0, 0, 0, 190), anchor="ls")
        d.text((x, y), a.sub, font=sf, fill=ink, anchor="ls")
    if a.eyebrow:
        py = top - (70 if style == "caps" else 100)
        if style == "scrim":  # cream pill, dark brown small caps with letter spacing
            text = a.eyebrow.upper()
            tw = sum(d.textlength(c, font=ef) for c in text) + 5 * (len(text) - 1)
            px = (W - tw) / 2 - 34
            d.rounded_rectangle((px, py - 30, px + tw + 68, py + 34), radius=32, fill=(248, 240, 226, 235))
            spaced(d, (W / 2, py + 2), text, ef, (74, 52, 36, 255), 5)
        elif style == "caps":  # small italic line, sentence case
            spaced(sd, (W / 2, py + 3), a.eyebrow, ef, (0, 0, 0, 190), 1)
            spaced(d, (W / 2, py), a.eyebrow, ef, (248, 240, 226, 245), 1)
        else:  # card / frame: spaced capitals between two thin rules
            col = (120, 92, 66, 255) if style == "card" else (248, 240, 226, 245)
            if style == "frame":
                spaced(sd, (W / 2, py + 3), a.eyebrow.upper(), ef, (0, 0, 0, 190), 6)
            tw = spaced(d, (W / 2, py), a.eyebrow.upper(), ef, col, 6)
            for sx in (-1, 1):
                x0 = W / 2 + sx * (tw / 2 + 24)
                d.line((x0, py, x0 + sx * 70, py), fill=col, width=2)
    layer = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)), layer)
    out = Image.alpha_composite(dark, layer).convert("RGB")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out, quality=92)
    record(a.out, style, a.title)
    print(f"THUMB {a.out} {Path(a.out).stat().st_size // 1024} KB style={style} scrim={alpha} lum={lum:.0f}")


if __name__ == "__main__":
    main()
