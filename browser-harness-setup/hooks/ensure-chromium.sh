#!/usr/bin/env bash
# PreToolUse hook: start Snap Chromium before browser-harness runs code (heredoc/herestring) when it is not running.
# browser-harness finds Chromium through links in ~/.config/chromium that point to the Snap profile.
cmd=$(jq -r '.tool_input.command // ""')
[[ $cmd =~ browser-harness[^|\;\&]*\<\< ]] || exit 0
pgrep -x chrome -a | grep -q /snap/chromium/ && exit 0

port_file="$HOME/snap/chromium/common/chromium/DevToolsActivePort"
started=$(date +%s)
setsid chromium >/dev/null 2>&1 < /dev/null &
# Wait until Chromium writes a fresh DevToolsActivePort (max 15s)
for _ in $(seq 1 30); do
  [[ -f $port_file && $(stat -c %Y "$port_file") -ge $started ]] && break
  sleep 0.5
done
# Drop the daemon left from the previous Chromium session; it holds a dead connection
browser-harness --reload >/dev/null 2>&1
exit 0
