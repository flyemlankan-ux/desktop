# Minimal native polish implementation

Implemented source changes; native screenshots and packaged app acceptance pending. No commit or UI launch.

## Changes

- `ZenTerminalTabs.mjs`: `markTerminalTab` uses ordinary `gBrowser.setIcon` with the already shipped `chrome://browser/skin/zen-icons/selectable/terminal.svg`. Existing `tab.zenStaticIcon` wins; the default icon is not recorded as a custom choice.
- `zen-terminal-tabs.css`: removed extra `›_` pseudo-element and blanket icon/overlay suppression. Only the default SVG gets native context-fill styling. Native overlays and custom icons are not hidden.
- `zen-terminal-page.css`: plain neutral background, no green gradient; status uses compact 11px system text, wrapping and native focus accent. Decorative second prompt is hidden. Real terminal text retains xterm's configured monospace font. Messages, persistence warnings, errors, restart/reconnect controls and live-region semantics remain intact.
- `prefs/zen/updates.yaml`: disable stock **Update Complete** notification by default for this manually built fork. This does not implement or claim an automatic updater.

## Proof run

- New `node scripts/terminal-tabs/test-terminal-native-polish.mjs`: pass. Executes the real marker method with default/custom icons; asserts no duplicate icon or overlay suppression, packaged icon manifest, update preference, compact wrapping status and retained accessibility markup.
- `node scripts/terminal-tabs/test-terminal-polish.mjs`: pass.
- `node scripts/terminal-tabs/check-terminal-tabs.mjs`: pass.

These are source/behavior tests, not screenshot acceptance. Parent must re-overlay/repackage. The existing local overlay builder does not compile YAML defaults; it must explicitly propagate the changed updater notification default before testing it. Final actual build must carry this preference too.

## Standalone saved-setup test fixes

`test-terminal-saved-setups-macos.py` uses plain session names for tmux `display-message` (the exact-target equals prefix is unsuitable there). Added native Settings/custom-element readiness, two animation frames and the existing main Mac proof's short settling delay before Add/Edit. Parent's first run reached four passing setup checks; a later run hit initial Settings readiness before showing the dialog. Neither failure is recorded here as successful complete native acceptance.

## Deferred address-bar hook, precisely

No address-bar behavior changed. Proposed follow-up source integration points:

- `src/browser/components/urlbar/content/UrlbarInput-mjs.patch` already patches the native URI setter at upstream hunk `@@ -846,6 +862,10 @@` (options include `hideSearchTerms` and `isSameDocument`). A dedicated presentation state should be derived here from the selected browser's exact terminal URI and tab identity, not assigned by an asynchronous timer.
- Same patch's `startLayoutExtend()` and native `endLayoutExtend()` hunks near upstream lines 3030/3053 are the focus/close boundaries; the presentation-only label must yield immediately to real editable URL state there.
- Existing `zenStrippedURI` getter derives copy/share from real currentURI/userTypedValue. Do not alter it to copy a friendly label or fake site URL.
- `ZenUIManager.mjs` native close path calls `setURI`, `handleRevert`, and `updateTextOverflow`; a terminal presentation state must remain consistent through this route and ordinary web-tab switching.

This merits a separate reviewed slice with typed URL/Cmd+L/Escape/copy/tab-switch tests. It is intentionally not implemented as CSS camouflage or an overwritten input value in this polish slice.

## Remaining limitations

No visual acceptance yet for light/dark, compact, custom icons, folder/pin/split layouts, narrow state strip or native update notification default. Custom strings remain English. Full xterm light-theme palette, keyboard-focus restoration after editing steps, and OS folder-picker sheet interaction remain separate pending work. No personal profile changes.
