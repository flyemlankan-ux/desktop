# Mixed nested folders and workspace lifecycle — prepared native journey

New script: `test-terminal-folder-lifecycle-macos.py`. Syntax and help pass. No browser launched; production unchanged.

## Source inspected

- Firefox156-aligned `ZenFolders.mjs`: actual `zenFolderActions` handlers map Rename and Delete to the folder's methods. `createFolder` pins its members and creates the native placeholder tab.
- `ZenFolder.mjs`: rename invokes Zen's real inline name editor; Delete recursively removes placeholder tabs then calls the browser's group removal.
- Upstream `browser_folder_subfolder.js`: nesting uses `parent.tabs[0].after(subfolder)`. The new test follows that native-method fixture setup and does not claim pointer drag proof.
- `ZenUIManager.mjs`: the real inline rename input is `tab-label-input` and commits on Return.
- `ZenSpaceManager.mjs` / `zen-sets.js`: workspace rename uses the same inline editor; `removeWorkspace` removes only tabs owned by that workspace and excludes Essentials. `contextDeleteWorkspace` adds a native confirmation before that method.
- Packaged SessionStore: `undoCloseTabGroup(sourceWindow, groupId, targetWindow)` provides the real closed-group restore operation.

## Test sequence and honest interaction labels

1. Launch an isolated synthetic Firefox156 fork profile with explicit home/app-data and actual PID/path checks.
2. Create one saved terminal setup whose harmless startup command appends one line to a synthetic counter file.
3. Start one neighbor job in the initial workspace. Create a second workspace with two more jobs using the **same setup**, plus two ordinary data-URL web tabs. This makes over-broad container-based cleanup detectable.
4. Create two mixed folders and nest one inside the other using the same native placement as upstream tests. Label: **native-method setup, not pointer drag**.
5. Right-click the actual parent folder label through browser pointer actions, click its visible Rename menu item and type into the real inline input. Verify folder name and unchanged jobs/counter.
6. Open the actual workspace popup using its native method, click the visible Rename item and type into the real inline input. Label: **actual menu item/input, popup discovery not proved by pointer**.
7. Right-click the parent folder and click its actual Delete item. Require nested web and terminal tabs to disappear, both intended jobs to stop, and the same-setup neighbor job to remain.
8. Invoke actual SessionStore Undo for the closed group. Label: **native-method Undo, not a menu-click claim**. Require nested organization and both terminal tabs to return, but both jobs to remain ended with an explicit Start again button. The startup counter must stay unchanged.
9. Click the actual Start again button on one restored terminal. Require exactly one additional startup execution. The other restored terminal must remain stopped and the neighbor must still run.
10. Call the real workspace deletion method. Require only its restarted job to stop; the original workspace/job survives. Label: **native-method deletion consequences; native confirmation not exercised or mocked**.

All fallback actions are explicit in the report. If an intended native menu cannot be opened or clicked, the test fails; it does not secretly substitute a method call and call it a UI pass. A failure to restore nested groups or recover safely is reported without changing production in advance.

## Run when parent owns the only UI slot

```sh
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 -B \
  scripts/terminal-tabs/test-terminal-folder-lifecycle-macos.py \
  --app '.terminal-test/Zen Terminal Test 156.app' \
  --label folder-lifecycle156-1
```

Use a new label. Failure cleanup targets only the Popen-owned browser and exact generated session names; no kill-server, personal profiles, original browser or clipboard access.

## Remaining boundaries

Prepared only: no native sequence has run in this slice. Pointer drag nesting, discovery of the workspace popup, menu-driven Undo, native workspace-delete confirmation, Essentials survival and multiple-window folder behavior are not covered by this script. Previous tests or future acceptance must cover those separately. The final compiled app should repeat this journey before release.

## Slice recap

1. A missing destructive-action acceptance journey is now runnable.
2. It checks nested mixed folders, rename, exact cleanup, honest Undo and explicit restart.
3. Overall goal remains natural Zen organization without losing control of terminal work.
4. No production fix, UI pass or untested interaction claim was added.
5. Syntax/help and source-method checks passed; actual native behavior remains pending.
6. Next: parent runs it after current UI queue, investigates any real failure before changing production.
7. Drift check: methods are labelled as methods, menus as menus, and restored terminal tabs must not silently rerun commands.

Recommended handoff: high reasoning because deletion/Undo affects real running work. Proof level: actual isolated native browser plus real jobs and startup counters, with neighboring-job preservation.

## Actual parent run and Undo diagnosis

