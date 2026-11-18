"""Usage: voices.py video.mp4 cues.json SPEAKERS   (SPEAKERS: one letter per cue, e.g. WWMWM)
  uv run --no-project --python 3.11 --with resemblyzer --with librosa --with setuptools \\
      python scripts/voices.py video.mp4 cues.json WWMWM
Each character keeps one voice for the whole video. Every line gets a speaker embedding
(resemblyzer); a line whose median similarity to the same speaker's other lines is < 0.70
is VOICE DRIFT (exit 1). muse picks a new voice per clip: EP09 v7 (three muse clips, voices
kept) sat at 0.50-0.67 and the user heard the voices change; the same video dubbed with dub.py
(one fixed TTS voice per character) sat at >= 0.72. Pitch per line is no identity signal
(the dubbed woman ranged 226-293 Hz). Fix drift with dub.py, never by re-rendering."""

import json
import subprocess
import sys
import tempfile

import librosa
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

MIN_SIM = 0.70
video, cues_path, who = sys.argv[1:4]
cues = json.load(open(cues_path))
if len(who) != len(cues):
    sys.exit(f"SPEAKERS has {len(who)} letters for {len(cues)} cues")
with tempfile.NamedTemporaryFile(suffix=".wav") as wav:  # librosa can't read mp4
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav.name],
        check=True,
    )
    y, sr = librosa.load(wav.name, sr=16000)
enc = VoiceEncoder("cpu", verbose=False)
emb = [
    enc.embed_utterance(preprocess_wav(y[int(a * sr) : int(b * sr)], source_sr=sr))
    for a, b, *_ in cues
]
drift = 0
for w in sorted(set(who)):
    idx = [i for i, x in enumerate(who) if x == w]
    if len(idx) < 2:
        continue
    for i in idx:
        sim = float(np.median([emb[i] @ emb[j] for j in idx if j != i]))
        bad = sim < MIN_SIM
        drift += bad
        print(
            f"{'VOICE DRIFT' if bad else 'ok         '} {w} line {i + 1:2} {cues[i][0]:6.2f}s  "
            f"similarity {sim:.2f} (min {MIN_SIM})"
        )
print("RESULT", "ok" if not drift else f"FAIL {drift} lines drift")
sys.exit(1 if drift else 0)
