#!/usr/bin/env python3
"""Assemble ep1 parts 1+5 (16:9): scale clips to 1280x720, hard cuts, black title/end cards,
burned zh + pinyin + vi subtitles. Usage: assemble169.py CLIPDIR OUT.mp4   (clips CLIPDIR/<id>.mp4)"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
ZH = "/System/Library/Fonts/STHeiti Medium.ttc"
LAT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
ORDER = [
    ("p1-01", 8),
    ("p1-02", 6),
    ("p1-03", 8),
    ("p1-04", 5),
    ("p1-05", 5),
    ("card1", 3),
    ("p5-01", 8),
    ("p5-02", 8),
    ("p5-03", 6),
    ("p5-04", 6),
    ("p5-05", 5),
    ("card2", 3),
]
CARDS = {
    "card1": ("第一集 · 最后一碗面", "Dì-yī jí · Zuìhòu yì wǎn miàn", "Tập 1 · Bát mì cuối cùng"),
    "card2": ("下集:一张欠条", "Xià jí: Yì zhāng qiàntiáo", "Tập sau: Tờ giấy nợ"),
}
# (clip, start, end, zh, pinyin, vi) times inside the clip
CUES = [
    ("p1-02", 0.3, 1.6, "这是什么?", "Zhè shì shénme?", "Đây là cái gì?"),
    ("p1-02", 2.9, 4.6, "爸,是汤。", "Bà, shì tāng.", "Bố, là nước dùng ạ."),
    (
        "p1-02",
        4.8,
        6.0,
        "这不是我们的汤!",
        "Zhè bú shì wǒmen de tāng!",
        "Đây không phải nước dùng của nhà ta!",
    ),
    ("p1-03", 4.8, 7.1, "今天关门!", "Jīntiān guānmén!", "Hôm nay đóng cửa!"),
    ("p5-02", 5.1, 7.1, "对不起,周婉……", "Duìbuqǐ, Zhōu Wǎn…", "Xin lỗi, Chu Uyển…"),
    (
        "p5-04",
        1.9,
        4.9,
        "老先生,日子到了。",
        "Lǎo xiānsheng, rìzi dào le.",
        "Lão tiên sinh, đến ngày rồi.",
    ),
]


def font(p, s):
    return ImageFont.truetype(p, s)


def center(d, y, text, f, fill, stroke=0):
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


def sub_png(path, zh, py, vi):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    center(d, 500, zh, font(ZH, 46), (255, 255, 255), 4)
    center(d, 560, py, font(LAT, 28), (255, 214, 120), 3)
    center(d, 600, vi, font(LAT, 28), (255, 255, 255), 3)
    im.save(path)


def card_png(path, zh, py, vi):
    im = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    center(d, 270, zh, font(ZH, 64), (255, 255, 255))
    center(d, 370, py, font(LAT, 32), (255, 214, 120))
    center(d, 420, vi, font(LAT, 32), (255, 255, 255))
    im.save(path)


def run(a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-1500:])


def main(src, out):
    src, tmp = Path(src), Path(tempfile.mkdtemp())
    parts = []
    for cid, dur in ORDER:
        o = tmp / f"{cid}.mp4"
        if cid in CARDS:
            card_png(tmp / f"{cid}.png", *CARDS[cid])
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-t",
                    str(dur),
                    "-i",
                    str(tmp / f"{cid}.png"),
                    "-f",
                    "lavfi",
                    "-t",
                    str(dur),
                    "-i",
                    "anullsrc=r=48000:cl=stereo",
                    "-vf",
                    "fps=24,format=yuv420p",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(o),
                ]
            )
        else:
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(src / f"{cid}.mp4"),
                    "-vf",
                    f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=24,format=yuv420p",
                    "-af",
                    "aresample=48000,loudnorm=I=-18:TP=-2,aformat=channel_layouts=stereo",
                    "-ar",
                    "48000",
                    "-c:v",
                    "libx264",
                    "-crf",
                    "17",
                    "-c:a",
                    "aac",
                    str(o),
                ]
            )
        parts.append(o)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    joined = tmp / "joined.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
    starts, t = {}, 0.0
    for cid, dur in ORDER:
        starts[cid] = t
        t += dur
    ins, filt, last = ["-i", str(joined)], [], "0:v"
    for i, (cid, a, b, zh, py, vi) in enumerate(CUES, 1):
        sub_png(tmp / f"s{i}.png", zh, py, vi)
        ins += ["-i", str(tmp / f"s{i}.png")]
        filt.append(
            f"[{last}][{i}:v]overlay=enable='between(t,{starts[cid] + a:.2f},{starts[cid] + b:.2f})'[v{i}]"
        )
        last = f"v{i}"
    run(
        [
            "ffmpeg",
            "-y",
            *ins,
            "-filter_complex",
            ";".join(filt),
            "-map",
            f"[{last}]",
            "-map",
            "0:a",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            out,
        ]
    )
    print(out, round(t, 1), "s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
