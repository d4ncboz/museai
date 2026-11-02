"""Usage: hook.py video.mp4 "<hook line>" out.mp4 [until=2.8]
  uv run --no-project --python 3.12 --with pillow --with opencv-python-headless==4.10.0.84 \\
      python scripts/hook.py final.mp4 "Đau răng ở Trung Quốc? Gọi nha sĩ thế nào?" hooked.mp4
Burns the scroll-stopping hook: the viewer's dilemma in their language, white on a red box in the top
band (x8-85 %, from y7 %, below the platform's top bar, down to just above the highest head), on screen from the first frame
until `until` s (end of the intro line), then fades out in 0.3 s. Shown on frame 0, so the first frame
a scroller sees already asks the question (user, EP44: "improve the hook at the beginning, so users
keep watching instead of scrolling past"). SUB="..." adds a small yellow open-loop line under it
(default "Cuối video có câu hỏi cho bạn!", SUB= to drop it; dropped by itself when the headroom is
short). Faces (opencv haar, every 0.25 s of the span, forehead added) set the box's lowest edge, and
the font shrinks to fit; with too little headroom it exits 1 with NO HEADROOM instead of covering her
head (EP44 intro: head top at y~300, 16 %): give the intro still headroom ("head top below 20 % of the
frame"), or shorten the line. Run after captions and cards, before qa's frame check."""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
X0, X1, Y0, Y1 = 86, 918, 134, 365  # x8-85 %, y7-19 % at most
GAP = 14  # px kept between the box and the highest head
LATIN = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
ZH = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
      ".asset/AssetData/PingFang.ttc")
CJK = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")
CJK_SPLIT = re.compile(r"([\u3000-\u9fff\uff00-\uffef]+)")
FADE = 0.3

video, text, out = sys.argv[1], sys.argv[2], sys.argv[3]
until = float(sys.argv[4]) if len(sys.argv) > 4 else 2.8
sub = os.environ.get("SUB", "Cuối video có câu hỏi cho bạn!")


class Mixed:
    """Arial with Hanzi runs in PingFang, so a hook like "Được khen 很地道 là khen gì?" has no tofu boxes."""

    def __init__(self, size):
        self.size = size
        self.latin = ImageFont.truetype(LATIN, size)
        self.zh = ImageFont.truetype(ZH, size, index=11)

    def runs(self, text):
        return [(self.zh if CJK.match(c) else self.latin, c) for c in CJK_SPLIT.split(text) if c]

    def getlength(self, text):
        return sum(f.getlength(c) for f, c in self.runs(text))

    def draw(self, d, xy, text, fill):
        x, y = xy
        for f, c in self.runs(text):
            d.text((x, y), c, font=f, fill=fill)
            x += f.getlength(c)


def wrap(f, words, width):
    """break after a ? or ! first when both halves fit ("Đau răng ở Trung Quốc? / Gọi nha sĩ thế nào?")"""
    for i, w in enumerate(words[:-1]):
        if w[-1] in "?!" and all(
            f.getlength(" ".join(p)) <= width for p in (words[: i + 1], words[i + 1 :])
        ):
            return [" ".join(words[: i + 1]), " ".join(words[i + 1 :])]
    lines, cur = [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if f.getlength(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    if len(lines) == 2:  # balance two lines: no lone "gì?" on the second one
        i = min(range(1, len(words)), key=lambda i: max(f.getlength(" ".join(p)) for p in (words[:i], words[i:])))
        lines = [" ".join(words[:i]), " ".join(words[i:])]
    return lines


def layout(y1, sub):
    """largest font (>= 44 px) that fits the text in at most 2 lines between Y0 and y1 (sub line included)"""
    inner = X1 - X0 - 60
    for size in range(78, 42, -2):
        f = Mixed(size)
        lines = wrap(f, text.split(), inner)
        fs = ImageFont.truetype(LATIN, max(30, int(size * 0.5)))
        h = len(lines) * size * 1.18 + 32 + (fs.size * 1.4 + 10 if sub else 0)
        if len(lines) <= 2 and all(f.getlength(x) <= inner for x in lines) and Y0 + h <= y1:
            return f, lines, fs, h
    return None


def head_tops():
    """[(t, head_top_y)] of faces under the hook's columns"""
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap, hits, t = cv2.VideoCapture(video), [], 0.0
    while t <= until:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(cv2.resize(fr, (W // 2, H // 2)), cv2.COLOR_BGR2GRAY)
        for x, y, w, h in cascade.detectMultiScale(gray, 1.1, 6, minSize=(60, 60)):
            fx0, fx1, fy0 = (
                x * 2,
                (x + w) * 2,
                y * 2 - h * 2 * 0.35,
            )  # haar box starts at the brows: add the forehead
            if fx1 > X0 and fx0 < X1:
                hits.append((t, int(fy0)))
        t += 0.25
    return hits


tops = head_tops()
y1 = min([Y1] + [y - GAP for _, y in tops])
fit = layout(y1, sub)
if not fit and sub:
    fit, sub = layout(y1, ""), ""
    print("sub line dropped: short headroom")
if not fit:
    t, y = min(tops, key=lambda x: x[1])
    sys.exit(
        f"NO HEADROOM: head top y={y} at {t:.2f}s leaves {y1 - Y0} px for '{text}'; "
        "give the intro headroom or cut the line to ~6 words"
    )
f, lines, fs, h = fit
bottom = Y0 + h

img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
box_w = max(f.getlength(x) for x in lines) + 60
cx = (X0 + X1) / 2
bx0 = cx - box_w / 2
main_h = len(lines) * f.size * 1.18 + 32
d.rounded_rectangle((bx0, Y0, bx0 + box_w, Y0 + main_h), 22, fill=(214, 32, 48, 240))
y = Y0 + 16
for line in lines:
    f.draw(d, (cx - f.getlength(line) / 2, y), line, "white")
    y += f.size * 1.18
if sub:
    y = Y0 + main_h + 10
    d.text(
        (cx - fs.getlength(sub) / 2, y),
        sub,
        font=fs,
        fill=(255, 214, 10),
        stroke_width=4,
        stroke_fill="black",
    )
with tempfile.TemporaryDirectory() as tmp:
    png = Path(tmp) / "hook.png"
    img.save(png)
    vf = (
        f"[1:v]format=rgba,fade=t=out:st={until - FADE:.2f}:d={FADE}:alpha=1[h];"
        f"[0:v][h]overlay=0:0:enable='lte(t,{until:.2f})'[v]"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            video,
            "-loop",
            "1",
            "-t",
            f"{until:.2f}",
            "-i",
            str(png),
            "-filter_complex",
            vf,
            "-map",
            "[v]",
            "-map",
            "0:a",
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            out,
        ],
        check=True,
    )
print(
    f"WROTE {out}  hook 0-{until:.2f}s, {len(lines)} line(s) {f.size}px, box bottom y={bottom:.0f}"
)
