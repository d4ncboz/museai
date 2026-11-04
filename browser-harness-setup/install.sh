#!/usr/bin/env bash
# Install browser-harness for Claude Code on Linux, with extra support for Snap Chromium.
# Safe to run again: it upgrades browser-harness and skips steps that are already done.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
claude_dir="$HOME/.claude"
settings="$claude_dir/settings.json"

say() { printf '\n==> %s\n' "$*"; }

command -v uv >/dev/null || { echo "uv is missing. Install it: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
command -v jq >/dev/null || { echo "jq is missing. Install it: sudo apt install jq"; exit 1; }

say "Install or upgrade browser-harness (Python 3.12)"
uv tool install --python 3.12 --upgrade --force browser-harness
browser-harness --version

say "Register the browser-harness skill for Claude Code"
mkdir -p "$claude_dir/skills/browser-harness"
{ browser-harness skill; cat "$here/skill-profiles.md"; } > "$claude_dir/skills/browser-harness/SKILL.md"
echo "Wrote $claude_dir/skills/browser-harness/SKILL.md"

say "Install bh-profile (named browser profiles)"
mkdir -p "$HOME/.local/bin"
install -m 755 "$here/bin/bh-profile" "$HOME/.local/bin/bh-profile"
echo "Installed $HOME/.local/bin/bh-profile"
[[ :$PATH: == *":$HOME/.local/bin:"* ]] || echo "Add ~/.local/bin to your PATH to use bh-profile"

say "Local recordings preference"
if browser-harness recordings | grep -q '(default)'; then
  echo "Recordings save screenshots and action traces on this computer. They can contain private content."
  read -r -p "Enable local browser recordings? [y/N] " answer || answer=""
  if [[ $answer =~ ^[Yy]$ ]]; then browser-harness recordings enable; else browser-harness recordings disable; fi
else
  echo "Keeping your existing setting: $(browser-harness recordings | head -1)"
fi

snap_profile="$HOME/snap/chromium/common/chromium"
if [[ -x /snap/bin/chromium ]]; then
  say "Snap Chromium found: link it where browser-harness looks"
  # browser-harness scans ~/.config/chromium; Snap Chromium keeps its profile under ~/snap.
  mkdir -p "$HOME/.config/chromium"
  for f in DevToolsActivePort "Local State"; do
    target="$HOME/.config/chromium/$f"
    if [[ -e $target && ! -L $target ]]; then
      echo "Skip $target: a real file exists (a non-Snap Chromium uses this folder)"
    else
      ln -sfn "$snap_profile/$f" "$target"
      echo "Linked $target"
    fi
  done

  say "Install the hook that starts Chromium before browser-harness runs"
  mkdir -p "$claude_dir/hooks"
  cp "$here/hooks/ensure-chromium.sh" "$claude_dir/hooks/ensure-chromium.sh"
  chmod +x "$claude_dir/hooks/ensure-chromium.sh"

  [[ -f $settings ]] || echo '{}' > "$settings"
  if jq -e '[.hooks.PreToolUse[]?.hooks[]?.command] | any(contains("ensure-chromium.sh"))' "$settings" >/dev/null; then
    echo "Hook already in $settings"
  else
    cp "$settings" "$settings.bak-browser-harness"
    jq '.hooks.PreToolUse = ((.hooks.PreToolUse // []) + [{"matcher":"Bash","hooks":[{"type":"command","command":"bash ~/.claude/hooks/ensure-chromium.sh","timeout":30,"statusMessage":"Starting Chromium for browser-harness"}]}])' \
      "$settings.bak-browser-harness" > "$settings"
    echo "Added hook to $settings (backup: $settings.bak-browser-harness)"
  fi
else
  echo
  echo "No Snap Chromium found. Google Chrome or a non-Snap Chromium works without extra setup."
fi

cat <<'EOF'

==> Last steps (one time)
1. Open your browser and go to chrome://inspect/#remote-debugging
2. Tick "Allow remote debugging for this browser instance"
3. Restart Claude Code (or open /hooks once)
4. Test it: ask Claude Code "open example.com and tell me the page title"

Each time the browser starts, the first connection shows "Allow remote debugging?". Click Allow.
EOF
