#!/bin/bash
# assemble.sh V [XFADE_AT]  -> jinxiu-V/w/sp.mp4 + words.json  (scale, ease_seams, stitch, jumps, shorten_pauses, transcribe)
set -e
REPO=${MUSE_REPO:-$(cd "$(dirname "$0")/../../../../.." && pwd)}
V=$1; D=~/Movies/museai; T=$D/jinxiu-tools; S=$REPO/.claude/skills/muse-video/scripts
W=$D/jinxiu-$V/w; mkdir -p $W; cd $W; rm -rf eased
for X in A B C D; do
  ffmpeg -v error -y -i $D/jinxiu-$V-$X.mp4 -vf "scale=1080:1920:flags=lanczos,fps=24" -c:v libx264 -crf 16 -pix_fmt yuv420p \
    -c:a aac -ar 48000 -ac 2 $X.mp4
done
uv run -q --no-project --python 3.12 --with opencv-python-headless==4.10.0.84 --with numpy python $T/ease_seams.py eased A.mp4 B.mp4 C.mp4 D.mp4 2>&1 | tail -4
if [[ -n $2 ]]; then XFADE=0.12 XFADE_AT=$2 $S/stitch.sh st.mp4 eased/A.mp4 eased/B.mp4 eased/C.mp4 eased/D.mp4 2>&1 | tail -2
else $S/stitch.sh st.mp4 eased/A.mp4 eased/B.mp4 eased/C.mp4 eased/D.mp4 2>&1 | tail -2; fi
uv run -q --no-project --python 3.12 --with opencv-python-headless==4.10.0.84 --with numpy python $T/jumps.py st.mp4 2>&1 | tail -2
uv run -q --no-project --python 3.12 --with numpy python $T/shorten_pauses.py st.mp4 sp.mp4 1.0 0.5 2>&1 | tail -2
uv run -q --no-project --python 3.12 --with faster-whisper --with opencc-python-reimplemented python $T/transcribe.py sp.mp4 words.json 2>&1 | grep -vE 'Warn|warn' | tail -14
echo ASSEMBLED $V
