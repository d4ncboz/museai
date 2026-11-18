"""voice_unify.py video.mp4 cues.json SPEAKERS out.mp4
Keeps muse's own dialogue (so every syllable stays on the lips) and makes each character sound like
one person: demucs splits voice/music, each cue's voice is re-pitched to that speaker's target median F0
with Praat "Change gender" (overlap-add, duration 1.0 = no retiming; formant ratio < 1 = larger/older
vocal tract), then voice + music are mixed back.
Targets: TARGET_<L>=f0,formant,range e.g. TARGET_L=92,0.90,0.8 (defaults below).
  uv run --no-project --python 3.12 --with praat-parselmouth --with soundfile --with numpy \
      python voice_unify.py sp.mp4 cues.json WMWW... out.mp4"""

import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import parselmouth
import soundfile as sf
from parselmouth.praat import call

video, cues_p, spk, out = sys.argv[1:5]
cues = json.load(open(cues_p))
assert len(cues) == len(spk), (len(cues), len(spk))
DEF = {"W": (235, 1.0, 1.0), "M": (118, 1.0, 1.0), "L": (92, 0.90, 0.8)}
tg = {
    k: tuple(float(x) for x in os.environ[f"TARGET_{k}"].split(","))
    if os.environ.get(f"TARGET_{k}")
    else DEF[k]
    for k in set(spk)
}
SR = 44100
tmp = tempfile.mkdtemp()
subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        video,
        "-vn",
        "-ac",
        "2",
        "-ar",
        str(SR),
        f"{tmp}/mix.wav",
    ],
    check=True,
)
subprocess.run(
    [
        "uv",
        "run",
        "-q",
        "--no-project",
        "--python",
        "3.11",
        "--with",
        "demucs",
        "--with",
        "soundfile",
        "python",
        "-m",
        "demucs",
        "--two-stems=vocals",
        "-n",
        "htdemucs",
        "-o",
        tmp,
        f"{tmp}/mix.wav",
    ],
    check=True,
)
voc, _ = sf.read(f"{tmp}/htdemucs/mix/vocals.wav")
mus, _ = sf.read(f"{tmp}/htdemucs/mix/no_vocals.wav")
vm = voc.mean(axis=1)
outv = np.zeros_like(vm)
PAD, FADE = 0.12, int(0.03 * SR)
for i, (c, who) in enumerate(zip(cues, spk, strict=False)):
    s0 = max(0, int((c[0] - PAD) * SR))
    s1 = min(len(vm), int((c[1] + PAD) * SR))
    # don't run into the next cue
    if i + 1 < len(cues):
        s1 = min(s1, int((cues[i + 1][0] - 0.02) * SR))
    seg = vm[s0:s1]
    snd = parselmouth.Sound(seg, SR)
    f0 = call(snd.to_pitch(0.01, 60, 400), "Get quantile", 0, 0, 0.5, "Hertz")
    f0t, fr, rng = tg[who]
    if not np.isfinite(f0) or f0 <= 0:
        new = seg
    else:
        res = call(snd, "Change gender", 60, 400, fr, f0t, rng, 1.0)
        new = res.values[0][: len(seg)]
        if len(new) < len(seg):
            new = np.pad(new, (0, len(seg) - len(new)))
        # keep loudness
        new *= (np.sqrt(np.mean(seg**2)) + 1e-9) / (np.sqrt(np.mean(new**2)) + 1e-9)
    w = np.ones(len(seg))
    w[:FADE] = np.linspace(0, 1, min(FADE, len(seg)))[:FADE]
    w[-FADE:] = np.linspace(1, 0, FADE)
    outv[s0:s1] += new * w
    print(
        f"{i + 1:2d} {who} {c[0]:6.2f}-{c[1]:6.2f}  f0 {f0:5.0f} -> {f0t:.0f} Hz  formant {fr}  {c[2]}"
    )
mixd = np.stack([outv, outv], 1) * 1.0 + mus * 0.7
peak = np.abs(mixd).max()
if peak > 0.95:
    mixd *= 0.95 / peak
sf.write(f"{tmp}/new.wav", mixd, SR)
subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        video,
        "-i",
        f"{tmp}/new.wav",
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
        "-ar",
        "48000",
        out,
    ],
    check=True,
)
print("WROTE", out)
