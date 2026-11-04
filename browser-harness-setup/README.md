# browser-harness for Claude Code

This package lets Claude Code control your real browser (click, type, read pages, use your logged-in sessions) through [browser-harness](https://github.com/browser-use/browser-harness).

Platform: Linux. Tested with Snap Chromium on Ubuntu. Google Chrome and non-Snap Chromium also work.

## Install

```bash
unzip browser-harness-setup.zip
cd browser-harness-setup
bash install.sh
```

Requirements: [uv](https://docs.astral.sh/uv/) and `jq`. The script tells you how to install them if they are missing.

## What `install.sh` does

1. Installs or upgrades `browser-harness` with `uv tool install --python 3.12`.
2. Writes the Claude Code skill to `~/.claude/skills/browser-harness/SKILL.md`, with the named-profile section from `skill-profiles.md`.
3. Installs `bh-profile` to `~/.local/bin` (see [Named profiles](#named-profiles)).
4. Asks if you want local recordings. The default is no. If you already chose, your choice is kept.
5. Snap Chromium only:
   - Links `DevToolsActivePort` and `Local State` from `~/snap/chromium/common/chromium` into `~/.config/chromium`. browser-harness looks in `~/.config/chromium`, not in the Snap folder.
   - Copies `hooks/ensure-chromium.sh` to `~/.claude/hooks/` and adds it as a `PreToolUse` hook in `~/.claude/settings.json`. The script makes a backup of `settings.json` first. The hook starts Chromium when Claude runs browser-harness and Chromium is closed.

You can run the script again to upgrade. It skips steps that are already done.

## After install (one time)

1. In your browser, open `chrome://inspect/#remote-debugging`.
2. Tick **Allow remote debugging for this browser instance**.
3. Restart Claude Code.
4. Ask Claude Code: "open example.com and tell me the page title".

Each time the browser starts, the first connection shows **Allow remote debugging?**. Click **Allow**. Chrome requires this for your normal profile.

## Named profiles

`bh-profile` runs extra browsers, each with its own profile folder and debug port. Use one per account or per task. Logins stay saved, and your normal browser is not touched.

```bash
bh-profile start work                 # open the profile's browser, then sign in once by hand
bh-profile run work <<'PY'            # run browser-harness against it
new_tab("https://example.com")
print(page_info())
PY
bh-profile list                       # all profiles, port, running or stopped
bh-profile stop work                  # close the browser and its daemon
bh-profile rm work                    # delete the profile and its logins (asks first)
eval "$(bh-profile env work)"         # or set BU_NAME and BU_CDP_URL in your shell
```

- No "Allow remote debugging?" prompt: profiles start with `--remote-debugging-port`.
- Profiles live in `~/snap/chromium/common/bh-profiles` (Snap Chromium) or `~/.local/share/bh-profiles`. Set `BH_PROFILES_DIR` to change it.
- Browser: first found of `chromium`, `google-chrome`, `chromium-browser`. Set `BH_BROWSER` to pick one.
- Ports: 9300-9399, one fixed port per profile.
- `bh-profile start <name> [url] --label "Work A"` sets the Chromium profile name (window title and profile menu). It is applied at start, while the browser is closed.
- Profiles open with `--profile-directory=Default`, so the "Who's using Chromium?" picker does not show.

## Troubleshooting

- Run `browser-harness --doctor`.
- `chrome-not-running`: open the browser, then try again.
- Full guide: https://github.com/browser-use/browser-harness/blob/main/install.md

## Uninstall

```bash
uv tool uninstall browser-harness
rm -r ~/.claude/skills/browser-harness ~/.claude/hooks/ensure-chromium.sh ~/.local/bin/bh-profile
rm ~/.config/chromium/DevToolsActivePort ~/.config/chromium/"Local State"   # Snap only; these are links
```

Then remove the `ensure-chromium.sh` entry from `hooks.PreToolUse` in `~/.claude/settings.json`.
