# Terminal tabs inside Zen: build path

## Simple idea

We are using the real Zen Browser source as the shell.

Zen already has the Mac feel we want: the sidebar, workspaces, menus, native window behaviour, and polished tab handling.

Our change is narrow:

- Zen still opens normal browser tabs.
- We add a new kind of tab for terminal work.
- The terminal tab should eventually run Claude, Codex, SSH, and normal shell commands inside the Zen-shaped app.

## Why this is not built locally

This Mac does not have enough free space for a full Zen/Firefox build.

A full local build can need tens of GB. This Mac has much less than that free.

Chubs has storage, but Chubs is Linux, not macOS. It can hold source code, but it cannot prove the final Mac app properly.

So the correct path is:

1. Keep editing source locally.
2. Push the branch to GitHub.
3. Let GitHub run the macOS build on a cloud Mac.
4. Download the DMG from the workflow artifacts.

An artifact is just the built file GitHub gives back, like a downloadable `.dmg`.

## Manual GitHub build

Workflow added:

```text
.github/workflows/terminal-macos-dev-build.yml
```

Run it from GitHub Actions:

1. Open the repo on GitHub.
2. Go to **Actions**.
3. Pick **Terminal macOS Dev Build**.
4. Click **Run workflow**.
5. Choose:
   - `aarch64` for Apple Silicon Macs.
   - `x86_64` for older Intel Macs.
6. Wait for the build.
7. Download the uploaded DMG artifact.

## Current terminal-tab state

This slice wires a first terminal-tab entry into the real Zen source.

It adds:

- a **New Terminal Tab** menu item,
- a Zen command for that menu item,
- a terminal-tab marker on the browser tab,
- a small tab icon hint.

This now opens a real Zen page for the terminal tab and starts a local Mac shell through macOS pseudo-terminal support.

A pseudo-terminal means command-line apps are more likely to behave as if they are inside a real Terminal window.

This now sends keystrokes directly into the shell: letters, Enter, Backspace, arrows, Ctrl keys, and paste.

This is still a first terminal screen. It strips terminal control codes instead of fully drawing them. The later stronger version should add a true terminal grid for richer full-screen apps.

The next slice is the stronger terminal screen:

- a true terminal grid,
- fuller terminal drawing,
- better copy/paste,
- closing the terminal cleanly when the tab closes.

A shell process means the actual command line program running behind the screen.
