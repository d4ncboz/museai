"""Catchy 9:16 cover for a dream-life reel, built for the Instagram profile grid.

The grid shows every Reel cover cropped to 3:4 (since 2025-01): 240 px go off the top and the
bottom of a 1080x1920 cover. Everything here sits inside x 60-1020, y 300-1620, so the grid, the
Reels tab and TikTok all show it whole. The hook is the only text: 3-7 big rounded words, white
with a dark plum outline (reads on pale skies and on dark nights), one word in the look's accent
colour, a "pov:" prefix on its own small line, and a small series pill above ("dream life no. 3")
so a viewer who lands on one cover binges the rest.

Usage:
  python3 scripts/cover.py --idea idea.json --at s3.mp4@2.0 --out thumbs/dream-<slug>_9x16.jpg \
      [--hook "pov: you fish *fallen stars* out of the lake"] [--no N] [--place top|bottom] [--grid grid.jpg]
*words* pick the accent (default: the last word). --no defaults to the next history number.
--grid writes the 3:4 crop the profile grid will show, to check before delivery.
"""

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

SKILL = Path(__file__).resolve().parent.parent
HIST = Path.home() / ".config/museai/dream-history.json"
FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
W, H = 1080, 1920
SAFE = (60, 300, 1020, 1620)  # inside the 3:4 grid crop (y 240-1680) with a margin
INK = (44, 26, 58)  # outline / shadow / pill text


def frame(at):
    clip, _, t = at.partition("@")
    png = Path(tempfile.mkdtemp()) / "f.png"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", t or "2", "-i", clip, "-frames:v", "1", str(png)],
        check=True,
    )
    img = Image.open(png).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((x, y, x + W, y + H))
    # punchier than the video: a cover competes with a whole grid of thumbnails
    img = ImageEnhance.Color(img).enhance(1.18)
    img = ImageEnhance.Contrast(img).enhance(1.07)
    img = ImageEnhance.Brightness(img).enhance(1.03)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))


def words_of(hook):
    """[(word, accent?)]; *a b* marks the accent words, else the last word is the accent."""
    out = []
    for part in re.split(r"(\*[^*]+\*)", hook):
        accent = part.startswith("*")
        out += [(w, accent) for w in part.strip("*").split()]
    if not any(a for _, a in out):
        out[-1] = (out[-1][0], True)
    return out


def wrap(d, words, font, max_w):
    rows, cur = [], []
    for w in words:
        t = " ".join(x for x, _ in cur + [w])
        if cur and d.textlength(t, font=font) > max_w:
            rows.append(cur)
            cur = [w]
        else:
            cur.append(w)
    return rows + [cur]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idea", required=True)
    ap.add_argument(
        "--at", required=True, help="clip.mp4@seconds: the brightest frame with the lead"
    )
    ap.add_argument("--out", required=True)
    ap.add_argument("--hook", help="default: the idea's hook")
    ap.add_argument("--no", type=int, help="series number (default: next in the history)")
    ap.add_argument(
        "--place", default="top", help="top | bottom (keep the text off the face) | a fraction of H"
    )
    ap.add_argument("--grid", help="also write the 3:4 grid crop here")
    a = ap.parse_args()

    idea = json.loads(Path(a.idea).read_text())
    look = json.loads((SKILL / "looks.json").read_text())[idea["look"]]
    accent = tuple(int(look["accent"][i : i + 2], 16) for i in (1, 3, 5))
    hook = a.hook or idea["hook"]
    pov = re.match(r"\s*pov:\s*", hook, re.I)
    words = words_of(hook[pov.end() :] if pov else hook)
    no = a.no or len(json.loads(HIST.read_text()) if HIST.exists() else []) + 1

    img = frame(a.at).convert("RGBA")
    d = ImageDraw.Draw(img)
    max_w = SAFE[2] - SAFE[0] - 40
    size = 150
    while True:  # biggest size that keeps the hook to 2 rows (3 for a long hook)
        font = ImageFont.truetype(FONT, size)
        rows = wrap(d, words, font, max_w)
        if len(rows) <= 2 or size <= 96 and len(rows) <= 3:
            break
        size -= 6
    small = ImageFont.truetype(FONT, int(size * 0.5))
    pill = ImageFont.truetype(FONT, 40)

    block = 72 + 34 + (small.size * 1.15 if pov else 0) + len(rows) * font.size * 1.12
    y = {"top": SAFE[1] + 20, "bottom": SAFE[3] - 20 - block}.get(a.place) or H * float(a.place)
    lines = []  # (y, [(text, colour)], font)
    tag = f"dream life  no. {no}"
    tw = d.textlength(tag, font=pill)
    pill_box = ((W - tw) / 2 - 30, y, (W + tw) / 2 + 30, y + 72)
    y += 72 + 34
    if pov:
        lines.append((y, [("pov:", accent)], small))
        y += small.size * 1.15
    for r in rows:
        lines.append((y, [(w, accent if acc else (255, 253, 248)) for w, acc in r], font))
        y += font.size * 1.12
    assert SAFE[1] <= pill_box[1] and y <= SAFE[3], (
        f"text block {pill_box[1]:.0f}-{y:.0f} leaves the grid-safe box"
    )

    # soft shadow, then outlined words
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(pill_box, radius=36, fill=(*INK, 120))
    for ly, parts, f in lines:
        x = (W - d.textlength(" ".join(t for t, _ in parts), font=f)) / 2
        sd.text(
            (x, ly + 8),
            " ".join(t for t, _ in parts),
            font=f,
            fill=(*INK, 200),
            stroke_width=12,
            stroke_fill=(*INK, 200),
        )
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(pill_box, radius=36, fill=(255, 253, 248, 235))
    d.text((W / 2, pill_box[1] + 36), tag, font=pill, fill=INK, anchor="mm")
    for ly, parts, f in lines:
        x = (W - d.textlength(" ".join(t for t, _ in parts), font=f)) / 2
        for t, col in parts:
            d.text((x, ly), t, font=f, fill=col, stroke_width=max(6, f.size // 16), stroke_fill=INK)
            x += d.textlength(t + " ", font=f)

    out = img.convert("RGB")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out, quality=93)
    if a.grid:
        out.crop((0, 240, W, 1680)).save(a.grid, quality=90)
    print(
        f"{a.out}  no. {no}, {len(rows)} rows at {size}px, text y {pill_box[1]:.0f}-{y:.0f} (grid-safe)"
    )


if __name__ == "__main__":
    main()
