"""No-text 9:16 cover for a dream-life reel: the reel's most striking frame, graded to pop.

User rule 2026-11-03: no text on the cover. The picture alone has to make a viewer curious, so the
script samples the reel at 4 fps and scores every frame on what the Instagram profile grid shows
(the 3:4 crop, y 240-1680 of 1080x1920): sharpness (drops dissolves and motion blur), colour,
contrast, a subject that stands out from its surroundings, and sane exposure. The best frame gets a
punchier grade than the video, a soft glow and a vignette that pulls the eye to the centre.

Usage:
  uv run --no-project --python 3.12 --with pillow --with numpy python scripts/cover.py \
      --video dream-<slug>.mp4 --out thumbs/dream-<slug>_9x16.jpg [--at 7.25] [--grid grid.jpg] \
      [--sheet picks.jpg] [--pick 2]
--at skips the search and uses that second. --sheet writes the top 4 picks side by side (1-4) to
choose by eye; --pick N then uses pick N (the score cannot see which frame shows the magic: prefer
the one where the impossible thing is big and clear). --grid writes the 3:4 crop the profile grid will show.
"""

import argparse
import subprocess
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

W, H = 1080, 1920
GRID = (0, 240, W, 1680)
FPS = 4
SW, SH = 270, 480  # scoring size


def duration(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout)


def samples(video):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={FPS},scale={SW}:{SH}"]
        + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, SH, SW, 3).astype(np.float32) / 255


def scores(frames, length):
    g = frames[:, SH * 240 // H : SH * 1680 // H]  # what the grid shows
    luma = g @ np.float32([0.299, 0.587, 0.114])
    lap = luma[:, 1:-1, 1:-1] * 4 - luma[:, :-2, 1:-1] - luma[:, 2:, 1:-1]
    lap -= luma[:, 1:-1, :-2] + luma[:, 1:-1, 2:]
    sharp = lap.var(axis=(1, 2))
    rg, yb = g[..., 0] - g[..., 1], (g[..., 0] + g[..., 1]) / 2 - g[..., 2]
    colour = np.hypot(rg.std(axis=(1, 2)), yb.std(axis=(1, 2)))
    colour += 0.3 * np.hypot(rg.mean(axis=(1, 2)), yb.mean(axis=(1, 2)))
    contrast = luma.std(axis=(1, 2))
    h, w = luma.shape[1:]
    centre = g[:, h // 4 : h * 3 // 4, w // 5 : w * 4 // 5].mean(axis=(1, 2))
    pop = np.linalg.norm(centre - g.mean(axis=(1, 2)), axis=1)  # subject vs surroundings
    mean = luma.mean(axis=(1, 2))
    clipped = ((luma < 0.03) | (luma > 0.97)).mean(axis=(1, 2))
    exposure = np.clip(1 - np.abs(mean - 0.5) * 1.6, 0, 1) * (1 - clipped)

    def rank(x):  # 0..1 within this reel, so one outlier frame does not flatten the rest
        return x.argsort().argsort() / max(len(x) - 1, 1)

    s = rank(sharp) ** 1.5 * (rank(colour) + rank(contrast) + 0.6 * rank(pop)) * exposure
    t = np.arange(len(s)) / FPS
    s[(t < 0.5) | (t > length - 0.7)] = 0  # fade in / out
    return s


def frame(video, t):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1"]
        + ["-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True,
        check=True,
    ).stdout

    img = Image.open(BytesIO(raw)).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def grade(img):
    # a cover competes with a whole grid of thumbnails: richer than the video, still dreamy
    img = ImageEnhance.Color(img).enhance(1.25)
    img = ImageEnhance.Contrast(img).enhance(1.10)
    glow = img.filter(ImageFilter.GaussianBlur(28))
    img = Image.blend(img, Image.fromarray(np.maximum(np.asarray(img), np.asarray(glow))), 0.22)
    y, x = np.ogrid[:H, :W]
    r = np.hypot((x - W / 2) / (W / 2), (y - H * 0.48) / (H / 2))
    vig = 1 - 0.28 * np.clip(r - 0.45, 0, 1) ** 1.6
    img = Image.fromarray((np.asarray(img) * vig[..., None]).clip(0, 255).astype(np.uint8))
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))


def picks(s, n=4, gap=2.5):
    out = []
    for i in np.argsort(-s):
        if s[i] <= 0 or len(out) == n:
            break
        if all(abs(i - j) / FPS >= gap for j in out):
            out.append(i)
    return [i / FPS for i in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--at", type=float, help="use this second instead of searching")
    ap.add_argument("--grid", help="also write the 3:4 grid crop here")
    ap.add_argument("--sheet", help="also write the top 4 picks side by side here")
    ap.add_argument("--pick", type=int, default=1, help="use the Nth pick of the sheet")
    a = ap.parse_args()

    best = [a.at]
    if a.at is None:
        best = picks(scores(samples(a.video), duration(a.video)))
    t = best[min(a.pick, len(best)) - 1]
    img = grade(frame(a.video, t))
    img.save(a.out, quality=93)
    if a.grid:
        img.crop(GRID).save(a.grid, quality=90)
    if a.sheet:
        sheet = Image.new("RGB", (len(best) * 360, 640), "white")
        for k, b in enumerate(best):
            sheet.paste(grade(frame(a.video, b)).resize((360, 640)), (k * 360, 0))
            ImageDraw.Draw(sheet).text((k * 360 + 12, 12), f"{k + 1}  ({b:.2f}s)", fill="white")
        sheet.save(a.sheet, quality=85)
    print(f"{a.out}  frame at {t:.2f}s (picks: {', '.join(f'{b:.2f}' for b in best)})")


if __name__ == "__main__":
    main()