`folders156-v2.log` passed nested setup, actual folder rename, actual workspace rename and actual recursive folder Delete with exact-job cleanup/neighbor preservation. It then failed in `SessionStore.undoCloseTabGroup` at the actual156 packaged line8360: `group.select()` received an undefined group. The failure remains evidence, not a pass.

Read the exact current test app's packaged modules, not an older extracted build:
- `SessionStore` successfully finds the requested closed group; missing-group lookup would throw a different error earlier.
- `#createTabsForSavedOrClosedTabGroup` passes the group's saved tabs and one group descriptor into the browser's restore routine, restores the tabs, and returns `tabs[0].group`.
- `Tabbrowser.createTabsForSessionRestore` creates a group only when a tab's saved groupId matches one of the supplied group descriptors.
- `SessionWindowUI.restoreLastClosedTabOrWindowOrSession`, the real Cmd+Shift+T path, chooses the last closed transaction. Its `undoCloseTab` calls the same `undoCloseTabGroup` method when a lastClosedTabGroupId exists.

Therefore this is not established to be a wrong test API. Nested tabs referring to a different group from the supplied parent descriptor, or later restore-time ungrouping, are plausible causes. The existing failure does not distinguish them.

The test now uses **actual Cmd+Shift+T** so the browser, not the test's parent ID assumption, chooses the normal user Undo transaction. Before pressing it, the script records only synthetic closed-group IDs, member group IDs, pin/placeholder flags and terminal ownership values. On failure it records the resulting synthetic folder/tab structure. Syntax passes; no rerun or production repair occurred here. Earlier wording describing Undo as a direct-method case is superseded by this real-shortcut diagnostic. The direct-method nesting/workspace-delete boundaries remain unchanged.

Next handoff: high reasoning, actual native diagnostic with pre/post transaction evidence. Do not suppress the exception or flatten nested folders to make the test pass. If normal user Undo reproduces the failure, repair the real restore path only after identifying the missing relationship.

## Corrected diagnosis after real-shortcut run

The parent's `folders156-shortcut` run again passed the first four stages. Its post-failure snapshot contains **both terminal ownership receipts**, but their `zen-terminal-session-id` attributes are absent because the restored tabs are lazy/pending. The previous test incorrectly treated that as no restored tabs. It now discovers them through persisted ownership receipts, selects each to load its page, and then requires the honest ended/Start again state and unchanged recipe counter.

The empty `groups` diagnostic also had a concrete source explanation: actual Firefox156's `getClosedTabGroups` false/all-windows branch checks `sourceOptions.sourceWindow.closedGroups`, although the argument is a DOM window and the actual data is stored internally. The test now uses `closedTabsFromAllWindows:true` within its single-window, isolated test process. This reads real closed records, not a guessed `_closedGroups` property. It does not touch the unrelated original Zen process.

The corrected script records terminal-restoration safety separately before asserting structural success. Structural success now explicitly requires two **Zen folder nodes** with the correct child-to-parent relation, not merely generic tab-group IDs. Failure diagnostics include node tags, pending flags and synthetic page status.

A separate optional control, `test-web-folder-undo-macos.py`, reproduces native folder Delete and actual Cmd+Shift+T with **ordinary web tabs only**. It starts no terminal jobs and records the closed/restored group structure. Syntax/help passed; native control run pending.

### Source-grounded repair direction, not implemented

The current TabGroupState patch adds pinned/essential/split-view properties but no nested Zen-folder snapshot. Full-window restoration separately calls `gZenFolders.restoreDataFromSessionStore(winData.folders)`. Closed-group restoration supplies only one parent group descriptor and does not call that folder reconstruction path. This is a concrete difference, but the exact affected saved IDs must be confirmed in the corrected native evidence before choosing a repair.

If confirmed, a repair should retain the closed folder subtree's own descriptors and Zen metadata, restore all referenced child groups, then rebuild their Zen-folder relationships using the existing restoration path. It must not capture unrelated folders, flatten children, replay terminal recipes or weaken session ownership. Production remains unchanged by this investigation.

## Bounded repair implemented; native proof pending

The parent confirmed the same structure loss with ordinary web tabs. The repair now captures only the deleted folder's own subtree before removing placeholder tabs. Closed history keeps its names, icons, workspace, sibling anchors and nested group descriptions. Undo supplies all group descriptions to Firefox, then uses Zen's existing folder reconstruction. It returns the restored root rather than assuming the first tab belongs to it.

