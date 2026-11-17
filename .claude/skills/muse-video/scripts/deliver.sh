#!/usr/bin/env bash
# Usage: FINAL=1 deliver.sh final.mp4 work_dir [prefix]
# Only once the user has accepted the 1080p preview (shown from the work folder, never copied to
# the Desktop): writes the ONE deliverable to ~/Desktop: the rendered 1080p file as is, or with
# UHD=1 (only when the user asked for 4K) the 4K UHD video (upscale.sh, Real-ESRGAN, ~1 h for 15 s), to ~/Desktop (DEST=dir to change) and checks it. Then it deletes
# every other resource made for the video: earlier Desktop copies whose name starts with prefix,
# the work folder (raw clips, takes, sheets, mouth strips, frame grabs, cues, words, prompts), the
# ~/Movies/museai renders starting with prefix, and the server copies in data/media of every take it logged
# (task ids) or that is identical to a clip.
# prefix defaults to the work folder's name (e.g. ep10). Deleted = moved to the Trash.
# CAPTIONS_FILE=captions.json: one caption per platform ({"youtube": "title\n\ndescription", "tiktok": ...,
# "facebook", "instagram", "x", "threads"}), written with the social-captions skill and checked by its
# captions.py before anything is copied. CAPTION="text" / CAPTION_FILE=caption.txt: the shared caption, used
# for a platform without its own (default: the TikTok one). Both are saved to the dashboard's "Ready to
# post" queue (MUSEAI_BASE, default http://127.0.0.1:18610) for the video.
# THUMB_DIR=dir: the thumbnail skill's <name>_9x16.jpg (+ <name>_16x9.jpg for a horizontal video), copied
# next to the video as "<video> - thumbnail 9x16.jpg" / "16x9.jpg" (the dashboard shows them and trashes
# them with the video). A vertical video needs no 16x9 one (user rule, 2026-10-30).
set -euo pipefail
final=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
work=$(cd "$2" && pwd)
prefix=${3:-$(basename "$work")}
dest=${DEST:-$HOME/Desktop}

# never trash a home, repo or system folder by a wrong argument
case "$work" in
  /|"$HOME"|"$HOME"/Desktop|"$HOME"/Movies|"$HOME"/Movies/museai|"$HOME"/Work|"$HOME"/Documents|"$dest")
    echo "refusing to trash $work" >&2; exit 1 ;;
