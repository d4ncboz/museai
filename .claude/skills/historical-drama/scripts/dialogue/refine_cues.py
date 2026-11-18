"""refine_cues.py sp.wav cues.json  -> overwrites cues.json with start/end snapped to real voiced segments
(whisper stretches a word over the silence before it, so a cue can swallow the previous speaker's tail)."""

import json
import sys

import numpy as np
import parselmouth

wav, cp = sys.argv[1:3]
cues = json.load(open(cp))
it = parselmouth.Sound(wav).to_intensity(minimum_pitch=100, time_step=0.01)
t = it.xs()
v = it.values[0]
loud = v > float(__import__("os").environ.get("THR", 40))
seg = []
idx = np.where(loud)[0]
if len(idx):
    st = prev = idx[0]
    for k in idx[1:]:
        if t[k] - t[prev] > 0.15:
            seg.append([t[st], t[prev]])
            st = k
        prev = k
    seg.append([t[st], t[prev]])
out = []
for c in cues:
    s0, e0 = c[0], c[1]
    ss = next((s for s in seg if s[1] > s0 + 0.3), None)
    ns = ss[0] if ss and s0 - 0.15 <= ss[0] <= s0 + 1.2 else s0
    ce = [s[1] for s in seg if e0 - 0.35 <= s[1] <= e0 + 0.5]
    ne = min(ce, key=lambda x: abs(x - e0)) if ce else e0
    out.append([round(ns, 2), round(max(ne, ns + 0.3), 2)] + c[2:])
    print(f"{s0:6.2f}-{e0:6.2f} -> {out[-1][0]:6.2f}-{out[-1][1]:6.2f}  {c[2]}")
json.dump(out, open(cp, "w"), ensure_ascii=False, indent=0)