Collision handling happens **before** creating tabs: saved metadata is cloned, IDs already present in the target window are replaced, and matching cloned tab/group/parent/placeholder references are updated. Existing folders and saved terminal ownership receipts are not modified. Missing workspaces fall back to the active workspace. Original first position is preserved when its saved position was the beginning. Originally empty folder records are retained rather than removed as orphan groups; empty restoration creates inert blank placeholders, not commands.

Source proof: `node scripts/terminal-tabs/test-folder-undo-subtree.mjs` passes five focused groups, including exact production-method execution and strict fuzz-zero application of the full SessionStore patch to the pinned Firefox156 fixture. Both Zen modules and the patched SessionStore pass syntax checks. This is not native browser proof. Empty-only root deletion, collision behavior, order, split-view and cross-window details still need native checks.

1. Where we are now: the defect has a source repair and focused checks.
2. What changed: Undo now carries and reconstructs the deleted nested folder structure.
3. Overall goal: normal Zen organization with real terminal tabs and safe job lifetimes.
4. Not built here: a new folder interface, automatic terminal restart, or broad SessionStore rewrite.
5. Proof checked: own-subtree capture, direct placeholders, cleanup on error, all child descriptors, collision remapping, unchanged receipts and ordinary-group behavior, empty restoration and workspace fallback.
6. Next slice: parent rebuilds the exact SessionStore overlay, then runs actual web-only and mixed Delete/Undo journeys.
7. Drift check: keep upstream folder behavior; do not weaken nested-folder checks or turn restored terminals into silent command execution.

Recommended reasoning: high. Recommended proof: isolated native app, actual Delete and Cmd+Shift+T, exact neighboring-job survival and startup counters; include empty folder and ID-collision cases before claiming complete folder Undo support.

Follow-up source tests now include actual reconstruction orchestration with a minimal DOM, preserving the first sibling and inert anchor; actual cleanup retains originally empty folders but removes exhausted real-tab folders and ordinary empty groups. Seven focused test groups pass. Parent native web-only repaired run passed all four stages; mixed run passed through nested Undo plus no command replay, then encountered a test-side stale content-button reference which parent is correcting. No broader native claim follows from that test interruption.

`test-web-folder-undo-macos.py --edges` adds actual Delete/Undo cases for empty parent and empty child, first-root order, a synthetic same-ID existing folder, and missing-workspace fallback. Folder creation/ID stress/workspace removal are labelled native-method fixtures; menu Delete and Cmd+Shift+T are real actions. Syntax passes; edge run is pending. Failure diagnostics retain actual closed history and synthetic live folder metadata.

## Empty-folder native failure and follow-up candidate

`web-folders156-edges` passed the baseline nested-web case, then failed empty parent/child Undo. Its failure snapshot had no closed group and no last group. Reading the actual browser close method explained why: Zen deleted every inert placeholder first, detaching an empty root before its group-close request could reach SessionStore. Even if recorded, no real closed tab existed to add the normal Undo action.

The follow-up keeps an empty root connected through the native group-close request, then removes its inert placeholders without separately recording them. The existing closed-group record gets a unique action ID; normal Undo resolves that record without making a fake tab or job. Empty records are bounded, removed when history is disabled/limited, cleared by private/global history clearing and forgetting, and given fresh action IDs when session history is restored. The valid last-empty-group fallback supports the normal shortcut after restart without pretending an action stack was persisted.

Eleven focused groups pass, including actual close/lookup/forget/private-purge/preference-change methods and zero history limits. Syntax and strict patch application pass. Native empty-folder rerun is still pending; source review requested before rebuild.

Independent native edge runs: first-root ordering passed. Initial collision failure was an insufficiently loaded synthetic page fixture; after waiting for the actual data page/title before flushing, collision passed without any production change. Missing-workspace Undo remains under investigation with real pre-Undo history snapshots; no unsupported claim that this edge works.

## Native empty pass; nested close-order defect found and repaired

The rebuilt empty-folder candidate passed actual empty parent/child Delete and Cmd+Shift+T (`empty-v2`). A subsequent baseline exposed a different genuine ordering defect: closed history contained the parent transaction, but `lastClosedTabGroupId` named the child when its tab happened to be collected last. Earlier ordering had hidden this.

The narrow fix supplies a separate root `closedInTabGroupId` to the native collection/save path. Each saved tab's `state.groupId` still names its true child folder. This separates which transaction Undo should open from where the restored tab belongs. Pending final tab updates retain the same root transaction metadata. Normal groups keep their original behavior.

