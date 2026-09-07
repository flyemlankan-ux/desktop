# Zen Terminal — current build and personal setup

## What it is
The real Zen browser, with local terminals in ordinary tabs. Browser containers keep
web logins separate. Terminal containers save a name, colour and ordered startup
commands. A plain Terminal choice is created on first launch.

## How to use it
- Open the new-tab/create menu, choose **Container Tab → Terminal**.
- For a saved setup, open **Settings → Container Tabs → Add New Container → Terminal**.
- Add commands in order. Example: `cd ~/projects/my-project`, then `claude`.
- For a remote machine, use `ssh person@computer`, then the command to run there.
- Leave the steps empty for a normal local shell.
- Normal browser tabs, workspaces and folders stay Zen's own features.

The shell runs as the current Mac user. Terminal containers do **not** isolate files
or agent credentials. Only run startup commands you trust. Agent permission prompts
remain the agent's responsibility; the app does not automatically disable them.

## What stays alive
With tmux installed, reload, browser quit and browser crash detach the viewer while
the shell keeps running. Returning to the tab reconnects to the same process.
Explicit tab close or confirmed container conversion/deletion stops its sessions.
A Mac reboot still ends live processes. Without tmux, the terminal clearly says work
is not saved, but typing and live resizing still work.

Each browser profile has a separate set of terminal processes, based on its actual
folder. Copying a profile cannot take over or delete the source profile's live work.
Older development sessions on the old shared `zen-terminal` tmux server are left
untouched, not silently adopted. Profile copying transfers saved browser data, not
running operating-system processes.

## The personal installation versus the distributable
The installer contains no profiles, cookies or passwords. The personal installation
uses `~/Library/Application Support/zen-terminal`, separate from stock Zen's `zen`.
The private copy tool preserves all registered source profile names and files,
excluding rebuildable caches and locks. It refuses overwrites, unsafe paths, source
activity and an older target engine. It never prints login secrets. Some sites may
still require signing in again.

Before copying, quit stock Zen normally. Do not point both apps at one live folder.
Never use `--allow-downgrade` to make a profile fit an older app. Keep the original
Zen installation and its profile folder as the fallback.

Read-only preflight for this Mac (no copy):

```sh
python3 scripts/terminal-tabs/copy-zen-profiles.py \
  --source-root "$HOME/Library/Application Support/zen" \
  --destination-root "$HOME/Library/Application Support/zen-terminal" \
  --source-engine-version 152.0.5 --target-engine-version 152.0.5 \
  --default-profile 'Default (release)' --dry-run
```

Use accurate engine versions from the actual apps, not a guessed Zen app version.
Only use `--copy` after the compatible packaged app has passed its tests and stock
Zen is closed. An existing destination is deliberately not overwritten.

## Testing

```sh
node scripts/terminal-tabs/check-terminal-tabs.mjs
node scripts/terminal-tabs/test-terminal-recipes.mjs
node scripts/terminal-tabs/test-terminal-session-persistence.mjs
node scripts/terminal-tabs/test-terminal-polish.mjs
scripts/terminal-tabs/build-terminal-pty.sh
python3 scripts/terminal-tabs/test-terminal-pty.py
python3 scripts/terminal-tabs/test-copy-zen-profiles.py
node scripts/terminal-tabs/test-terminal-browser.mjs
```

The Python programs are tests/copy tools, not dependencies of the terminal app.
Playwright checks the real terminal page in Chromium with a test-only bridge to the
real native helper and disposable tmux sessions. It does not certify Zen's menus.

The Mac app test drives the real Settings and terminal through Mozilla Marionette:

```sh
python3 -m venv .terminal-test/venv
.terminal-test/venv/bin/pip install marionette_driver
.terminal-test/venv/bin/python3 scripts/terminal-tabs/test-terminal-macos-app.py \
  --app '/path/to/Zen Terminal.app' --label packaged
```

It always makes synthetic profiles. It does not use the founder's logins or conversations.
See `docs/proof/2026-09-07/` for labelled evidence; local patched-app proof is not a
fresh-installer pass. `zen-terminal-build-checklist.md` records remaining work honestly.

## Building the Mac installer
GitHub Actions workflow: **Terminal macOS Dev Build**. Target `aarch64` for this Mac.
The workflow tests first, compiles the browser and native terminal helper, disables
stock updates, uses a separate profile root, and inspects the resulting installer.
The native helper is included in the package manifest, not merely left in a build folder.

This is not an Apple-notarized public release. Do not claim otherwise or disable
Gatekeeper globally. A private build still needs a maintained browser engine and a
future update process; turning off stock auto-update protects the fork but does not
solve long-term security maintenance.

## September 7 stable-base update
The active build is now in `desktop-stable`, branch `release/zen-terminal-1.22b`, using stable Zen 1.22b / Firefox 155.0.1. The older branch remains a recoverable snapshot; its Mac screenshots prove the terminal work on that older app, not acceptance of the new installer. Cloud build34165359251 failed before compilation on an inherited upstream patch. The new Settings integration and final installer must pass again. Personal copying remains unperformed while original Zen is open. For the final copy use target engine155.0.1, never a downgrade override.

The stock automatic updater is deliberately removed so it cannot overwrite the terminal edition. Until a dedicated signed update service exists, browser security updates require rebuilding and installing a tested terminal edition. This is a private development distribution, not an Apple-notarized public release.