esac
[ -e "$work/.git" ] || [ -e "$work/pyproject.toml" ] && { echo "refusing to trash a repo: $work" >&2; exit 1; }
[ ${#prefix} -ge 3 ] || { echo "prefix '$prefix' too short" >&2; exit 1; }

mkdir -p "$dest"
out="$dest/$(basename "$final")"
[ "${FINAL:-0}" = 1 ] || { echo "preview: show $final from the work folder; nothing goes to the Desktop before FINAL=1" >&2; exit 1; }
# Every final lands on the dashboard's posting queue; without a caption it shows there empty
# (EP20, 2026-10-28). NO_CAPTION=1 only for a video that will not be posted.
caption=${CAPTION:-}
[ -n "${CAPTION_FILE:-}" ] && caption=$(cat "$CAPTION_FILE")
captions=
if [ -n "${CAPTIONS_FILE:-}" ]; then
  python3 "$(dirname "$0")/../../social-captions/scripts/captions.py" check "$CAPTIONS_FILE" ||
    { echo "captions break a platform rule: fix $CAPTIONS_FILE" >&2; exit 1; }
  captions=$(cat "$CAPTIONS_FILE")
fi
[ -n "$caption$captions" ] || [ "${NO_CAPTION:-0}" = 1 ] ||
  { echo "no caption: pass CAPTIONS_FILE=captions.json (social-captions skill; or NO_CAPTION=1 for a video that will not be posted)" >&2; exit 1; }
# Every posted video gets thumbnails (user rule, 2026-10-29); NO_THUMB=1 only for one that will not be posted.
thumbs=()
if [ -n "${THUMB_DIR:-}" ]; then
  kinds=9x16
  wh=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$final")
  [ "${wh%x*}" -gt "${wh#*x}" ] && kinds="9x16 16x9"
  for k in $kinds; do
    t=$(ls "$THUMB_DIR"/*_"$k".jpg 2>/dev/null | head -1)
    [ -n "$t" ] || { echo "no *_$k.jpg in $THUMB_DIR" >&2; exit 1; }
    thumbs+=("$k=$t")
  done
elif [ "${NO_THUMB:-${NO_CAPTION:-0}}" != 1 ]; then
  echo "no thumbnails: make them with ../thumbnail (scripts/thumb.py) and pass THUMB_DIR=dir (or NO_THUMB=1)" >&2; exit 1
fi
# 4K only on request (UHD=1): a good 1080p render needs no upscale (user rule, 2026-10-27)
if [ "${UHD:-0}" = 0 ]; then
  cp "$final" "$out"
  cmp -s "$final" "$out" || { echo "copy differs: $out" >&2; exit 1; }
else
  "$(dirname "$0")/upscale.sh" "$final" "$out"
  frames() { ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets -of csv=p=0 "$1"; }
  [ "$(frames "$final")" = "$(frames "$out")" ] || { echo "frame count differs: $out" >&2; exit 1; }
fi
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out" >/dev/null || { echo "copy unreadable: $out" >&2; exit 1; }
echo "DELIVERED $out"
kept=("$out")
for kt in ${thumbs[@]+"${thumbs[@]}"}; do
  t="$dest/$(basename "${out%.*}") - thumbnail ${kt%%=*}.jpg"
  cp "${kt#*=}" "$t" && kept+=("$t") && echo "THUMBNAIL $t"
done
# DEST = an episode folder on the Desktop ("Chinese 40 · Fri 11-12 12h00 · <title>"): the dashboard
# lists only folders holding .museai-post, so without it the video never reached "Ready to post" (2026-11-17).
[ "$(dirname "$dest")" = "$HOME/Desktop" ] && touch "$dest/.museai-post"
if [ -n "$caption$captions" ]; then
  name=$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$(basename "$out")")
  CAPTION="$caption" CAPTIONS="$captions" python3 -c '
import json, os
own = json.loads(os.environ["CAPTIONS"] or "{}")
print(json.dumps({"caption": os.environ["CAPTION"] or own.get("tiktok", ""), "captions": own}))' |
    curl -sf -X POST "${MUSEAI_BASE:-http://127.0.0.1:18610}/dashboard/posts/$name" -H "Content-Type: application/json" --data-binary @- >/dev/null &&
    echo "CAPTIONS saved for the posting queue" || echo "captions not saved (server down?), add them on the dashboard"
fi

shopt -s nullglob
junk=("$work")
# "$prefix"[-_.]* so ep1 never takes ep10.mp4 along
for f in "$dest/$prefix"[-_.]*; do
  for k in "${kept[@]}"; do [ "$f" = "$k" ] && continue 2; done
  junk+=("$f")
done
# Renders are files only: every directory under ~/Movies/museai is some video's work folder, and a short
# prefix (reel) matched reel-bled/, reel-machupicchu/ ... of other running sessions (2026-11-05).
# This video's own folder is "$work", already listed above. A render named after another work folder
# (reel-b_s1.mp4 next to reel-b/) belongs to that video, not this one.
others=()
for d in "$HOME/Movies/museai"/*/; do
  d=${d%/}; [ "$d" = "$work" ] || others+=("$(basename "$d")")
done
renders=()
for f in "$HOME/Movies/museai/$prefix"[-_.]*; do
  [ -d "$f" ] && continue
  b=$(basename "$f") w=$(basename "$work")
  for o in ${others[@]+"${others[@]}"}; do
    # the longest matching folder name owns the file (reel-a_s1.mp4 stays ours next to a reel/ folder)
    case "$b" in "$o"[-_.]*) case "$b" in "$w"[-_.]*) [ ${#w} -ge ${#o} ] && continue ;; esac; continue 2 ;; esac
  done
  renders+=("$f")
done
junk+=(${renders[@]+"${renders[@]}"})
# Server copies: every take the server rendered for this video stays in <data>/media (1490 files, 10 GB by
# 2026-11-05), also rejected takes and re-encoded ones no byte check finds. The skills run from a
# museai-main checkout with no data/, so look in the running server's folder too (MUSEAI_DATA to force one).
datas=()
for d in "${MUSEAI_DATA:-}" "$(cd "$(dirname "$0")/../../../.." && pwd)/data" \
  "$(lsof -a -d cwd -Fn -p "$(pgrep -f 'python -m museai' | head -1)" 2>/dev/null | sed -n 's/^n//p' | head -1)/data"; do
  [ -n "$d" ] && [ -d "$d/media" ] || continue
  d=$(cd "$d" && pwd)
  for u in ${datas[@]+"${datas[@]}"}; do [ "$u" = "$d" ] && continue 2; done
  datas+=("$d")
done
# 1. each task muse-video logged (task task_x submitted) in the work folder or a render log: its result file
ids=$(grep -rhoE 'task_[0-9a-f]{16}' "$work" ${renders[@]+"${renders[@]}"} 2>/dev/null | sort -u || true)
mp4s=()
while IFS= read -r f; do mp4s+=("$f"); done < <(find "$work" -type f -name '*.mp4')
for f in ${renders[@]+"${renders[@]}"}; do [ "${f%.mp4}" = "$f" ] || mp4s+=("$f"); done
for d in ${datas[@]+"${datas[@]}"}; do
  if [ -n "$ids" ] && [ -f "$d/tasks.json" ]; then
    while IFS= read -r m; do junk+=("$m"); done < <(IDS="$ids" python3 - "$d" <<'PY'
import json, os, sys
d = sys.argv[1]
ids = set(os.environ["IDS"].split())
for t in json.load(open(os.path.join(d, "tasks.json"))):
    url = (t.get("result") or {}).get("url") or ""
    p = os.path.join(d, "media", os.path.basename(url))
    if t.get("id") in ids and url and os.path.isfile(p):
        print(p)
PY
)
  fi
  # 2. any server file identical to a clip of this video (tasks.json keeps only the last 500 tasks)
  # (one stat per folder, cmp only on equal sizes: data/media holds thousands of files)
  [ ${#mp4s[@]} -gt 0 ] || continue
  sizes=" $(stat -f%z "${mp4s[@]}" | tr '\n' ' ')"
  while read -r s m; do
    case "$sizes" in *" $s "*) ;; *) continue ;; esac
    for f in "${mp4s[@]}"; do cmp -s "$m" "$f" && { junk+=("$m"); break; }; done
  done < <(find "$d/media" -maxdepth 1 -name 'vid_*.mp4' -exec stat -f'%z %N' {} +)
done
# list each path once, or trash fails on an already-trashed path and set -e aborts the cleanup
uniq=()
for f in "${junk[@]}"; do
  for u in ${uniq[@]+"${uniq[@]}"}; do [ "$u" = "$f" ] && continue 2; done
  uniq+=("$f"); echo "delete $f"
done
trash "${uniq[@]}"
for k in "${kept[@]}"; do echo "LEFT ONLY $k"; done
