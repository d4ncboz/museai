"""Assemble a dream-life reel: 6 calm shots joined by soft dissolves, the look's grade, the dream
track over the clips' own soft ambience.

Usage:
  python3 scripts/compose.py --idea idea.json --music track.m4a --out dream-<slug>.mp4 s1.mp4 s2.mp4@1.5 ...
  [--shot 4.6] [--xfade 0.5] [--text none|hook|alt|"custom line"] [--text-secs 3.5] [--ambience 0.25]

Measured on the references (720x1280, 25-48 s, -14 LUFS): one shot every 4.3-5 s, 6-10 shots, soft
cuts, no on-screen text, music carries the reel. clip@start picks where the window starts (default
0.8 s: muse's first second often settles). No text on the video (user rule 2026-11-01): the hook
goes on the thumbnail and in the captions. --text hook draws it for the first --text-secs only if
the user asks for it on a video.
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SKILL = Path(__file__).resolve().parent.parent
LNORM = SKILL.parent / "healing-video/scripts/lnorm.py"
FONT = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"

ap = argparse.ArgumentParser()
ap.add_argument("clips", nargs="+", help="shot.mp4 or shot.mp4@start_seconds, in order")
ap.add_argument("--idea", required=True)
ap.add_argument("--music", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--shot", type=float, default=4.6, help="seconds each shot is on screen")
ap.add_argument("--xfade", type=float, default=0.5, help="dissolve between shots (0 = hard cut)")
ap.add_argument("--text", default="none", help="none | hook | alt | a custom line")
ap.add_argument("--text-secs", type=float, default=3.5)
ap.add_argument("--ambience", type=float, default=0.25, help="clip ambience level under the music")
ap.add_argument("--size", default="1080x1920")
a = ap.parse_args()

idea = json.loads(Path(a.idea).read_text())
look = json.loads((SKILL / "looks.json").read_text())[idea["look"]]
W, H = map(int, a.size.split("x"))
n = len(a.clips)
total = n * a.shot - (n - 1) * a.xfade
text = {"hook": idea.get("hook"), "alt": idea.get("caption_alt"), "none": None}.get(a.text, a.text)


def text_png(line, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    font = ImageFont.truetype(FONT, int(W * 0.062))
    d = ImageDraw.Draw(img)
    words, rows, cur = line.split(), [], ""
    for w in words:  # wrap to ~80 % of the width
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=font) > W * 0.8 and cur:
            rows.append(cur)
            cur = w
        else:
            cur = t
    rows.append(cur)
    y = int(H * 0.15)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for i, r in enumerate(rows):
        x = (W - d.textlength(r, font=font)) / 2
        yy = y + i * int(font.size * 1.3)
        sd.text(
            (x, yy + 2),
            r,
            font=font,
            fill=(40, 30, 50, 230),
            stroke_width=4,
            stroke_fill=(40, 30, 50, 230),
        )
        d.text((x, yy), r, font=font, fill=(255, 252, 245, 255))
    Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)), img).save(path)


with tempfile.TemporaryDirectory() as tmp:
    inputs, chains = [], []
    for i, c in enumerate(a.clips):
        path, _, start = c.partition("@")
        inputs += ["-ss", start or "0.8", "-t", f"{a.shot}", "-i", path]
        chains.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,"
            f"{look['grade']},setsar=1,format=yuv420p[v{i}]"
        )
        has_audio = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                path,
            ],
            capture_output=True,
            text=True,
        ).stdout.strip()
        src = f"[{i}:a]aresample=48000" if has_audio else f"aevalsrc=0:s=48000:d={a.shot}"
        chains.append(
            f"{src},aformat=channel_layouts=stereo,volume={a.ambience},afade=in:d=0.3,afade=out:st={a.shot - 0.4}:d=0.4[a{i}]"
        )
    # video: chain xfades; audio: crossfade the ambience the same way
    v, au, off = "[v0]", "[a0]", 0.0
    for i in range(1, n):
        off += a.shot - a.xfade
        if a.xfade > 0:
            chains.append(
                f"{v}[v{i}]xfade=transition=fade:duration={a.xfade}:offset={off:.3f}[vx{i}]"
            )
            chains.append(f"{au}[a{i}]acrossfade=d={a.xfade}[ax{i}]")
        else:
            chains.append(f"{v}[v{i}]concat=n=2:v=1:a=0[vx{i}]")
            chains.append(f"{au}[a{i}]concat=n=2:v=0:a=1[ax{i}]")
        v, au = f"[vx{i}]", f"[ax{i}]"
    music_in = len(a.clips)
    inputs += ["-i", a.music]
    # light film grain + soft fade in/out, loop-friendly ending
    chains.append(f"{v}noise=alls=4:allf=t,fade=in:d=0.3,fade=out:st={total - 0.6:.2f}:d=0.6[vg]")
    vout = "[vg]"
    if text:
        png = Path(tmp) / "text.png"
        text_png(text, png)
        inputs += ["-loop", "1", "-t", f"{total}", "-i", str(png)]
        chains.append(
            f"[{music_in + 1}:v]format=rgba,fade=in:d=0.4:alpha=1,"
            f"fade=out:st={a.text_secs - 0.5}:d=0.5:alpha=1[t]"
        )
        chains.append(f"{vout}[t]overlay=0:0:enable='lte(t,{a.text_secs})'[vt]")
        vout = "[vt]"
    chains.append(f"[{music_in}:a]atrim=duration={total:.2f},afade=out:st={total - 2:.2f}:d=2[m]")
    # steep roll-off above 5.5 kHz like the references' vintage top end: muse ambience hiss and the
    # track's 6-7 kHz edge failed qa.py's noise floor (< -70 dB above 7 kHz) on dl-0005/0006
    hiss_cut = ",".join(["lowpass=f=5500"] * 6)
    chains.append(f"[m]{au}amix=inputs=2:duration=first:normalize=0,{hiss_cut}[mix]")
    mixed = Path(tmp) / "mix.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            *inputs,
            "-filter_complex",
            ";".join(chains),
            "-map",
            vout,
            "-map",
            "[mix]",
            "-t",
            f"{total:.2f}",
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-preset",
            "medium",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "48000",
            str(mixed.with_suffix(".mov")),
        ],
        check=True,
    )
    # one fixed gain to -14 LUFS like the references (two-pass, no pumping)
    audio = Path(tmp) / "mix.m4a"
    subprocess.run(
        ["python3", str(LNORM), str(mixed.with_suffix(".mov")), str(audio), "-14"], check=True
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(mixed.with_suffix(".mov")),
            "-i",
            str(audio),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            a.out,
        ],
        check=True,
    )
print(f"{a.out}  {total:.1f} s, {n} shots, look {idea['look']}, text: {text or 'none'}")
