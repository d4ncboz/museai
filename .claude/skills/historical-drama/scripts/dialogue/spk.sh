#!/bin/bash
# spk.sh V   speakers check on jinxiu-V/w/vu.mp4 (V=02: L->W, FEMALE=Z, LEFT from env)
V=$1; cd ~/Movies/museai/jinxiu-$V/w; S=$(cat cues.json.spk | tr L W)
[[ $V == 02 ]] && export FEMALE=Z
uv run -q --no-project --python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless==4.10.0.84 --with librosa --with numpy \
  python ../../jinxiu-tools/speakers.py ${VID:-vu.mp4} cues.json $S m$V.jpg 2>&1 | grep -vE 'W0000|I0000|INFO|Warn|warn' | tail -25
