# Compiled 0c2b163 native acceptance — bounded evidence

## What passed
Inspected `compiled0c-main-macos-results.json`: **27 checks, all pass** against `.terminal-test/compiled-0c2b163/Zen Terminal.app`, using synthetic profile/app-data (`.terminal-test/mac-b6e038d6`). This is the actual compiled package, not the local resource-overlay test app.

Checks cover actual engine/package profile identity, clean first launch, default Terminal setup, website refusal of privileged terminal URL, invalid recipe rejection, ordered editor/compact layout, actual Settings creation and saved-terminal menu, keyboard/Ctrl-C/editor input, both installed CLI version starts, window resize, duplicate-view lifetime, rename save/cancel, reload/relaunch/name restoration, actual browser crash recovery without repeating startup, and last-tab session cleanup. CLI version checks do not establish authenticated or paid agent workflows.

## Native dialogs did not pass
Inspected `compiled0c-native-dialogs-results.json`, `.terminal-test/compiled0c-native-dialogs.log`, the saved owned AX-tree receipt, and the existing owned-browser failure screenshot. One ownership/trust check passed; the test then failed finding the actual picker Cancel button. No picker Cancel/Choose/Save or private-alert pass follows that failure.

The saved AX tree contains only `AXApplication` (Zen Terminal) and `AXMenuBar`, no exposed window, sheet or buttons. Focus logs report PID9332 and the expected app bundle; the final AX diagnostic reports frontmost=false. Recent -25212 errors concern absent AXDescription/AXValue attributes, not proof that Accessibility permission was refused. The existing browser screenshot shows the Settings editor; Marionette's browser screenshot does not establish whether an external native panel was visible. Gecko log contains GPU helper connection errors, but no clear file-picker failure reason. Product failure versus driver visibility is unresolved.

## Read-only driver audit
- `OwnedAppDialogs.activate()` sets AXFrontmost but returns when AXWindows is merely nonempty. It does not verify foreground state or exact focused-window identity. This is weaker than the ownership-checked pointer driver.
- Root traversal chooses AXWindows **or** AXChildren, rather than observing both. Descendants use only AXChildren. A separately exposed AXSheets or AXFocusedWindow branch can be missed. Broader traversal must remain owned-PID-only, cycle/node bounded, and must not silently authorize a separate system process.
- `dialog_button()` treats missing AXEnabled as eligible, although the proof wording says enabled. A future driver hardening should require known-enabled state or explicitly report uncertainty.
- `enter_picker_folder()` relies on English accessible names and PID-targeted shortcuts; neither ran here. It should not be blamed for a failure that occurred before it.
- Settings Save uses a script-triggered click, unlike the real AX Cancel/Choose operations. Label its proof as native Settings save activation, not physical pointer input.

## Next and limits
Parent owns UI. Recommended next: high reasoning for a narrowly instrumented owned-PID focus/AX-tree comparison, then actual native controls. Do not toggle permissions, broaden to unrelated processes, or replace picker acceptance with a mocked response. A separate private-only test can establish private refusal independently, but cannot pass the picker case.

This report accepts only the inspected 0c2b163 package journeys. It does **not** establish newer drag-coordinate fixes, successful drag-to-split, migration, or final release acceptance. The slice changed this report only; no UI launch or production/test edits by this reviewer. Overall goal remains a separate Zen-native terminal app that preserves the user's browser experience without touching personal data during testing.

## Bounded helper repair (not a native-dialog pass)
Parent authorized a test-helper-only repair after the read-only review. `macos-test-dialogs.py` now unions AXWindows/AXChildren/AXSheets and the focused window; deduplicates by CFEqual; preserves depth/node bounds; skips an external-PID branch before reading its attributes; requires a positively enabled button; and verifies actual foreground state plus an owned focused AXWindow that matches an exposed owned window before returning from activation. It does not claim a rectangle match without browser geometry, traverse another process, change permissions, or fabricate a panel.

New `test-macos-dialog-ownership.py` runs without any real app or Accessibility calls. **Six tests pass**: union/cycles/foreign exclusion; node limit; unknown enabled refusal; false foreground refusal; foreign focused-window refusal; exact owned-window success. Python syntax and focused diff checks also pass. Files were released for parent-controlled native retry. This helper repair does not turn the failed Cancel journey into a pass; actual picker controls remain unproved until a new native receipt succeeds.


## Further compiled0c tests

- compiled0c-saved:9passes, actual saved folder/recipe workflows; nativepicker excluded.
- compiled0c-navigation:12passes,2not_run (URLdrop/non-tmux notice).
- compiled0c-folders:8passes, mixed nested Delete/Undo and explicit restart; native-method fixture/setup/workspace removal labelled.
- compiled0c-native-dialogs-v2: stillfailed locating actual ownedCancel after helper traversal/activation repair; correct separate bundleforeground observed at trigger. Not a passing picker.

These four successful native suites contain56pass checks total (27+9+12+8), not56 independent features or whole-release acceptance. Full latest-source replay remains pending. Main terminal screenshot inspected: real Zen sidebar/tab and full terminal; screenshot alone does not establish all theme/scale/interaction polish.