Twelve focused groups pass, including both root/child collection orders and an initially-unsaved tab whose final update arrives later. The native web script adds `--child-last` to deliberately exercise the reverse ordering via labelled method-level placement; Delete and Undo remain real user actions. Native proof of this follow-up is pending rebuild. The missing-workspace case remains separately under diagnosis; do not treat the baseline stall as a workspace repair.

## Missing-workspace no-op close diagnosis

The after-workspace-removal diagnostic proved the saved root group and tab remained intact, and `prepareClosedFolderState` correctly selected the surviving workspace. But `lastClosedTabGroupId` became null before the shortcut. This was not a missing-workspace conversion error.

Actual source cause: deleting an already-empty workspace calls `gBrowser.removeTabs([])`. Tabbrowser's existing Zen placeholder filter also converts placeholder-only requests into an empty list. The method then reset the previous Undo transaction despite closing no real tab. The narrow fix returns immediately when the filtered list is empty, before history reset or last-window close logic. Normal and mixed real-tab close requests remain unchanged.

The complete Tabbrowser production patch applies fuzz-zero to newly saved official156 source, with verified Git blob and SHA256 in the existing fixture receipt. `test-terminal-empty-close-history.mjs` executes the actual patched method: empty and placeholder-only calls do not reset history; ordinary and mixed calls still enter the original history path; an empty request does not close the browser window. This test and syntax pass. Native missing-workspace rerun is pending the parent overlay rebuild.

Parent native results before this follow-up: reversed-order baseline, empty subtree, first position and collision pass; actual empty-history restart and actual history-clear notification pass. These passes do not waive the still-failing missing-workspace case.

## Final standard native acceptance: 11 passes

The parent's rebuilt no-op-close fix passed the complete standard native web suite: all 11 stages, including nested Undo, empty parent/child, first-root order, same-ID collision, missing-workspace fallback, empty-history quit/relaunch, history clearing and disabled history. These are actual isolated browser results, not inferred from source tests.

A separate `--child-last` rerun then stopped before Undo with no closed group and no last-group marker. This differs from the earlier proven child-transaction bug, which had a valid parent closed record and an incorrect child marker. The baseline fixture had not yet waited for both real data pages to finish loading before flushing their state; the edge fixture already had that safeguard. Parent is adding the same readiness check and rerunning. Treat this latest interruption as a fixture diagnostic, not an established new source defect. No production changes are justified by it unless the corrected run supplies further evidence.

Current handoff: production remains released and unchanged. Parent owns the baseline readiness correction and native rerun. Recommended reasoning: high for any new close/Undo change. Proof: actual loaded pages, saved closed-history snapshots, real menu Delete/Cmd+Shift+T, and unchanged exact terminal job safety. No personal-profile migration or OS-level input/accessibility claim follows from these folder results.

## Final confirmed native receipts

Read and checked the final result files; each contains only passing results and a null failure:

- `web-folders156-noop-standard-results.json`: **11 passes** for the full standard web-folder journey.
- `web-folders156-noop-childlast-v2-results.json`: **11 passes** with the child deliberately placed last, including all empty/order/collision/workspace/restart/clear/disabled edges.
- `folders156-noop-final-results.json`: **8 passes** for the mixed web/terminal journey, including exact-job cleanup, actual nested Undo without command replay, one explicit Start again creating exactly one new job, and native-method workspace removal preserving the neighboring job.

The child-last fixture was corrected to wait for both actual baseline data pages to load before flushing their state. The earlier empty closed-history interruption remains preserved evidence, but the corrected native rerun passes without further production changes. Both parent-first and child-last arrangements now have actual complete native proof.

1. Where we are now: the bounded nested-folder Delete/Undo repair and its edge cases pass native acceptance.
2. What changed: deleted folder structure, Undo transaction identity and empty-folder history are preserved; empty close requests no longer erase the preceding transaction.
3. Overall goal: the familiar Zen browser with terminal tabs that follow normal organization while protecting running work.
4. Not built here: personal-data migration, macOS input-source/VoiceOver proof, or a new folder interface.
5. Proof checked: 11 standard web cases, 11 reversed-order web cases, 8 mixed cases, plus focused strict-source tests and independent review.
6. Next slice: parent source audit and commit; retain all earlier failed receipts beside the final passes.
7. Drift check: no renamed requirements, flattened folders, silent command replay or relaxed assertions were used to obtain these passes.

Recommended future handoff reasoning: high when modifying close, history or terminal ownership. Proof level: focused source tests plus isolated native Delete/Undo with exact neighboring-job survival; do not rerun unrelated broad suites unless the changed shared code warrants it.
