"""Usage: transcribe.py video.mp4 out.json [hint text]  -> word timestamps (zh)."""

import json
import os
import subprocess
import sys

import numpy as np
import opencc
from faster_whisper import WhisperModel

video, out = sys.argv[1], sys.argv[2]
hint = sys.argv[3] if len(sys.argv) > 3 else None
pcm = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
    capture_output=True,
    check=True,
).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
model = WhisperModel(os.environ.get("WMODEL", "small"), device="cpu", compute_type="int8")
segments, _ = model.transcribe(
    audio,
    language="zh",
    word_timestamps=True,
    initial_prompt=hint,
    vad_filter=os.environ.get("VAD", "1") == "1",
)
# Whisper often answers zh in traditional characters (EP10), which qa.py scores as misheard
t2s = opencc.OpenCC("t2s").convert
words = []
for seg in segments:
    print(f"{seg.start:6.2f}-{seg.end:6.2f} {t2s(seg.text)}")
    words += [{"w": t2s(w.word), "s": round(w.start, 2), "e": round(w.end, 2)} for w in seg.words]
json.dump(words, open(out, "w"), ensure_ascii=False)
