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
