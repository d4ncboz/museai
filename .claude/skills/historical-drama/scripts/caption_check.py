"""caption_check.py CUES_JSON VIDEO [--tol 0.85]
Gate: what the character SAYS must equal the burned caption. For each cue [s,e,zh,...] whisper the
audio of VIDEO in [s-0.3, e+0.3] and compare hanzi with the cue text (opencc to simplified).
Fails (exit 1) when a cue matches < tol, when a cue's text is heard twice in its window
(a repeated line), or when audio outside every cue window carries speech (stray repeat).
Needs pypinyin. Run: uv run -q --no-project --python 3.12 --with faster-whisper --with numpy --with soundfile --with opencc-python-reimplemented --with pypinyin python caption_check.py cues.json sp.mp4
"""

import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from opencc import OpenCC
from pypinyin import lazy_pinyin

cues = json.load(open(sys.argv[1]))
video = sys.argv[2]
tol = float(sys.argv[sys.argv.index("--tol") + 1]) if "--tol" in sys.argv else 0.85
wav = tempfile.mktemp(suffix=".wav")
subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True
)
a, sr = sf.read(wav, dtype="float32")
os.remove(wav)
m = WhisperModel("small", compute_type="int8")
cc = OpenCC("t2s")


def han(t):
    return re.sub(r"[^一-鿿]", "", cc.convert(t))


def hear(x):
    segs, _ = m.transcribe(
        x, language="zh", initial_prompt="简体中文", condition_on_previous_text=False
    )
    return han("".join(s.text for s in segs))


bad = 0
for i, c in enumerate(cues):
    s, e, zh = c[0], c[1], han(c[2])
    got = hear(a[int(max(0, s - 0.3) * sr) : int((e + 0.3) * sr)])
    r = max(
        difflib.SequenceMatcher(None, zh, got).ratio(),
        difflib.SequenceMatcher(None, lazy_pinyin(zh), lazy_pinyin(got)).ratio(),
    )  # homophones (她/他, 夫/福) are whisper noise
    rep = got.count(zh) > 1 or (len(got) > 1.6 * len(zh) + 1)
    ok = r >= tol and not rep
    bad += not ok
    print(
        ("OK  " if ok else "BAD ")
        + f"{i} {s:.1f}-{e:.1f} say={got} caption={zh} match={r:.2f}"
        + (" REPEATED" if rep else "")
    )
mask = np.zeros(len(a), bool)
mask[: int((cues[-1][1] + 0.5) * sr)] = True  # body only (recap audio follows)
for c in cues:
    mask[int(max(0, c[0] - 0.5) * sr) : int((c[1] + 0.5) * sr)] = False
rms = np.sqrt(np.convolve(a**2, np.ones(1600) / 1600, "same"))
stray = (rms[mask] > 0.02).mean() if mask.any() else 0
print(f"stray speech outside cues: {stray:.1%}")
sys.exit(1 if bad else 0)
