#!/usr/bin/env bash
# Check a vocab quiz video: format, ticks, speech-to-text of every answer, frame sheet.
# Usage: check_video.sh <video.mp4> <lang_code, e.g. de>
# Override timings for older layouts: HOOK=1.5 WORD=7 VOICE1=6.5 VOICE2=6.5 check_video.sh ...
# Timings follow SKILL.md "Episode format": hook 3 s, 6 words x 7 s, ticks at 0.5/1.5/2.5 s, voice at 3.6 s and 5.3 s.
set -euo pipefail
video=$(realpath "$1"); lang=$2
HOOK=${HOOK:-3}; WORD=${WORD:-7}; VOICE1=${VOICE1:-3.5}; VOICE2=${VOICE2:-5.2}
work="${video%.*}-check"; mkdir -p "$work"; cd "$work"

echo "== format"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration -of compact "$video"

ffmpeg -v error -y -i "$video" -ac 1 -ar 16000 audio.wav

echo "== ticks (loud 0.1 s windows from 0.3 to 3.3 s of each word; expect 0.5 1.5 2.5)"
python3 -I - "$HOOK" "$WORD" <<'EOF'
import array, math, sys, wave
hook, word = float(sys.argv[1]), float(sys.argv[2])
w = wave.open("audio.wav"); sr = w.getframerate(); a = array.array("h", w.readframes(w.getnframes()))
for r in range(6):
    base = hook + r * word; hits = []
    for i in range(round((base + 0.3) * 10), round((base + 3.3) * 10)):
        s = a[int(i * 0.1 * sr):int((i + 1) * 0.1 * sr)]
        p = max((abs(x) for x in s), default=0)
        if p and 20 * math.log10(p / 32768) > -12:
            hits.append(round(i / 10 - base, 1))
    print(f"word {r + 1}: {hits}")
EOF

echo "== speech-to-text (first and second reading of each answer)"
for r in 0 1 2 3 4 5; do
  for k in 1 2; do
    off=$([ $k = 1 ] && echo "$VOICE1" || echo "$VOICE2")
    s=$(python3 -c "print($HOOK + $r * $WORD + $off)")
    ffmpeg -v error -y -ss "$s" -t 1.7 -i audio.wav "voice_${r}_${k}.wav"
  done
done
uv run --no-project --python 3.12 --with faster-whisper==1.1.1 --with requests python -I - "$lang" <<'EOF' 2>&1 | grep -E '^word'
import sys, wave
import numpy as np
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)
for r in range(6):
    heard = []
    for k in (1, 2):
        w = wave.open(f"voice_{r}_{k}.wav")
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        # vad_filter: silent windows otherwise come back as invented text ("SWR 2020").
        segs, _ = m.transcribe(a, language=sys.argv[1], beam_size=5, vad_filter=True)
        heard.append(" ".join(s.text.strip() for s in segs))
    print(f"word {r + 1}: {heard}")
EOF

echo "== frames"
times=(0.7)
for r in 0 1 2 3 4 5; do
  times+=("$(python3 -c "print($HOOK + $r * $WORD + 2.0)")" "$(python3 -c "print($HOOK + $r * $WORD + 4.5)")")
done
times+=("$(python3 -c "print($HOOK + 6 * $WORD + 1.5)")")
inputs=()
for t in "${times[@]}"; do
  ffmpeg -v error -y -ss "$t" -i "$video" -frames:v 1 -vf scale=240:-1 "f_$t.jpg"; inputs+=(-i "f_$t.jpg")
done
ffmpeg -v error -y "${inputs[@]}" -filter_complex "xstack=inputs=14:grid=7x2" sheet.jpg
echo "sheet: $work/sheet.jpg (hook, then per word: countdown + answer, then end card)"
