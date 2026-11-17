#!/usr/bin/env bash
# Join 2+ music tracks into one long bed with 8 s crossfades, so a 12-15 min film never loops a 300 s track.
#   music_chain.sh out.m4a m1.m4a m2.m4a [m3.m4a ...]
set -euo pipefail
out=$1; shift
(( $# >= 2 )) || { echo "need 2+ tracks" >&2; exit 2; }
ins=(); fc=""; last="0:a"
for f in "$@"; do ins+=(-i "$f"); done
for (( k=1; k<$#; k++ )); do
  fc+="[$last][$k:a]acrossfade=d=8:c1=tri:c2=tri[a$k];"; last="a$k"
done
ffmpeg -y -hide_banner -loglevel error "${ins[@]}" -filter_complex "${fc%;}" -map "[$last]" -c:a aac -b:a 192k "$out"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out"
