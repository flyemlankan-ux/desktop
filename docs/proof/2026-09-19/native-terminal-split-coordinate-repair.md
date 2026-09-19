# Native terminal drag-to-split coordinate repair

## Observed failure and control

The native pointer owner reproduced terminal-to-content split failure in isolated runs while sidebar reorder passed. Corrected post-dispatch instrumentation showed the real trusted terminal dragover **does** reach the existing chrome tabbox listener. Its path includes the content frame message manager, browser and tabbox. Therefore a second event listener or forwarding bridge would be the wrong repair.

At the same physical pointer point, the terminal event reported content-local clientX 996 while the chrome position was 1232 (screenX 1236 minus chrome origin 4). The existing splitter compared 996 against the chrome right-edge threshold, so it did not show a preview. The ordinary remote-web control reported browser-relative chrome coordinates and showed the real right preview.

## Bounded source change

Only `onBrowserDragOverToSplit` in `ZenViewSplitter.mjs` changes. For a trusted event originating from the exact selected terminal document, with system principal and matching canonical terminal document/browser URLs, it derives a coordinate-only point from screen coordinates minus chrome window origin. Both screen coordinates and origins must be finite. All existing native tab MIME, same-window source, multiselection, workspace, split count and drag checks remain unchanged.

It does not add listeners, dispatch synthetic events, copy trust flags, call split creation directly or change terminal commands. Ordinary web events retain their existing coordinates. The original event object is not modified.

Final split completion remains native: tabbrowser dragend originates on the original chrome tab and calls `moveTabToSplitView`. The preview's leave listener is attached to its chrome vbox. Those chrome-relative paths are unchanged.

## Source proof and remaining native proof

`test-terminal-split-drag-coordinates.mjs` executes the actual handler and edge calculator. It checks the measured terminal geometry, unchanged event coordinates, ten negative identity/source cases, unchanged ordinary web behavior, center rejection and both left/right edges. It passes, as does module syntax. Independent read-only review passed. The identity/trust negatives prove that the new coordinate correction is withheld; they do not claim the unchanged upstream handler rejects every possible synthetic event at every coordinate. Actual pointer preview/drop and exact terminal-job continuity still require parent/native-owner proof after verified repackaging.

1. Where we are now: measured coordinate mismatch has a narrowly guarded source repair.
2. What changed: terminal content coordinates are translated into the browser window's coordinate system for edge detection.
3. Overall goal: real terminal tabs behave like native Zen tabs, including actual split gestures.
4. Not built here: a substitute gesture, a new drag system or a test-only split shortcut.
5. Proof checked: actual handler geometry and guards, not native final completion yet.
6. Next slice: verified app packaging, native pointer preview/drop, neighbor/session checks and ordinary-web control.
7. Drift check: do not claim a method-created split as proof of the user's real gesture.

Recommended reasoning: high. Proof level: actual owned-app native pointer sequence with trusted event/preview/drop receipts and terminal session continuity; focused source negatives first.

## Native preview confirmed; final gesture still failing

The parent rebuilt the coordinate repair. Actual terminal-edge dragging now creates the native right-side preview, confirming the measured coordinate fix affects the real gesture. Final split completion still fails: a trusted, uncancelled chrome-relative dragend arrives with dropEffect none, but the splitter has lost its accepting state. There were no Gecko JavaScript errors in the examined run.

Do not claim split acceptance from the preview. No second production change has been made. The test now records bounded before/after lifecycle snapshots for dragenter/leave/over/drop/end and TabSelect, with native document/path, both coordinate spaces, preview bounds, selected/previous/dragged tabs and splitter state. It also records animation-wait and button-release milestones. Listeners only observe; they do not replace production handlers or dispatch fake events. Failure saves a separate `-split-lifecycle.json` receipt. Syntax passes; parent owns the next actual UI run.

The diagnostic must distinguish dragleave cancellation, selection/location cleanup and normal final commit consumption before choosing any further repair.
