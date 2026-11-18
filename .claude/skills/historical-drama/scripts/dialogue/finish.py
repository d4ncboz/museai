"""finish.py spec.json  -> body + recap/quiz tail, captions, cards, quiz card, hook.
spec: {"dir", "body", "cues", "cards": [[start, until, zh, py, vi]], "recap": [[src_s, src_e, zh, py, vi]],
       "quiz": [title, line1, line2, ...], "teaser", "hook", "reveal", "hook_until", "out"}"""

import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

T = Path(__file__).parent
ZH = "/System/Library/Fonts/STHeiti Medium.ttc"
LAT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
sp = json.load(open(sys.argv[1]))
D = Path(sp["dir"])
os.chdir(D)


def run(c, **kw):
    subprocess.run(c, check=True, **kw)


def dur(f):
    return float(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]
        )
    )


body = sp["body"]
L = dur(body)
# tail: last frame, slow push-in; recap words (their own dubbed audio) then quiz + teaser
rec = sp["recap"]
STEP = 1.9
R0 = 0.5
qz0 = R0 + STEP * len(rec) + 0.2
QA = sp.get("qaudio")
QD = dur(QA) if QA else 0
TL = qz0 + max(4.6, QD + 2.5)
run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.05", "-i", body, "-frames:v", "1", "last.png"])
run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-loop",
        "1",
        "-i",
        "last.png",
        "-t",
        f"{TL}",
        "-vf",
        "scale=1080:1920,gblur=sigma=28,eq=brightness=-0.22:saturation=0.8,fps=24,format=yuv420p",
        "-c:v",
        "libx264",
        "-crf",
        "16",
        "tailv.mp4",
    ]
)
if not sp.get("music"):
    run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "recap_bed.py"),
            f"{TL}",
            "bed.wav",
        ],
        env={**os.environ, "MUSE_SKILL_DEV": "1"},
    )
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

SR = 48000


def load(args):
    r = subprocess.run(
        ["ffmpeg", "-v", "error", *args, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2)


mix = np.zeros((int(TL * SR), 2), np.float32)


def put(x, t, g):
    i = int(t * SR)
    n = min(len(x), len(mix) - i)
    if n > 0:
        mix[i : i + n] += x[:n] * g


MUS = sp.get("music")
if MUS:
    m = load(["-stream_loop", "-1", "-i", MUS, "-t", f"{L + TL:.2f}"])
    m = m.copy()
    fo = int(2.0 * SR)
    m[-fo:] *= np.linspace(1, 0, fo)[:, None]
    put(m[int(L * SR) :], 0, 0.55)
    body_music = m[: int(L * SR)]
else:
    put(load(["-i", "bed.wav"]), 0, 0.4)
    body_music = None
RA = sp.get("recap_audio")
for i, (s_, e_, *_) in enumerate(rec):
    x = (
        load(["-i", RA[i]]) if RA else load(["-ss", f"{s_}", "-t", f"{e_ - s_:.2f}", "-i", body])
    ).copy()
    f = int(0.04 * SR)
    x[:f] *= np.linspace(0, 1, f)[:, None]
    x[-f:] *= np.linspace(1, 0, f)[:, None]
    put(x, R0 + STEP * i + (0.25 if RA else 0), 1.3)
if QA:
    put(load(["-i", QA]), qz0, 1.4)
pk = np.abs(mix).max()
if pk > 0.95:
    mix *= 0.95 / pk
sf.write("taila.wav", mix, SR)
run(["ffmpeg", "-v", "error", "-y", "-i", "taila.wav", "-c:a", "aac", "-ar", "48000", "taila.m4a"])
run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        "tailv.mp4",
        "-i",
        "taila.m4a",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        "tail.mp4",
    ]
)
if body_music is not None:
    bx = load(["-i", body]).copy()
    n = min(len(bx), len(body_music))
    g = np.full(n, 0.22, np.float32)
    fi = int(1.0 * SR)
    g[:fi] = np.linspace(0, 0.22, fi)
    bx[:n] += body_music[:n] * g[:, None] * 0.55
    pk = np.abs(bx).max()
    bx *= (0.95 / pk) if pk > 0.95 else 1
    sf.write("bodyA.wav", bx, SR)
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            body,
            "-i",
            "bodyA.wav",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-r",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "body24.mp4",
        ]
    )
else:
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            body,
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-r",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "body24.mp4",
        ]
    )
Path("cat.txt").write_text("file 'body24.mp4'\nfile 'tail.mp4'\n")
run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        "cat.txt",
        "-c:v",
        "libx264",
        "-crf",
        "16",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "joined.mp4",
    ]
)

# captions: dialogue cues + one per recap word
cues = json.load(open(sp["cues"]))
cues = [c[:5] for c in cues]
recap_cues, recap_cards = [], []
for i, (_s, _e, zh, py, vi) in enumerate(rec):
    t0 = L + R0 + STEP * i
    recap_cues.append([round(t0, 2), round(t0 + STEP - 0.15, 2), zh, py, vi])
    recap_cards.append([round(t0 - 0.1, 2), round(t0 + STEP - 0.2, 2), zh, py, vi])
