# Native terminal organization review — September 19

Status: read-only source audit and fix proposal. No production edit or new app pass.
Canonical product plan read directly on Chubs; not copied back to this Mac.

## Finding
`ZenTerminalTabs.markTerminalTab` invokes `#forceNormalZenTab` immediately and at
0/100/500/1500 ms. This removes Essential and default-container attributes, deletes
`_zenPinnedInitialState`, and invokes native unpin. Selection and background restore
invoke the marker again. Native folders pin member tabs. Therefore simply selecting
a terminal dismantles the user's folder membership; quick manual pinning is also
reversed by queued timers. This matches the September 8 actual-app diagnostic.

## Minimal proposed repair
1. Remove both force-normal methods and all calls. Marking is identification, not
   permission to reorganize the tab. Preserve pinned/Essential flags, folder,
   workspace, initial pinned state, default-container marker, and split membership.
2. Clear only URL-reset decoration while marking: `zen-pinned-changed`,
   `had-zen-pinned-changed`, `--zen-original-tab-icon`, and existing unwanted sublabel.
3. At `ZenPinnedTabManager.pinHasChangedUrl`, if the tab is marked terminal, clear
   those same URL-reset decoration attributes and return. This handles delayed
   browser progress and split decoration without discarding useful native state.
   Do not suppress decoration for ordinary website tabs.
4. Keep the terminal session id and close-handler semantics unchanged. Native pinned
   close preferences can switch/unload/reset rather than remove a tab. Such actions
   must retain the shell; only actual last-view removal destroys it.

Deleting initial pinned state is NOT an acceptable substitute for a narrow guard:
window mirroring and native restoration use it to reconstruct tab identity.

## Files required for implementation
- `src/zen/terminal/ZenTerminalTabs.mjs`
- `src/zen/tabs/ZenPinnedTabManager.mjs`
- New `scripts/terminal-tabs/test-terminal-organization.mjs`
- Expand `scripts/terminal-tabs/audit-terminal-native-grouping.py` or new dedicated
  native organization journey under the parent-controlled app test schedule.
- Parent packaging owner must add changed `ZenPinnedTabManager.mjs` to local overlay
  preparation and exact-byte packaged asset verification. Currently those scripts
  only include terminal resources and the previously modified ZenUIManager.

## Focused automated coverage
Use the real class source in a small synthetic browser environment, not a recreated
implementation. Assert state preservation after mark, repeated mark, select,
background lazy restore, and all queued callbacks. State includes pin, Essentials,
folder object, nested split group, workspace id, default-container marker, initial
pin object, custom name, and terminal session id. Assert intentional unpin remains
unpin. Assert marker never calls pin/unpin. Test decoration suppression for terminal
and unchanged positive website pin-decoration behavior, including split markers.

These are logic checks, NOT drag-and-drop or actual native integration proof.

## Native proof required before acceptance
Synthetic profile, test-owned shell only. Create terminal + website; group; select
away/back and wait beyond old 1500 ms timeout; preserve both members. Reorder,
collapse/expand, rename, nested folder, workspace transfer, pin/unpin, Essentials,
split/unsplit. Check same shell PID and recipe count. Quit/relaunch with grouped
background terminal and repeat selection. Explicit folder removal cancels safely
or removes exactly intended shells; undo starts a new process, not a falsely claimed
resurrection. Website pin URL-reset behavior remains intact.

Actual pointer-driven grouping must supplement method-driven diagnostics. No personal
profiles, global tmux server, original Zen process, or installed app changes here.

Recommended reasoning: high. Proof: strong focused logic + actual packaged native
journeys, including negative/destructive cases. No unrelated Core tests.

## Implemented after refreshed readiness approval

Parent approved this bounded production slice. Removed all force-normal methods and
calls; terminal marking now clears decoration only. Added terminal-only early return
in native pin decoration creation, leaving website behavior and reset logic intact.
No changes to session deletion, native unload, pinned reset, split/folder ownership,
or user-selected pin/Essentials state.

