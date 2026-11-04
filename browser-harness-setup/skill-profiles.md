
## Named Profiles (bh-profile)

Use a named profile when the task needs a separate login (a second account, a work vs. personal site), a browser that must not touch the user's normal tabs, or parallel tasks on this computer. Each profile is its own Chromium user-data folder and debug port. Logins stay saved between runs.

```bash
bh-profile run work <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

- `bh-profile run <name>` starts the profile's browser if needed, then runs browser-harness against it. Use it in place of `browser-harness` for every call in that task.
- `bh-profile list` shows profiles and whether they run. `bh-profile stop <name>` closes one.
- A new profile has no logins. At a login wall, stop and ask the user to sign in once in the profile's window.
- Do not run `bh-profile rm`, it deletes the saved logins. Ask the user.
- Use the plain `browser-harness` command (no profile) for the user's normal browser.
