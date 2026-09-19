# Project drag/drop: optional owned-process macOS mouse path

1. Current state: prior W3C drag attempts never proved a completed drop. This slice does not change that result or claim a pointer pass.
2. Changed: `test-terminal-project-workflows.py` now accepts `--native-pointer-drag`, mutually exclusive with `--pointer-drag`. It reuses `macos-test-dialogs.py`'s existing owned-PID CGEvent drag. No production changes.
3. Overall: prove a user can actually reorder a terminal among website tabs in a native folder, keeping saved shell jobs alive.
4. Not done: no UI execution, no accessibility permission requested, no screenshot/interaction with another app, no fallback DOM reorder called when a pointer attempt fails.
5. Checks: Python compilation and diff whitespace checks pass. Before dragging, the helper must have existing Accessibility permission, confirm the spawned app PID, activate/raise only its own native window, read that window's AX position/size, and agree with browser chrome screenX/screenY/outerWidth/outerHeight within two points. DOM client positions are offset using mozInnerScreenX/Y. No Retina multiplication is guessed. Mismatch fails closed. Every native mouse event is directed only to that PID; release is guaranteed by the existing helper. Afterward the test requires genuine trusted dragstart/drop/dragend, the native tab MIME type, the requested actual folder order, and unchanged shell PIDs/recipe counts. Native mousedown screen coordinates must also match calculated screen points.
6. Parent command: `python3 scripts/terminal-tabs/test-terminal-project-workflows.py --app '.terminal-test/Zen Terminal Test 156.app' --label project156-native-pointer --native-pointer-drag`. Parent runs only when UI ownership is free. Recommended reasoning high if input or geometry fails; proof actual trusted mouse completion plus order/session invariants. This source readiness is not that proof.
7. Drift: the method-only path remains clearly separate. No desired native behavior or acceptance condition was weakened to make a result pass.

## Gecko process-local experiment (not executed)
New separate flag: `--gecko-native-pointer-drag` (mutually exclusive with W3C and PID CGEvent modes).

Pinned Firefox156 official sources:
- `dom/interfaces/base/nsIDOMWindowUtils.idl`, Git blob `83313786eba285ecd6895869f9991c722c99f799`, lines428–456: `sendNativeMouseEvent(screenX, screenY, message, button, modifiers, elementOnWidget, callback)`. Screen coordinates are device pixels. Down=1, up=2, move=3; no drag message exists.
- `dom/base/nsDOMWindowUtils.cpp`, blob `3f3b4faf59409622822da3e4ee4ae57fdef05290`, lines934–975: obtains the widget from the supplied owned element and dispatches its native mouse method. Does not select another desktop app.
- `widget/cocoa/nsCocoaWindow.mm`, blob `1f45cbe8eba39656f681d0948ad94df7230e13de`, lines403–507: converts device pixels to Cocoa points, constructs NSEvent for its NSWindow, sends through its own NSApp. No global CGEventPost. It DOES move the shared system cursor; parent explicitly accepted that side effect for scheduled isolated UI testing.

Implementation checks exact owned PID and tab document, source/target bounds, live geometry and pixel scale; multiplies screen points by devicePixelRatio exactly once as required by this API. Each native dispatch is awaited via `onCompleteDispatch`, with bounded timeout. Button-up is attempted in finally. Source event capture now includes button/buttons to expose actual pressed-state behavior. It never creates a DOM drop or calls tab reordering to rescue a failed pointer attempt.

Important limitation: Cocoa maps MOVE to NSEventTypeMouseMoved, not NSEventTypeLeftMouseDragged. There is no supported dragged message constant to invent. This sequence may therefore fail to start or complete a real drag. The existing strict trusted dragstart/drop/dragend, MIME, actual-order, coordinate and saved-shell assertions remain unchanged. A failed attempt is not a pointer pass. Parent executes when UI is free; this worker only compiled Python and checked whitespace.
