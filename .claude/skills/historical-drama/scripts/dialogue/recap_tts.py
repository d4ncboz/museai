"""recap_tts.py spec.json [voice] -> dir/rv{i}.wav: the standard Putonghua teaching voice (edge-tts zh-CN-XiaoxiaoNeural, as in the
modern learning-Chinese videos) reads ONLY the recap words, once each. Sets spec['recap_audio'] for finish.py.
Run: uv run -q --no-project --python 3.12 --with edge-tts python recap_tts.py spec.json"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import edge_tts

sp = json.load(open(sys.argv[1]))
voice = sys.argv[2] if len(sys.argv) > 2 else "zh-CN-XiaoxiaoNeural"
d = Path(sp["dir"])


async def one(i, text):
    mp3 = d / f"rv{i}.mp3"
    await edge_tts.Communicate(text + "。", voice, rate="-12%").save(str(mp3))
    subprocess.run(  # noqa: ASYNC221
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(mp3),
            "-af",
            "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,loudnorm=I=-16:TP=-1.5",
            "-ar",
            "24000",
            "-ac",
            "1",
            str(d / f"rv{i}.wav"),
        ],
        check=True,
    )
    mp3.unlink()


async def main():
    for i, r in enumerate(sp["recap"]):
        await one(i, r[2])


asyncio.run(main())
sp["recap_audio"] = [str(d / f"rv{i}.wav") for i in range(len(sp["recap"]))]
json.dump(sp, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
for i in range(len(sp["recap"])):
    print(
        sp["recap"][i][2],
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(d / f"rv{i}.wav"),
            ],
            capture_output=True,
            text=True,
        ).stdout.strip(),
    )
