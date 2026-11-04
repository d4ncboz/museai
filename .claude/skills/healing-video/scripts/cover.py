"""Soft 9:16 cover for a healing video: one calm frame, a hook line in a large white italic serif, a
small cream label above it (place · season). The video's own line is already burned into the frame
(compose.py, 55 % down), so the scrim band reaches down over it and no second line is drawn. Calm, never the
thumbnail skill's travel shock style: no rings, arrows or red banners. What makes it readable on a
bright frame is a soft dark scrim behind the text block (a blurred band, strengthened until the frame
under the text is dark enough for white) plus a soft shadow; the frame outside the band stays bright.
Text stays in the 9:16 safe box (x80-960, y300-1560) so platform crops and UI never cover it.

Usage: python3 scripts/cover.py --at healing-<slug>.mp4@auto --eyebrow "Scottish Highlands · autumn" \
           --title "slow down with me" --out thumbs/healing-<slug>_9x16.jpg
`@auto` takes the brightest sharp frame of the clip (sampled every 0.5 s); `@2.0` a fixed second.
deliver.sh takes THUMB_DIR=thumbs (it looks for *_9x16.jpg).
"""
import argparse
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", required=True, help="clip.mp4@seconds or clip.mp4@auto")
    ap.add_argument("--eyebrow", default="", help="small cream label above the title: place · season")
    ap.add_argument("--title", required=True, help="the hook line, large italic serif, up to two lines")
    ap.add_argument("--sub", default="", help="small line under the title (normally none: the video's line is in the frame)")
    ap.add_argument("--y", type=float, default=0.40, help="title centre, fraction of the height")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    clip, _, t = a.at.partition("@")
    img = frame_at(clip, t)
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    img = ImageEnhance.Brightness(ImageEnhance.Color(img).enhance(1.05)).enhance(1.04)  # bright, never dark

    d = ImageDraw.Draw(Image.new("RGBA", (W, H)))
    tf, tlines = wrap(d, a.title, ITALIC, 136, MAX_W)
    ef = ImageFont.truetype(REGULAR, 34)
    sf = ImageFont.truetype(REGULAR, 44)
    lh = tf.size * 1.08
    top = H * a.y - lh * len(tlines) / 2
    block_top = top - (110 if a.eyebrow else 0)
    block_bot = max(top + lh * len(tlines) + (sf.size * 1.6 if a.sub else 0), H * 0.605)  # the in-frame line too

    # Scrim: a blurred dark band over the text block, stronger until white text reads on it.
    base = img.convert("RGBA")
    # Judge the title band and the in-frame line's band on their own: a bright house wall under the
    # small line must darken even when the sky under the title is already fine.
    regions = [(0, int(block_top), W, int(top + lh * len(tlines))), (0, int(H * 0.53), W, int(H * 0.605))]
    alpha = 90
    while True:
        scrim = Image.new("L", (W, H), 0)
        ImageDraw.Draw(scrim).rectangle((0, block_top - 60, W, block_bot + 60), fill=alpha)
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
    y = top + tf.size
    for ln in tlines:
        x = (W - d.textlength(ln, font=tf)) / 2
        sd.text((x, y + 4), ln, font=tf, fill=(0, 0, 0, 200), anchor="ls")
        d.text((x, y), ln, font=tf, fill=(255, 252, 245, 250), anchor="ls")
        y += lh
    if a.sub:
        y += sf.size * 0.3
        x = (W - d.textlength(a.sub, font=sf)) / 2
        sd.text((x, y + 3), a.sub, font=sf, fill=(0, 0, 0, 190), anchor="ls")
        d.text((x, y), a.sub, font=sf, fill=(255, 252, 245, 235), anchor="ls")
    if a.eyebrow:  # cream pill, dark brown small caps with letter spacing
        text = a.eyebrow.upper()
        gap = 5
        tw = sum(d.textlength(c, font=ef) for c in text) + gap * (len(text) - 1)
        px, py = (W - tw) / 2 - 34, top - 100
        d.rounded_rectangle((px, py - 30, px + tw + 68, py + 34), radius=32, fill=(248, 240, 226, 235))
        x = px + 34
        for c in text:
            d.text((x, py + 2), c, font=ef, fill=(74, 52, 36, 255), anchor="lm")
            x += d.textlength(c, font=ef) + gap
    layer = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)), layer)
    out = Image.alpha_composite(dark, layer).convert("RGB")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out, quality=92)
    print(f"THUMB {a.out} {Path(a.out).stat().st_size // 1024} KB scrim={alpha} lum={lum:.0f}")


if __name__ == "__main__":
    main()
