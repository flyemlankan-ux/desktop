# Native Firefox text-input integration — ready, not browser-run

New files:
- `test-terminal-text-input-macos.py`
- `terminal-text-input-receiver.py`

No browser or OS UI launched for this slice. No clipboard access, operating-system input-source changes, VoiceOver activation or product edits.

## Actual Firefox156 mechanism

The script instantiates the real `@mozilla.org/text-input-processor;1` service, calls `beginInputTransactionForTests` on the owned terminal window, and uses pending composition clauses, flush, commit and cancellation. It does not create and dispatch synthetic DOM composition events. A keyboard-event description is passed to the actual processor for a composing Enter, as supported by Firefox's own interface.

Pinned primary sources inspected:
- [Firefox156 nsITextInputProcessor.idl](https://raw.githubusercontent.com/mozilla-firefox/firefox/FIREFOX_156_0_RELEASE/dom/interfaces/base/nsITextInputProcessor.idl)
- [Firefox156 EventUtils.js](https://raw.githubusercontent.com/mozilla-firefox/firefox/FIREFOX_156_0_RELEASE/testing/mochitest/tests/SimpleTest/EventUtils.js), `_getTIP` and its use of `beginInputTransactionForTests`.

## What the prepared test checks

1. Fresh isolated Firefox156 app/profile/home/app-data; exact owned PID and directory checks.
2. A genuine terminal startup command launches the bounded raw-input receiver inside its actual PTY. The receiver never executes incoming text and restores terminal modes on normal exit.
3. Composition updates send no premature bytes. Commit sends the exact UTF-8 sequence for CJK, emoji and a combining accent, once only. The observed composition events must be trusted.
4. Cancelling a second composition adds no PTY bytes. A short bounded quiet window catches deferred duplicate output.
5. Actual browser key actions for Option-b must reach the PTY as one ESC+b Meta sequence, matching the product's Option-as-Meta behavior. No OS keyboard layout is changed.
6. Open terminal search through Command+F, compose the Unicode search query using the same real processor, and require a real matching selection in scrollback.
7. Send Enter through the processor while composition is still active. Require trusted composing-key observation, unchanged search match selection and unchanged shell bytes.
8. Commit the search composition and use actual Shift-Left key actions to select text inside the search input. Shell bytes remain unchanged.

The receiver has a 120-second lifetime and 64KiB input limit. It writes only known synthetic test bytes into the synthetic home. The app and exact test session are cleaned up even on failure. No kill-server or unrelated process control.

## Proof completed without browser UI

- Both Python files parse; test help works.
- The installed Marionette key constants used by the script exist.
- The receiver was exercised through an actual local pseudo-terminal, without a browser or GUI: exact Unicode and ESC+b bytes were captured, then EOT produced a clean exit. This proves the receiver, **not** browser composition.
- Actual Firefox/xterm composition integration remains pending the parent's native run.

## Run, parent-exclusive UI slot

```sh
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 -B \
  scripts/terminal-tabs/test-terminal-text-input-macos.py \
  --app '.terminal-test/Zen Terminal Test 156.app' \
  --label text-input156-1
```

Do not report a pass as actual macOS Japanese/Chinese input-source, candidate-window, dead-key, physical Option-key layout or VoiceOver proof. This is **Firefox text-input integration** plus real PTY bytes. Those OS-level acceptance journeys remain separate.

## Slice recap

1. A real browser-service composition journey is prepared.
2. Added exact-byte receipt, cancellation, composing-Enter isolation and keyboard-selection checks.
3. Overall goal is terminal tabs that accept normal text safely and predictably inside Zen.
4. No product changes, browser-run pass or macOS input-method claim.
5. Syntax/help and the standalone PTY receiver passed; native browser integration is still pending.
6. Next: parent schedules the native run and reports any failure before production changes.
7. Drift check: trusted Firefox composition is not renamed into a claim about the user's actual OS input method.

Recommended handoff: high reasoning for Unicode/composition failures; proof level actual isolated app, trusted processor events and exact real PTY bytes, with OS input-source proof kept separate.
