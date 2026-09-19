# Native pointer driver: read-only source findings

## Scope
No UI launch, input posting, permission change, or production edit. No complete Firefox engine source files existed in the searched local tree, so the official Firefox156 release bytes were fetched into ignored `.terminal-test/native-source156/` for inspection. Their Git blob hashes match the previously pinned engine sources:

- `nsCocoaWindow.mm`: `1f45cbe8eba39656f681d0948ad94df7230e13de`
- `nsDragService.mm`: `340a9ad81c5cb23bb7e5f927d11d5cffdde7ce70`

## Grounded driver limits
[Official Firefox156 Cocoa source](https://raw.githubusercontent.com/mozilla-firefox/firefox/FIREFOX_156_0_RELEASE/widget/cocoa/nsCocoaWindow.mm), lines403–507,2938–2960,3894–3942:
- Native test MOVE becomes `NSEventTypeMouseMoved`, not a held-button `LeftMouseDragged` event. It is delivered directly to the owned window; down/up use its NSApp event dispatch.
- The test method warps the shared cursor but does not change globally held mouse-button state. Gecko reads `NSEvent pressedMouseButtons` when constructing DOM button state. Our trusted mousedown/drag events recording `buttons=0` are consistent with this distinction.
- The AppKit drag-ended callback independently ends Gecko's drag session. It derives the final point from current mouse location, so matching final coordinates alone do not establish that our UP caused the end.

This makes the process-local driver different from a physical held-button drag. It does **not** establish why these particular native sessions ended early, nor exclude a production bug.

[Official Firefox156 drag-session source](https://raw.githubusercontent.com/mozilla-firefox/firefox/FIREFOX_156_0_RELEASE/widget/cocoa/nsDragService.mm), lines181–200,249–256: native dragging uses AppKit's dragging session and requires Gecko's saved mouse-down view. If that view was cleared by mouse-up, startup aborts. Our runs did start a native drag; that guard alone does not explain the later early end.

## More specific product-side cancellation clue
Saved-setups agent identified, and this review confirmed, `src/zen/drag-and-drop/ZenDragAndDrop.js:983–1003`. A window capture dragleave with no relatedTarget, outside the fake-browser target, is treated as leaving the window. Once native moving-tab guards pass, it calls `onBrowserDragEndToSplit(event,true)` and builds an outside-window drag image. This listener is registered at startup (`:130`) before the test's observer.

Our failed sequence records such an in-window content dragleave. Thus a diagnostic event's "before" state can already include this production capture listener's changes. A later timer attached to TabSelect cannot assign causation to TabSelect itself. The previous report's temporal observations remain valid, but selection-specific causation is unproved.

## Next bounded discrimination
High reasoning; focused native evidence only:
1. Hold the trusted native drag over the source tab without a split preview and without additional test selection. Record buttons, native session activity, any early end, and exact UP time. An early end here demonstrates a driver limitation independent of split selection.
2. During the existing edge journey, read the real outside-window drag-image wrapper presence/connection and record it with the null-related-target dragleave, chrome-relative screen position, actual window bounds, and split state. Do not replace or invoke any production event handler. Its creation would support the specific false-window-exit path.
3. Run those probes against the correctly identified compiled app when available. A clean result in an older build does not replace final-source acceptance.

No guessed new native message constants, global HID posting, forged DOM drag events, or direct split-method success should substitute for the required real gesture.

## Slice recap
We now know the driver does not emulate physical held-button state, and have a separate grounded native cleanup path to investigate. This slice only researched and documented; it did not repair or accept drag-to-split. The overall goal remains ordinary Zen tab gestures with live terminals. No scope reduction or waiver is recommended.
