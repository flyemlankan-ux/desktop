# Native drag-to-split: real input, unresolved acceptance

## Where we are
The optional `--gecko-native-drag-to-split` journey is implemented in `test-terminal-project-workflows.py`. It requires the existing `--gecko-native-pointer-drag` flag. Three actual isolated overlay runs failed; **drag-to-split is not accepted**. The original trusted reorder checks remain unchanged and passed before each split attempt.

## What changed
Test only. The new gesture sends native own-window mouse down, a threshold move inside the source tab, then right-edge moves. It waits for a real native split preview and trusted native-tab dragover before release. It never invokes `splitTabs` in this optional path, synthesizes a DOM drop, or changes a production handler. It checks actual mixed split membership, live shell identity, and the existing resize/unsplit/window lifecycle checks if the gesture succeeds. Dispatch remains exact owned-process/AX-window verified, with no global HID posting. The shared cursor moves as already authorized.

## Source and proof
`src/zen/split-view/ZenViewSplitter.mjs` registers `onBrowserDragOverToSplit` on `#tabbrowser-tabbox` (lines 130–136), builds the native edge preview (lines 325–424), and commits through `moveTabToSplitView`. `src/browser/components/tabbrowser/content/drag-and-drop-js.patch` calls that method from uncancelled native dragend when dropEffect is `none`. Therefore the added split check deliberately requires trusted uncancelled dragend, not a DOMdrop that this native path does not use. The independent reorder still requires trusted dragstart/drop/dragend, actual drop MIME, and actual final order.

Receipts/logs: `split-pointer156{,-v2,-v3}-project-workflows.json`; `.terminal-test/split-pointer156{,-v2,-v3}.log`.
- First attempt leapt directly from tab into content: only mousedown; no dragstart. Test now initiates movement inside the source tab first.
- Second attempt produced real start/edge-over/end, but source tab detached after unsupported drop, masking timeout with the connected-tab dispatch guard. Test now uses stable owned tab-container widget for the split dispatch only; process/document/connection guards remain.
- Third attempt gives the relevant failure: trusted dragover with `application/x-moz-tabbrowser-tab` at intended right-edge screen position. Event target is `div` in terminal content, `gBrowser.tabbox.contains(event.target)` is false, splitter `_canDrop` remains false, no fake-browser preview is created. Timeout releases the owned mouse and fails. Native dragend follows; no successful split claimed.

This suggests the privileged terminal page's event path differs from ordinary remote web pages. It does **not** yet prove which production change is correct. In particular, event client coordinates are content-local in this receipt; forwarding them unmodified to a chrome-relative handler would be wrong.

## Overall / not built
Overall target remains Zen-native terminal organization. No production drag handler was changed. No compiled-product result, ordinary-web comparison, or repaired terminal drag-to-split is claimed. Exact owned process and scoped shell cleanup ran; original Zen and personal profiles were not touched.

## Next slice
High reasoning, focused native proof: compare ordinary web source and terminal source drag paths using the same owned-window input, inspect event retargeting, then review a narrowly scoped terminal/native splitter integration fix with security guards before editing production. Preserve MIME, exact source/window identity, and coordinate conversion. Repeat actual gesture after any fix, including website-only behavior and rejected external payloads.

## Drift check
This is a real user gesture gap, not an excuse to replace pointer proof with direct split methods. Existing method-based split proof remains valid but does not close this acceptance item.

## Follow-up control: coordinate mismatch, not missing propagation
Parent requested a controlled web target with the same terminal source and screen-edge gesture. Added explicit `--split-web-target-control`: after a real trusted terminal dragstart, the test selects `projectWeb` by native browser method before crossing into content. This is a diagnostic state change, **not** a claimed normal user journey or complete split acceptance.

Capture-time `queueMicrotask` inspection happened before later event listeners. Split-only diagnostics now wait a zero-delay task to inspect native effects after dispatch; composedPath is saved during dispatch. Existing reorder behavior is unchanged.

- `split-pointer156-webcontrol-v2`: actual browser-element target in browser.xhtml, tabbox capture hit **1**, real right-side `zen-split-view-fake-browser` preview and dropEffect none. Split itself did not finish; this selection intervention changes the native previous-tab state. No split pass claimed.
- `split-pointer156-terminal-path`: actual terminal document `div` target, but composedPath **does include** `ContentFrameMessageManager`, browser, tabpanels, tabbox, chrome window. Tabbox capture hit **1**. Thus the earlier propagation hypothesis is superseded: the event reaches the native listener. There is no preview.
- Terminal drag event coordinates are content-local: the edge event's clientX is about 996 while the same screenX 1236 corresponds to chrome clientX 1232 (chrome origin 4). The source handler directly compares event.clientX/Y to chrome tabbox rectangles. The web control retargets to a browser element and supplies chrome-relative coordinates, creating the preview.

Next fix review should consider **terminal-only coordinate normalization in the existing native handler**, not a second forwarding listener. Require exact selected terminal document/browser ownership and trusted native tab source, preserve all native drop guards and normal website behavior. The new test still fails closed and will exercise the production fix without replacing native split methods. UI ownership explicitly released to parent after these runs. No app rebuild or production changes by this agent.

## Bounded driver investigation after coordinate repair
Parent rebuilt the overlay with the separately reviewed terminal-coordinate fix. This agent changed only the project test, then ran three further isolated comparisons under exclusive UI ownership:

- `split-pointer156-sequence`: real corrected right-edge preview appears. Native dragend at 6650.8 ms precedes explicit native mouse-up request at 6805.2 ms. No earlier button-up appears in the recorded dispatches.
- `split-pointer156-tracking`: driver now waits for real native dragover tracking after dragstart, sends the content-edge MOVE only once, then observes rather than repeatedly moving. Native preview still appears; dragend at approximately 6476 ms precedes explicit UP at 6628.7 ms. Thus queued repeated moves do not explain or repair the failure.
- `split-pointer156-websource`: optional `--split-web-source-control` drags the actual ordinary web tab toward the previously selected terminal, with no mid-drag test selection. This reverses the source/target roles while keeping the same native gesture. Native preview appears; native selection changes to previous terminal; trusted uncancelled dragend at 5944.7 ms precedes explicit UP at 6081.6 ms. The remaining failure is not specific to terminal as dragged source.

The test now records each native dispatch request/completion timestamp and explicitly rejects a dragend occurring before its intended release, including after preview animation. The existing trusted native MIME, edge preview, geometry, uncancelled end, split membership and shell-lifetime checks are not removed. Readiness still does not count as split acceptance. The source/control fixtures remain disposable, and the original browser is untouched.

The trace shows native tab selection while preparing the preview, then `_draggingTab` clears and `_canDrop` becomes false before native dragend. Source inspection shows `onTabSelect` invokes `onLocationChange`; native cleanup and animation also manage these fields. Observation alone does not establish which call caused the first reset. No production handler was replaced, wrapped or patched to fabricate a successful result, and no global input fallback was used.

**Outstanding:** distinguish a native own-NSApp simulation limitation from native split cleanup/selection behavior on the fully compiled final app. The repeatability of early dragend in both directions warrants source-level diagnosis, not another guessed timing delay. A separately built older installer exists but does not contain the final source fixes, so it is not interchangeable acceptance evidence. UI ownership was explicitly released to the parent after this bounded investigation. Python compilation and focused whitespace checks pass.
