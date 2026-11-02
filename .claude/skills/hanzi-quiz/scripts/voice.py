"""Usage: voice.py quizzes/<topic>.json work/<topic>/voice
Run: uv run --no-project --python 3.12 --with edge-tts python scripts/voice.py ...

Writes one 48 kHz mono wav per spoken line plus voice.json ({name: seconds}):
  hook.wav            hook.say in the quiz language (en: AriaNeural, vi: HoaiMyNeural), brisk +12 %
  NN_slow.wav         the answer word, Standard Mandarin (zh-CN-XiaoxiaoNeural) at -20 %: learner read
  NN.wav              the same word at natural speed, +0 %
  outro.wav           outro.say
Phrases are cached by text + voice + rate, so editing one line re-synthesises only that line.
"""
import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

VOICES = {"en": "en-US-AriaNeural", "vi": "vi-VN-HoaiMyNeural", "zh": "zh-CN-XiaoxiaoNeural"}


async def say(text, voice, rate, dst):
    import edge_tts
    key = hashlib.sha1(f"{text}|{voice}|{rate}".encode()).hexdigest()[:12]
    cache = dst.parent / ".cache" / f"{key}.mp3"
    cache.parent.mkdir(exist_ok=True)
    if not cache.exists():
        await edge_tts.Communicate(text.replace("!", "."), voice, rate=f"{rate:+d}%").save(str(cache))
    # trim the TTS lead-in / tail silence so placement times are the real onsets
    trim = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(cache), "-af", trim, "-ar", "48000", "-ac", "1", str(dst)]
    await asyncio.to_thread(subprocess.run, cmd, check=True)


def seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return round(float(out), 3)


async def main(quiz, out):
    q = json.loads(await asyncio.to_thread(Path(quiz).read_text))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lang = VOICES[q.get("lang", "en")]
    jobs = [(q["hook"]["say"], lang, 12, "hook"), (q["outro"]["say"], lang, 8, "outro")]
    for i, w in enumerate(q["words"], 1):
        jobs += [(w["hanzi"], VOICES["zh"], -20, f"{i:02d}_slow"), (w["hanzi"], VOICES["zh"], 0, f"{i:02d}")]
    await asyncio.gather(*(say(t, v, r, out / f"{n}.wav") for t, v, r, n in jobs))
    meta = {n: seconds(out / f"{n}.wav") for *_, n in jobs}
    (out / "voice.json").write_text(json.dumps(meta, indent=1))
    for n, s in meta.items():
        print(f"{n:10s} {s:5.2f}s")


if __name__ == "__main__":
    asyncio.run(main(*sys.argv[1:3]))
