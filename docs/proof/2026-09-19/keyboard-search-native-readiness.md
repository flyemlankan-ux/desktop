# Native keyboard/search journey — ready for parent-run acceptance

New script: `scripts/terminal-tabs/test-terminal-keyboard-macos.py`.

Command (using the existing environment with marionette_driver):

```
python3 scripts/terminal-tabs/test-terminal-keyboard-macos.py --app '.terminal-test/Zen Terminal Test 156.app' --label keyboard156
```

No UI launched by this worker. Python syntax compilation passes; no execution claim.

Uses a new synthetic browser profile and home. Confirms owned PID/profile/data paths before testing. Only its exact spawned process is quit/terminated; only its recorded tmux session is cleaned. Screenshots are of the owned browser through Marionette, not the desktop. No private browser data or clipboard is read.

Checks actual W3C key input for Cmd+F and Ctrl+F, terminal find instead of browser find, literal query selection, next/previous, no-match, Escape focus, command-shaped search text never creating a shell file, and subsequent real shell input. Reload and actual viewer detach/reconnect must preserve shell PID and restore focus. Captures light/dark-system-preference small-window screenshots and checks search/status controls stay within the viewport. The terminal intentionally remains dark in both system themes.

Actual xterm options are observed using a test-only constructor wrapper installed before terminal scripts load by a document observer. The wrapper calls the original constructor unchanged, capturing the instance; it does not modify product options or extract methods. Both initial and changing synthetic `ui.prefersReducedMotion` settings must reach actual matchMedia and actual xterm blink/scroll options. If this observation mechanism fails on Gecko, it is a test blocker, not evidence that production motion support failed.

Explicit not-run: OS clipboard (all-format/race-safe preservation not guaranteed), OS IME, actual screen-reader speech. DOM accessible names and live-region attributes are checked but are not called assistive-technology acceptance.

Next: parent executes against rebuilt current assets. High reasoning if native chrome shortcut routing or focus recovery fails; use focused keyboard and real app proof, not broader feature redesign. No production files changed by this slice.
