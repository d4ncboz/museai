# browser-harness for Claude Code

Set up Claude Code to control your real browser (click, type, read pages, use your logged-in muse.ai session) through [browser-harness](https://github.com/browser-use/browser-harness). This is a developer tool for working with muse.ai by hand. The gateway's own browser driver does not use it.

Platform: Linux. Tested with Snap Chromium on Ubuntu. Google Chrome and non-Snap Chromium also work.

## Install

From the repository root:

```bash
bash scripts/browser-harness/install.sh
```

Requirements: [uv](https://docs.astral.sh/uv/) and `jq`. The script tells you how to install them if they are missing.

## What `install.sh` does

1. Installs or upgrades `browser-harness` with `uv tool install --python 3.12`.
2. Writes the Claude Code skill to `~/.claude/skills/browser-harness/SKILL.md`.
3. Asks if you want local recordings. The default is no. If you already chose, your choice is kept.
4. Snap Chromium only:
   - Links `DevToolsActivePort` and `Local State` from `~/snap/chromium/common/chromium` into `~/.config/chromium`. browser-harness looks in `~/.config/chromium`, not in the Snap folder.
   - Copies `scripts/browser-harness/ensure-chromium.sh` to `~/.claude/hooks/` and adds it as a `PreToolUse` hook in `~/.claude/settings.json`. The script makes a backup of `settings.json` first. The hook starts Chromium when Claude runs browser-harness and Chromium is closed.

You can run the script again to upgrade. It skips steps that are already done.

## After install (one time)

1. In your browser, open `chrome://inspect/#remote-debugging`.
2. Tick **Allow remote debugging for this browser instance**.
3. Restart Claude Code.
4. Ask Claude Code: "open example.com and tell me the page title".

Each time the browser starts, the first connection shows **Allow remote debugging?**. Click **Allow**. Chrome requires this for your normal profile.

## Troubleshooting

- Run `browser-harness --doctor`.
- `chrome-not-running`: open the browser, then try again.
- Full guide: https://github.com/browser-use/browser-harness/blob/main/install.md

## Uninstall

```bash
uv tool uninstall browser-harness
rm -r ~/.claude/skills/browser-harness ~/.claude/hooks/ensure-chromium.sh
rm ~/.config/chromium/DevToolsActivePort ~/.config/chromium/"Local State"   # Snap only; these are links
```

Then remove the `ensure-chromium.sh` entry from `hooks.PreToolUse` in `~/.claude/settings.json`.
