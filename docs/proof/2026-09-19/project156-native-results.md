# Firefox156 mixed-project native integration results

Actual app: disposable `.terminal-test/Zen Terminal Test 156.app`, official156
engine plus current source overlay. NOT a fresh source-built final release package.
Synthetic profiles and test-owned processes only.

## Native-method workflows: 11 passing checks
Receipt: `project156-agent-methods-project-workflows.json`.
Log: ignored `.terminal-test/project156-agent-methods.log`.
Screenshot: `project156-agent-methods-project-workflows.png`, inspected.

The previous reorder test used removed Firefox155 property `_tPos`. Firefox156
Tabbrowser.sys.mjs documents tabIndex as position in gBrowser.tabs and uses tab.index.
Test now passes `gBrowser.tabs.indexOf(projectWeb)` to real gBrowser.moveTabTo.
Exact membership and desired order assertions were retained. No production change.

Passing journeys: two independent jobs/recipes once; mixed folder select/collapse;
native reorder; whole folder workspace move; mixed split + actual resize reaches
shell; unsplit; real second native window mirrored tabs; close-window retains jobs;
close last tab destroys matching session only. PID and recipe counts checked.

Screenshot has native terminal icon and full terminal surface. Raw internal address
remains visible; this is a polish gap, NOT visually accepted. Folder label was New
Folder because test supplied options.name while actual upstream API wants label.
Script corrected to label for future runs; no claim folder-renaming UI was tested.

## Actual pointer reorder: still failing, not waived
Logs: `.terminal-test/project156-agent-pointer.log` and `-pointer-v2.log`.
Failure receipts/screenshots retained under project156-agent-pointer* names.
Second attempt used a point8px above the web tab center, focused owned window, and
1000ms drop pause rather than2px top edge; same unchanged tab order.

Observed real trusted mousedown, dragstart and dragover. Transfer types included
application/x-moz-tabbrowser-tab and text/x-moz-text-internal. No drop or dragend
was observed after WebDriver pointerUp and release. Screenshot shows a lingering
drag placeholder. Captured dragover dropEffect values were none at capture phase;
this does not prove their values after native handlers ran.

Cannot yet distinguish Mac native-drag/WebDriver release behavior from a native
browser defect. Both attempts remain FAIL, not rewritten as method-based acceptance.
Next bounded investigation should compare an all-web same-folder pointer reorder
in pristine official156 and use a documented native-input release path if WebDriver
cannot finish OS drag. Do not fake a drop event or modify ordering directly and call
that pointer proof. Parent owns UI scheduling; no new app run without coordination.

All owned browser processes quit and generated tmux sessions cleaned; UI released.
Reasoning high; proof actual scoped native input + upstream baseline, then final
packaged regression. No personal data or original Zen process touched.
