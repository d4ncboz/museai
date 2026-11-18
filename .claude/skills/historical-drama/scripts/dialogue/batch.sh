#!/bin/bash
# batch.sh "V X SRC" ...   renders clips in order (one muse request at a time); a failing clip gets one
# retake and the take with fewer failing lines is kept. SRC "prev" = the clip just rendered (CONTINUE_FROM).
D=~/Movies/museai; T=$D/jinxiu-tools; prev=""
nfail() { r=$(grep -h 'RESULT' "$1" | tail -1); [[ $r == *PASS* || $r == *" ok"* ]] && { echo 0; return; }
  l=$(echo "$r" | sed -n 's/.*lines \([0-9,]*\).*/\1/p'); [[ -z $l ]] && { echo 99; return; }
  echo "$l" | tr ',' '\n' | grep -c .; }
for job in "$@"; do
  set -- $job; V=$1 X=$2 SRC=$3; [[ $SRC == prev ]] && SRC=$prev
  echo "== $V-$X from $(basename $SRC)"
  $T/rc.sh $V $X $SRC > $D/jinxiu-$V/$X.qa1 2>&1; tail -3 $D/jinxiu-$V/$X.qa1
  n1=$(nfail $D/jinxiu-$V/$X.qa1)
  if [[ $n1 != 0 ]]; then
    cp $D/jinxiu-$V-$X.mp4 $D/jinxiu-$V/$X-take1.mp4
    RETAKE=1 $T/rc.sh $V $X $SRC > $D/jinxiu-$V/$X.qa2 2>&1; tail -3 $D/jinxiu-$V/$X.qa2
    n2=$(nfail $D/jinxiu-$V/$X.qa2)
    if (( n1 < n2 )); then cp $D/jinxiu-$V/$X-take1.mp4 $D/jinxiu-$V-$X.mp4; echo "KEEP take1 ($n1 < $n2)"; else echo "KEEP take2 ($n2 <= $n1)"; fi
  fi
  prev=$D/jinxiu-$V-$X.mp4
done
echo BATCHDONE
