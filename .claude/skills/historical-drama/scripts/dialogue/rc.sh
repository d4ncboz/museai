#!/bin/bash
# rc.sh V X SRC   SRC = still png (IMAGE) or previous clip mp4 (CONTINUE_FROM). Renders + QA.
REPO=${MUSE_REPO:-$(cd "$(dirname "$0")/../../../../.." && pwd)}
V=$1 X=$2 SRC=$3; D=~/Movies/museai; cd $REPO
export MUSE_SKILL_DEV=1
if [[ $SRC == *.png ]]; then K=IMAGE; else K=CONTINUE_FROM; fi
env SIZE=9:16 DURATION=10 $K=$SRC OUT_NAME=jinxiu-$V-$X.mp4 NO_OPEN=1 ${RETAKE:+RETAKE=1} \
  .claude/skills/muse-video/scripts/muse-video -f $D/jinxiu-$V/$X.txt > $D/jinxiu-$V/$X.log 2>&1
tail -2 $D/jinxiu-$V/$X.log
P=""; [[ $K == CONTINUE_FROM ]] && P=$SRC
cd $D && SCRIPT=jinxiu-$V/$X.script .claude 2>/dev/null; SCRIPT=$D/jinxiu-$V/$X.script $REPO/.claude/skills/muse-video/scripts/check_clip.sh jinxiu-$V-$X.mp4 $P 2>&1 | grep -vE 'Warning|warnings.warn' | tail -8
