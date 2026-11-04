#!/usr/bin/env bash
# Render several prompts at the same time on one browser profile, each in its own background tab
# of the profile's one window. Run from the repo root, with museai running:
#   bash .claude/skills/vocab-quiz-video/scripts/run_parallel.sh <profile> /tmp/vocab-german-a1-city.prompt.txt ...
# Output per prompt: videos/<slug>.mp4 and videos/<slug>.render.log (slug = prompt name without vocab- and .prompt.txt).
set -u
prof=${1:?profile name}; shift
api=${MUSEAI_URL:-http://localhost:18610}
key=${MUSEAI_KEY:-$(cat data/api_key)}
cdp=$(curl -s -X POST "$api/v1/profiles/$prof/launch" -H "Authorization: Bearer $key" | jq -r .cdp_url)
[[ $cdp == http* ]] || { echo "launch failed: $prof" >&2; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)

for prompt in "$@"; do
  slug=$(basename "$prompt" .prompt.txt); slug=${slug#vocab-}
  name=$(printf '%s' "$prof-$slug" | cut -c1-64)  # one browser-harness daemon (and tab) per run
  (
    BU_NAME=$name BU_CDP_URL=$cdp PROMPT_FILE=$prompt OUT=videos/$slug.mp4 REC=$slug \
      timeout 3000 browser-harness < "$here/muse_run.py" > "videos/$slug.render.log" 2>&1
    rc=$?
    # Stopping a named daemon also closes the blank tab it keeps, so the window stays clean.
    BU_NAME=$name browser-harness --reload >/dev/null 2>&1
    echo "$slug exit=$rc: $(grep -E 'video ready|timeout|stopped replying|not a new chat' "videos/$slug.render.log" | tail -1)"
  ) &
  sleep 20  # muse.ai sometimes lands on its home page when new chats open at the same moment
done
wait