Executed:
- `node scripts/terminal-tabs/test-terminal-organization.mjs`: PASS 8 real-class,
  synthetic-browser cases. Normal pinned, Essential, lazy background, split member,
  unpinned; selection/restore/repeated markers; normal and split website indicators;
  deliberate unpin remains unpinned. Delayed constructor callbacks drained.
- `node scripts/terminal-tabs/check-terminal-tabs.mjs`: PASS source wiring/syntax.
- `node --check` both changed production modules: PASS.
- `python3 -m py_compile scripts/terminal-tabs/audit-terminal-native-grouping.py`: PASS.

Expanded actual-app diagnostic to cover intentional pin/unpin, Essentials,
regroup/collapse, decoration suppression, grouped restart and same shell PID.
This expanded native diagnostic has NOT been run by this agent. Parent owns UI
scheduling, packaged module verification, and native acceptance. No claim that this
slice proves pointer dragging, nested folders, workspaces, or split journeys.

### Slice recap
1. Current state: organization-destroying marker code removed; native proof pending.
2. Changed: marking no longer reorganizes tabs; terminal URL-reset badge suppressed.
3. Overall: real Zen with first-class terminal tabs and saved terminal setups.
4. Not built: broad mixed-project acceptance, final packaging, personal migration.
5. Proof: focused synthetic logic, wiring, syntax only; actual-app checks expanded.
6. Next: parent packages exact bytes and runs native journeys. Reasoning high;
   proof strong focused logic plus actual packaged Mac tests.
7. Drift: native organization retained rather than replacing it with custom UI.

## Native Essentials diagnostic correction

Parent actual-app run found native eligibility refusal, not terminal unpinning:
`allowed=false`, separate Essentials enabled, terminal cookie container6 versus
workspace container0, count0/max12. addToEssentials correctly returned false.

Diagnostic now deliberately tests BOTH supported settings:
1. Start synthetic profile with `zen.workspaces.separate-essentials=true` and prove
   mismatched-container add is refused, leaves tab non-Essential.
2. Set that actual preference false in synthetic profile, persist the synthetic
   startup preference file, quit and relaunch. Zen reads containerSpecificEssentials
   during initialization; its native Settings requests restart for this preference.
   No direct mutation of manager fields and no `replicating=true` bypass.
3. Assert stored preference and active manager mode are false, native add succeeds,
   selection preserves Essential, then a second restart retains Essential and PID.
4. Remove Essential normally, regroup with the website and prove grouped restart.

The test logs the native eligibility values, refusal, preference transition and
post-restart active mode. Web-tab identity is saved with a synthetic custom tab value
so the same tab can be found reliably across restarts. Syntax check passed; updated
headed run belongs to parent and is pending. No production logic changed.

## Agent-owned native diagnostics (September19)

Ran only owned synthetic grouping app sessions after parent delegated UI access.
1. `organization-agent.log`: reproduced apparent Essential reconnect timeout. Full
   timeout snapshot proved target selected, correct session URI/id, pending=false,
   persistent record and tmux alive. Actual status was `saved session reconnected`:
   old test substring `ready` was wrong. Updated readiness to actual terminal-ready
   DOM state; same-PID assertion remains mandatory.
2. `organization-agent-v2.log` and v3: shared Essential selection AND restart now
   pass with same shell. Next pin-decoration test genuinely failed.
3. Exact source inspection of generated app found preparer had placed pin manager
   under unused `chrome/browser/content/browser/ZenPinnedTabManager.mjs`. Actual
   native loader uses `chrome/browser/content/browser/zen-components/ZenPinnedTabManager.mjs`.
   Actual loaded method lacks terminal guard; v3 logs guard=false, marked=true.
   This is an overlay/verification mapping error, not a reason to waive assertion.
4. Also found SpaceManager's actual entry is `modules/zen/ZenSpaceManager.mjs` inside
   browser/omni.ja; preparer had added unused chrome-root entry. ZenUIManager chrome
   root path is correct. Parent owns packaging correction and subsequent testing.

All spawned app processes quit and exact synthetic tmux sessions cleaned. UI handed
back to parent. No production changes in this investigation. Full grouping acceptance
still pending corrected app. Old local overlay checks of SpaceManager cannot be used
as proof of its changed behavior until this packaging path is repaired.