json.dump(cues, open("allcues.json", "w"), ensure_ascii=False)
json.dump(sp["cards"], open("allcards.json", "w"), ensure_ascii=False)
uvp = [
    "uv",
    "run",
    "-q",
    "--no-project",
    "--python",
    "3.12",
    "--with",
    "pillow",
    "--with",
    "opencv-python-headless==4.10.0.84",
    "python",
]
run(uvp + [str(T / "burn_subs.py"), "joined.mp4", "allcues.json", "subs.mp4"])
run(uvp + [str(T / "cards.py"), "subs.mp4", "allcards.json", "carded.mp4"])


# "Ôn lại" banner over recap + quiz card + teaser
def font(p, s):
    return ImageFont.truetype(p, s, index=0)


def panel(lines, path, y0):
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hs = []
    for txt, sz, col in lines:
        f = font(ZH if any("一" <= ch <= "鿿" for ch in txt) else LAT, sz)
        while d.textlength(txt, font=f) > 900 and sz > 30:
            sz -= 2
            f = font(ZH if any("一" <= ch <= "鿿" for ch in txt) else LAT, sz)
        hs.append((txt, f, col, sz))
    h = sum(int(x[3] * 1.35) for x in hs) + 60
    d.rounded_rectangle(
        (70, y0, 1010, y0 + h), 36, fill=(12, 12, 16, 215), outline=(240, 196, 80, 255), width=5
    )
    y = y0 + 30
    for txt, f, col, sz in hs:
        w = d.textlength(txt, font=f)
        d.text(((1080 - w) / 2, y), txt, font=f, fill=col)
        y += int(sz * 1.35)
    im.save(path)


GOLD, WHITE, YEL = (240, 196, 80, 255), (255, 255, 255, 255), (255, 230, 120, 255)
panel([("ÔN LẠI 3 TỪ", 58, GOLD)], "p_recap.png", 330)
q = sp["quiz"]
panel(
    [(q[0], 54, GOLD)]
    + [
        (
            x,
            (62 if i == 0 else 58)
            if any("\u4e00" <= ch <= "\u9fff" for ch in x)
            else (56 if i == 0 else 48),
            WHITE,
        )
        for i, x in enumerate(q[1:])
    ]
    + [("Comment đáp án nhé!", 40, YEL)],
    "p_quiz.png",
    560,
)
panel([(sp["teaser"], 46, YEL)], "p_teaser.png", 1500)
tq = L + qz0


def wordpanel(zh, py, vi, path):
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rows = [
        (zh, font(ZH, 190), (255, 255, 255, 255)),
        (py, font(LAT, 82), (120, 190, 255, 255)),
        (vi, font(LAT, 78), (255, 255, 255, 255)),
    ]
    hs = [int(f.size * 1.3) for _, f, _ in rows]
    y = (1920 - sum(hs)) // 2 + 40
    for (t, f, c), h in zip(rows, hs, strict=False):
        w = d.textlength(t, font=f)
        d.text(((1080 - w) / 2, y), t, font=f, fill=c, stroke_width=7, stroke_fill=(0, 0, 0, 255))
        y += h
    im.save(path)


wp = []
for i, (_s, _e, zh, py, vi) in enumerate(rec):
    wordpanel(zh, py, vi, f"wp{i}.png")
    wp.append((L + R0 + STEP * i - 0.1, L + R0 + STEP * (i + 1) - 0.25))
nw = len(rec)
wins = "".join(f"[w{i}]" for i in range(0))
fcw = ""
last = "[0:v]"
for i, (a_, b_) in enumerate(wp):
    fcw += f"{last}[{4 + i}:v]overlay=enable='between(t,{a_:.2f},{b_:.2f})'[ww{i}];"
    last = f"[ww{i}]"
run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        "carded.mp4",
        "-i",
        "p_recap.png",
        "-i",
        "p_quiz.png",
        "-i",
        "p_teaser.png",
        *sum([["-i", f"wp{i}.png"] for i in range(nw)], []),
        "-filter_complex",
        fcw + f"{last}[1:v]overlay=enable='between(t,{L + 0.1:.2f},{tq - 0.1:.2f})'[a];"
        f"[a][2:v]overlay=enable='gte(t,{tq:.2f})'[b];[b][3:v]overlay=enable='gte(t,{tq + max(2.2, QD + 0.3):.2f})'[v]",
        "-map",
        "[v]",
        "-map",
        "0:a",
        "-c:v",
        "libx264",
        "-crf",
        "17",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "panel.mp4",
    ]
)
env = {**os.environ, "REVEAL": str(sp["reveal"])}
run(uvp + [str(T / "hook.py"), "panel.mp4", sp["hook"], sp["out"], str(sp["hook_until"])], env=env)
print("OUT", sp["out"], dur(sp["out"]))
