"""Gate a healing music take: calm, soft, never dramatic. Run with the ACE venv python (librosa).

Usage: calm.py track.m4a  -> prints the numbers; exit 3 when the take is too busy, bright or swelling.
Limits from the user's verdicts: the hv-0002 soft take kept was 2.25 onsets/s, its MOOD=sunny take
(7.2/s) was "too dramatic"; delivered hv 01/02 (3.4-3.5/s, centroid 860-1020 Hz) were called dramatic
too (2026-11-04). Reference 3 (the calm piano the user liked) is ~530 Hz centroid.
"""

import sys

import librosa
import numpy as np

MAX_ONSETS = 2.5  # notes per second: held notes, not running arpeggios
MAX_CENTROID = 650  # Hz, median: warm and low, not a bright singing piano
MAX_SWELL = 6.0  # dB, loudest 3 s over the median 3 s: no crescendo or dramatic build

y, sr = librosa.load(sys.argv[1], sr=22050, mono=True)
onsets = len(librosa.onset.onset_detect(y=y, sr=sr)) / (len(y) / sr)
centroid = float(np.median(librosa.feature.spectral_centroid(y=y, sr=sr)))
hop = sr * 3 // 2  # 3 s windows, 1.5 s hop; skip the fades at both ends
win = [y[i : i + 2 * hop] for i in range(hop, len(y) - 4 * hop, hop)]
db = [10 * np.log10(np.mean(w**2) + 1e-12) for w in win] or [0.0]
swell = max(db) - float(np.median(db))
bad = [
    f"{name} {val:.2f} > {lim}"
    for name, val, lim in (
        ("onsets/s", onsets, MAX_ONSETS),
        ("centroid Hz", centroid, MAX_CENTROID),
        ("swell dB", swell, MAX_SWELL),
    )
    if val > lim
]
print(
    f"music: {onsets:.2f} onsets/s (max {MAX_ONSETS}), centroid {centroid:.0f} Hz (max {MAX_CENTROID}), swell {swell:.1f} dB (max {MAX_SWELL})",
    file=sys.stderr,
)
if bad:
    print(
        "music: not calm enough for a healing video (" + ", ".join(bad) + "); try another seed",
        file=sys.stderr,
    )
    sys.exit(3)
