"""shotcut.py V  -> jinxiu-V/w/sp.mp4 + cues.json(+.spk) from single-person shot clips (cut between speakers).
order: line index -> (clip, k-th line of that clip). Needs jinxiu-V/w/cues.json (zh,py,vi per line; times replaced)."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

V = sys.argv[1]
D = Path.home() / "Movies/museai"
W = D / f"jinxiu-{V}/w"
W.mkdir(exist_ok=True)
ORD = {
    "01": [
        ("sW1", 0),
        ("sM1", 0),
        ("sW1", 1),
        ("sW1b", 0),
        ("sM1", 1),
        ("sW1b", 1),
        ("sM1", 2),
        ("sW2", 0),
        ("sM2", 0),
        ("sW2", 1),
        ("sM2", 1),
        ("sW2", 2),
    ],
    "02": [
        ("sL1", 0),
        ("sQ1", 0),
        ("sL1", 1),
        ("sQ1", 1),
        ("sL1", 2),
        ("sQ1", 2),
        ("sL2", 0),
        ("sQ2", 0),
        ("sL2", 1),
        ("sQ2", 1),
        ("sL2", 2),
        ("sQ2", 2),
    ],
}[V]
SPK = {"01": "WMWWMWMWMWMW", "02": "LMLMLMLMLMLM"}[V]
base = json.load(open(W / "cues.base.json")) if (W / "cues.base.json").exists() else None
if base is None:
    base = json.load(open(W / "cues.json"))
    json.dump(base, open(W / "cues.base.json", "w"), ensure_ascii=False)
clips = sorted({c for c, _ in ORD})
words = {}
for c in clips:
    f = D / f"jinxiu-{V}-{c}.mp4"
    out = W / f"{c}.words.json"
    if not out.exists():
        subprocess.run(
            [
                "uv",
                "run",
                "-q",
                "--no-project",
                "--python",
                "3.12",
                "--with",
                "faster-whisper",
                "--with",
                "opencc-python-reimplemented",
                "python",
                str(D / "jinxiu-tools/transcribe.py"),
                str(f),
                str(out),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    words[c] = json.load(open(out))


def chars(ws):
    r = []
    for w in ws:
        t = re.sub(r"[^一-鿿]", "", w["w"])
        n = len(t)
        for i in range(n):
            r.append((w["s"] + (w["e"] - w["s"]) * i / n, w["s"] + (w["e"] - w["s"]) * (i + 1) / n))
    return r


span = {}  # (clip,k) -> (s,e)
for c in clips:
    lines = [
        ln.split(": ", 1)[1].strip()
        for ln in (D / f"jinxiu-{V}/{c}.script").read_text().splitlines()
    ]
    ch = chars(words[c])
    exp = [len(re.sub(r"[^一-鿿]", "", ln.replace("嗯", ""))) for ln in lines]
    print(c, "heard", len(ch), "expected", sum(exp))
    k = 0
    for i, n in enumerate(exp):
        seg = ch[k : k + n]
        k += n
        span[(c, i)] = (seg[0][0], seg[-1][1]) if seg else (0, 0.5)
OV = W / "spans.override.json"
ov = json.load(open(OV)) if OV.exists() else {}
for c, lst in ov.items():
    for i, sp in enumerate(lst):
        if sp:
            span[(c, i)] = tuple(sp[:2]) + (tuple(sp[2:4]) if len(sp) > 2 else ())
import numpy as np  # noqa: E402


def env(c):
    f = D / f"jinxiu-{V}-{c}.mp4"
    r = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(f),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "f32le",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    x = np.frombuffer(r.stdout, np.float32)
    n = len(x) // 160
    return np.sqrt((x[: n * 160].reshape(n, 160) ** 2).mean(1))  # 10 ms rms


ENV = {c: env(c) for c in clips}


def real_end(c, e, nxt):
    v = ENV[c]
    thr = 0.12 * np.percentile(v, 95)
    i = int(e * 100)
    j = i
    while (
        j < min(len(v) - 12, int((nxt - 0.1) * 100) if nxt else len(v) - 12, int((e + 0.6) * 100))
        and (v[j : j + 12] > thr).any()
    ):
        j += 1  # until 120 ms of quiet
    return max(e, j / 100)


def real_start(c, s, prv):
    v = ENV[c]
    thr = 0.12 * np.percentile(v, 95)
    i = int(s * 100)
    lo = int(max(prv, s - 0.6) * 100)
    j = i
    while j > lo and v[j - 1] > thr:
        j -= 1  # walk back while still voiced
    return j / 100


NXT = {}
PRV = {}
for c in clips:
    ks = sorted(k for (cc, k) in span if cc == c)
    for a_, b_ in zip(ks, ks[1:], strict=False):
        NXT[(c, a_)] = span[(c, b_)][0]
        PRV[(c, b_)] = span[(c, a_)][1]
XF = float(__import__("os").environ.get("XF", 0.22))
durs = []
parts = []
cues = []
t = 0.0
for i, (c, k) in enumerate(ORD):
    sp_ = span[(c, k)]
    s, e = sp_[0], sp_[1]
    gap = sp_[2:4]
    s2 = real_start(c, s, PRV.get((c, k), 0))
    e2 = real_end(c, e, NXT.get((c, k)))
    a = max(0, s2 - 0.10)
    b = e2 + 0.22
    if not gap:
        s_, e_ = s, e
    p = W / f"cut{i:02d}.mp4"
    src = str(D / f"jinxiu-{V}-{c}.mp4")
    if gap:  # drop the dead air inside the line (video + audio)
        g0, g1 = gap
        fc = (
            f"[0:v]split[v1][v2];[v1]trim={a}:{g0},setpts=PTS-STARTPTS[x1];[v2]trim={g1}:{b},setpts=PTS-STARTPTS[x2];[x1][x2]concat=n=2:v=1,scale=1080:1920:flags=lanczos,fps=24[v];"
            f"[0:a]asplit[a1][a2];[a1]atrim={a}:{g0},asetpts=PTS-STARTPTS[y1];[a2]atrim={g1}:{b},asetpts=PTS-STARTPTS[y2];[y1][y2]concat=n=2:v=0:a=1[a]"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                src,
                "-filter_complex",
                fc,
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-crf",
                "16",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(p),
            ],
            check=True,
        )
        cut = g1 - g0
        e -= cut
        b -= cut
    else:
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                f"{a:.2f}",
                "-to",
                f"{b:.2f}",
                "-i",
                src,
                "-vf",
                "scale=1080:1920:flags=lanczos,fps=24",
                "-af",
                "loudnorm=I=-17:TP=-2:LRA=7,afade=t=in:d=0.02,afade=t=out:st=%.2f:d=0.05"
                % (b - a - 0.05),
                "-c:v",
                "libx264",
                "-crf",
                "16",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(p),
            ],
            check=True,
        )
    cues.append([round(t + (s - a), 2), round(t + (e - a), 2)] + base[i][2:5])
    t += b - a - XF
    durs.append(b - a)
    parts.append(p)
# voice match: each muse clip invents a slightly different voice; pull every cut of one speaker to that speaker's median pitch (max +-12 %, duration kept -> lip sync kept)
if os.environ.get("VOICE_MATCH", "1") == "1":
    import parselmouth
    from parselmouth.praat import call

    med = {}
    for i, p_ in enumerate(parts):
        wav = W / f"vm{i:02d}.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(p_),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "44100",
                str(wav),
            ],
            check=True,
        )
        sn = parselmouth.Sound(str(wav))
        f = sn.to_pitch(pitch_floor=75, pitch_ceiling=500).selected_array["frequency"]
        f = f[f > 0]
        med[i] = float(np.median(f)) if len(f) else None
    for spk in set(SPK):
        idx = [i for i in range(len(parts)) if SPK[i] == spk and med[i]]
        tgt = float(np.median([med[i] for i in idx]))
        for i in idx:
            r = max(0.88, min(1.12, tgt / med[i]))
            print("voicematch", i, spk, round(med[i]), "->", round(med[i] * r))
            if abs(r - 1) < 0.02:
                continue
            sn = parselmouth.Sound(str(W / f"vm{i:02d}.wav"))
            out = call(sn, "Change gender", 75, 500, 1.0, med[i] * r, 1.0, 1.0)
            out.save(str(W / f"vm{i:02d}_o.wav"), "WAV")
            q = W / f"cutv{i:02d}.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(parts[i]),
                    "-i",
                    str(W / f"vm{i:02d}_o.wav"),
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                    "-c:v",
                    "copy",
                    "-af",
                    "loudnorm=I=-17:TP=-2:LRA=7",
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-shortest",
                    str(q),
                ],
                check=True,
            )
            parts[i] = q
n = len(parts)
ins = []
for p_ in parts:
    ins += ["-i", str(p_)]
fv = []
fa = []
lastv, lasta = "[0:v]", "[0:a]"
acc = durs[0]
for i in range(1, n):
    off = acc - XF
    fv.append(f"{lastv}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[v{i}]")
    lastv = f"[v{i}]"
    fa.append(f"{lasta}[{i}:a]acrossfade=d={XF}[a{i}]")
    lasta = f"[a{i}]"
    acc += durs[i] - XF
subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        *ins,
        "-filter_complex",
        ";".join(fv + fa),
        "-map",
        lastv,
        "-map",
        lasta,
        "-c:v",
        "libx264",
        "-crf",
        "16",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        str(W / "sp.mp4"),
    ],
    check=True,
)
json.dump(cues, open(W / "cues.json", "w"), ensure_ascii=False, indent=0)
(W / "cues.json.spk").write_text(SPK)
print("OK", round(t, 1), "s")
[print(c[0], c[1], c[2]) for c in cues]
