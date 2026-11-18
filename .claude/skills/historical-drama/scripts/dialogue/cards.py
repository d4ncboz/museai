"""Usage: cards.py video.mp4 cards.json out.mp4
cards.json: [[word_start, show_until, zh, pinyin, vi], ...] -> one vocabulary card at a time,
upper-left (x10-44%, y16-~31%), highlighted (gold border + glow) for the first 0.6 s on its spoken word."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
X0, X1, Y0 = (
    357,
    724,
    70,
)  # TOP of the screen, centered (user: word cards while speaking go on top, not bottom)
ZH = "/System/Library/Fonts/STHeiti Medium.ttc"
LATIN = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
HIGHLIGHT = 0.6


def font(path, size, width, text):
    while size > 20:
        f = ImageFont.truetype(path, size, index=0)
        if f.getlength(text) <= width:
            return f
        size -= 2
    return f


def card(zh, py, vi, lit, dest):
    pad, inner = 26, X1 - X0 - 52
    rows = [
        (font(ZH, 104, inner, zh), zh, (25, 25, 35)),
        (font(LATIN, 48, inner, py), py, (190, 60, 70)),
        (font(LATIN, 42, inner, vi), vi, (55, 55, 70)),
    ]
    h = pad * 2 + sum(f.size * 1.15 for f, _, _ in rows) + 10
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    box = (X0, Y0, X1, Y0 + h)
    if lit:  # soft gold glow behind the card while its word is spoken
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle(box, 30, fill=(255, 200, 60, 200))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        box,
        28,
        fill=(255, 255, 255, 238),
        outline=(240, 180, 40, 255) if lit else (255, 255, 255, 0),
        width=7 if lit else 0,
    )
    y, cx = Y0 + pad, (X0 + X1) / 2
    for f, text, color in rows:
        d.text((cx, y + f.size * 0.575), text, font=f, anchor="mm", fill=color)
        y += f.size * 1.15 + 5
    img.save(dest)


def main():
    video, cards_path, out = sys.argv[1:4]
    cards = json.load(open(cards_path))
    tmp = Path(tempfile.mkdtemp())
    args, chain, prev, n = ["ffmpeg", "-v", "error", "-y", "-i", video], [], "0:v", 0
    for i, (s, e, *texts) in enumerate(cards):
        for lit, (a, b) in ((True, (s, min(e, s + HIGHLIGHT))), (False, (s + HIGHLIGHT, e))):
            if b <= a:
                continue
            png = tmp / f"k{i}{int(lit)}.png"
            card(*texts, lit, png)
            n += 1
            args += ["-i", str(png)]
            chain.append(f"[{prev}][{n}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{n}]")
            prev = f"v{n}"
    args += [
        "-filter_complex",
        ";".join(chain),
        "-map",
        f"[{prev}]",
        "-map",
        "0:a",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        out,
    ]
    subprocess.run(args, check=True)
    print("WROTE", out)


main()
