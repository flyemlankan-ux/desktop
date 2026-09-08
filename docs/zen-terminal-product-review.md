# Zen Terminal — complete product review and delivery plan

Date: September 8, 2026. Status: **not ready for personal migration or finished-product acceptance**.
Scope: the real Zen browser with first-class terminal tabs, not another browser shell.
Owner: Codex implements and self-tests; founder judges whether the final experience meets their intent.

## Why this review exists

The founder explicitly corrected the delivery standard: research and plan the whole
experience, from opening terminals and saving terminal setups to mixed web/terminal
organization, with native visual quality and end-to-end completion. The earlier26
installed-app checks are valid narrow evidence, not evidence for every workflow.
The earlier promotion of the whole native-tab area to `proved` was too broad.

This correction is R14, a supplied instruction, not an invented interview answer.
R01/R02 already required native folders/workspaces and one shared container list.
We must not ask the founder to repeat those decisions or call missed work new scope.
Personal copying stays on hold even if original Zen is closed.

## Real findings so far

1. **Confirmed blocker: selecting a terminal removes it from its mixed folder.**
   Actual installed `/Applications/Zen Terminal.app`, isolated synthetic profile.
   Native folder creation initially puts both a web tab and terminal in one folder.
   After switching away/back, the terminal becomes unpinned and leaves the folder;
   the web tab remains. Its shell survives, but organization is broken.
   Evidence: `proof/2026-09-08-product-audit/mixed-folder-diagnostic.json` and screenshot.
   Reproducer: `scripts/terminal-tabs/audit-terminal-native-grouping.py`.
   This uses actual native browser methods; it is NOT drag-and-drop user acceptance.
   Cause: `ZenTerminalTabs.markTerminalTab` calls `#forceNormalZenTab`, including
   repeated delayed unpinning; native `ZenFolders.createFolder` pins folder tabs.
   Tab selection also calls the restore-marker path. These two behaviors conflict.
2. **Acceptance gap: no current mixed-folder/workspace/split-view workflow in the26
   installed-app checks.** Old handoff claims do not prove the latest compiled app.
3. **Starting folder is not a dedicated current control.** The original handoff
   names a folder plus startup commands. Current editor stores command rows; users
   can type `cd`, but that is not proof of the intended saved-setup experience.
4. **Visual integration is not closed.** Terminal CSS forces dark/green colors;
   xterm has fixed theme values. Native dialog uses custom inline fieldsets/buttons.
   Need compare actual light/dark/compact/small-window states against upstream Zen,
   not merely show that controls fit one screenshot.
5. **Packaging remains development-grade.** Real resources, isolated identity,
   signed bundle and native behavior were tested. Ad-hoc signing is not Apple
   notarization; updates are manual, PGO is disabled, some native build utilities
   remain, and full upstream multilingual packaging was not completed.
6. **Security and remote-agent coverage has limits.** CLI `--version` does not prove
   authenticated interactive agents, remote reconnects or normal macOS permission
   prompts. No permission bypass or paid command should be introduced to get a pass.

7. **Inspected audit screenshot adds visible polish gaps:** the terminal exposes a
   raw internal `chrome://` address and a persistent technical-looking status strip;
   a fresh synthetic launch shows an upstream “Update Complete” toast despite this
   fork having no stock updater. These need deliberate native treatment, not cosmetic
   claims based solely on launching the app.

## Research: what Zen already provides

Primary sources checked September8; local pinned source wins if documentation and
this exact build differ. No unrelated competitor redesign is being copied.

- [Zen workspaces and containers](https://docs.zen-browser.app/user-manual/workspaces):
  workspaces organize projects; containers isolate website cookies. They are not
  interchangeable. Existing links/tab context menus also expose container choices,
  so auditing only the New Tab menu is insufficient.
- [Zen split view](https://docs.zen-browser.app/user-manual/split-view): existing
  drag-to-split and rearrangement are the surfaces to preserve for mixed content.
- [Zen window sync and recovery](https://docs.zen-browser.app/user-manual/window-sync):
  same-device windows can mirror tabs; temporary blank windows have different
  restoration behavior. Terminal lifetime must account for these cases explicitly.
- [Zen shortcuts](https://docs.zen-browser.app/user-manual/shortcuts): commands are
  customizable and conflicts exist. Browser shortcuts and shell keys need a
  deliberate focus policy, not whichever event handler wins by accident.
- Source receipts: original `terminal-tabs-step-one-handoff.md` and phase2 handoff;
  `src/zen/terminal/ZenTerminalTabs.mjs`, `ZenTerminalContainerStore.mjs`,
  `ZenTerminalPage.mjs`, native ContainerEditor patches; `src/zen/folders/` and
  `src/zen/split-view/ZenViewSplitter.mjs`.

## The product model — keep the meanings separate

- **Browser profile:** the whole private browser setup, including login data.
- **Saved terminal setup:** a named reusable configuration in Zen's one existing
  container list, with name/color/icon, starting location and ordered startup steps.
  The implementation currently calls this a terminal container/recipe. Do not add
  another competing profile manager or silently store passwords in startup steps.
- **Live terminal tab:** one running shell launched from a saved setup. Opening that
  setup twice should create independent jobs; viewing the same mirrored tab twice
  should not run startup twice. Editing a setup must not change an already-running job.
- **Folder/workspace:** groups related terminals and websites using Zen's own tools.
- **Split view:** arranges those tabs on screen. It must not create a new shell merely
  because a tab moved, became visible or changed size.

Existing lifetime rule remains: tab close destroys the last view's shell; quitting
or crashing the browser preserves tmux-backed shells; Mac reboot survival was
explicitly deferred. Restoring a closed tab cannot honestly resurrect a killed
process. This distinction needs visible, tested behavior rather than an ambiguous
'Saved' label.

## Complete workflow inventory and acceptance obligations

Every row needs actual behavior evidence, not only a code-exists check. 'Audit' below
means not currently accepted; it does not mean the feature is definitely broken.

| Area | User journey / edge case | Required outcome | Current status |
|---|---|---|---|
| First launch | Fresh app, no personal data | Ordinary Zen welcome/default web tab; obvious intentional terminal choice | Partial proof |
| First launch | Default Terminal deleted, browser restarted | Do not recreate deliberately deleted setup | Logic proof; native retest |
| Open | Plain New Tab, Cmd+T, address bar | Remain ordinary web browsing | Audit all entry points |
| Open | Mixed container list | One list, understandable names/kind, one Manage entry | Narrow native proof |
| Open | Sidebar menu and long-press New Tab | Same setup opens same kind, no duplicated items | Audit both real inputs |
| Open | Tab/link 'open in container' menus | Never unexpectedly replace a URL action with shell execution | High-priority audit |
| Open | Workspace default container | No accidental shell launch from ordinary web navigation | High-priority audit |
| Open | Open same saved setup twice | Separate shells, each recipe once | Logic proof; full journey needed |
| Open | Deleted/malformed saved setup | Clear recoverable message, no unintended command | Partial failure tests |
| Save setup | Create/name/icon/color/cancel | Native controls; cancel writes nothing | Partial native proof |
| Save setup | Select starting folder with spaces/unicode | Starts in exact chosen folder, no shell injection | Missing dedicated control |
| Save setup | Folder missing/unavailable | Explain failure; never quietly start in wrong place | Needs defined recovery/UI |
| Save setup | Add/reorder/remove/empty startup rows | Order is durable; blank means plain shell | Narrow native + logic proof |
| Save setup | SSH then a program | Program runs remotely only after connection; failure stays safe | Local/fake-host proof only |
| Save setup | Edit, cancel, reopen Settings, restart | Configuration persists, cancel preserves prior data | Full journey needed |
| Save setup | Edit while jobs are running | Existing processes unchanged; new tabs use new settings | Audit |
| Save setup | Rename setup vs rename an individual tab | Clear distinction; custom tab names not overwritten | Partial proof |
| Save setup | Delete/change kind with running/background tabs | Explain consequences; cancel safe; exact cleanup | Logic proof; native journey needed |
| Group | Drag terminal and web page into same folder | Both remain members, including after selection | CONFIRMED FAIL |
| Group | Reorder/collapse/expand/nest/rename folder | Preserve order, membership and live shells | Untested |
| Group | Move folder between workspaces | All web/terminal children move intact | Untested |
| Group | Pin/unpin and Essentials | Respect intentional user organization; no delayed reversal | Confirmed pin conflict; broader audit |
| Group | Delete folder with mixed tabs | Explicit consequences; only intended terminal processes stop | High-priority audit |
| Group | Undo folder/tab close | No false promise of reviving killed processes | Needs full visible-state proof |
| Workspace | Switch/create/rename/delete | No lost tabs or unexpected terminal launch | Untested |
| Workspace | Mixed website cookie containers | Website account separation unchanged | Untested with synthetic accounts |
| Split | Drag web+terminal into side-by-side view | Native layout, correct focus and shell dimensions | Untested |
| Split | Rearrange/resize/unsplit | Same shell, no recipe rerun; no dead input | Untested |
| Split | Two terminals, close one pane | Correct session survives, no cross-session cleanup | Untested |
| Windows | Mirror/adopt/move tabs and folders | Ownership correct across all viewers | Duplicate-tab subset only |
| Windows | Close one window vs quit all | No accidental shell destruction/orphan ambiguity | Full native journey needed |
| Windows | Temporary blank window | Explicit restore/lifetime limits consistent with Zen | Audit |
| Recovery | Reload/quit/crash | Same shell and custom tab name; recipe not repeated |26-test subset passes |
| Recovery | Restore folder/workspace/split layout | Organization and process identity both survive | Untested |
| Recovery | Sleep/wake, helper loss, tmux loss | Honest state and safe reconnect; no silent duplicate job | Partial process proof |
| Recovery | Mac reboot | Explain live-process loss; saved setups remain | Deferred live survival, UX audit |
| Input | Unicode, repeated keys, paste, Ctrl+C, vi | Exact input and correct interrupts | Proved narrow cases |
| Input | Cmd+C/V/A, selection, context menu, IME, Option keys | Browser/shell focus rules predictable | Broader audit |
| Input | Large/multiline paste | No truncated command; clear warning for rejected data | Size guard proved; UX audit |
| Terminal | Scrollback, search, long output, streaming | Responsive, bounded memory, usable navigation | Bounded rendered tests; broader audit |
| Terminal | Links and file paths in output | Deliberate safe behavior; no accidental privileged launch | Clickable links previously deferred |
| Appearance | Light/dark, custom accent, compact sidebar | Added UI feels native; readable terminal contrast | Not accepted |
| Appearance | Narrow window, split panes, fullscreen, high DPI | No clipping; controls reachable, no dead margins | Resize subset only |
| Accessibility | Keyboard-only, focus order, labels, contrast, motion | Core tasks possible without pointer; assistive-tech check | Not accepted |
| Security | Website cannot open privileged terminal page | No website-to-shell bridge | Native principal check passes |
| Security | URLs/session IDs, shared folders/tabs, extensions | No secret/session capability leakage; deliberate execution only | High-priority audit |
| Security | Local processes and credentials | OS prompts respected; no passwords copied into recipe logs | Boundaries exist; full review needed |
| Security | Private browsing | Explicit supported/refused behavior, no persistent leakage | Not accepted |
| Security | Terminal setup is not an isolation sandbox | Do not claim separate OS users or isolated agent homes | Documented limit; UI clarity audit |
| Performance | Cold start, idle, many tabs, high output | Measured targets vs stock Zen; no timer/listener growth | No baseline comparison |
| Delivery | Install/upgrade/rollback/remove | Distinct identity, user data separate, recoverable changes | Fresh install only proved |
| Delivery | Browser security updates/dependencies | Owned repeatable patch/update process, honest age/risk | Manual process, needs hardening |
| Delivery | Signing/languages/licenses/clean packaging | No dev/test debris or missing notice; public claims accurate | Private-dev proof only |
| Personal copy | All profiles/logins/tabs/settings | Copy not move; verify privately; original untouched | Synthetic proof, actual copy on hold |
| Personal copy | Future divergence or rollback | Never copy upgraded data backwards; explain independence | Documented; end-to-end pending |

## Build sequence — finish journeys, not isolated buttons

1. **Repair the native-tab foundation.** Reproduce folder/pin failure; remove only
   organization-destroying logic without restoring unwanted URL-reset labels.
   Test selected/background restore, repeated marking, folders, pins and Essentials.
   Then exercise real drag/drop and restart on a disposable app.
2. **Complete the saved-setup journey.** Reconcile starting-folder requirement with
   command rows; use native controls, clear setup-vs-tab names and empty/error states.
   Prove create -> save -> launch twice -> edit -> relaunch -> restart -> delete/cancel.
3. **Audit every way in and out.** Sidebar, menus, keyboard, ordinary web new tab,
   context menus, workspace defaults, close/undo and dangerous actions. No unexpected
   terminal execution from an action that means opening a website.
4. **Complete mixed-project workflows.** Folder nesting/reordering, workspaces,
   split view, mirrored windows, switching and recovery, including deletion failure cases.
5. **Visual, keyboard and accessibility pass.** Side-by-side native Zen baseline,
   actual light/dark/compact/small-window screenshots and keyboard navigation.
   Use Zen's existing styling; no invented second dashboard or decorative skin.
6. **Security, remote use and load review.** Threat review, disposable failures,
   realistic local interactive programs, consent-bounded remote test if available,
   measured CPU/memory/latency, sleep/disconnect and permission-dialog behavior.
7. **Clean delivery and maintenance.** Reproducible clean package, installation/
   upgrade/rollback proof, licensing and realistic update/signing limitations.
8. **Only then personal setup.** Copy with original Zen closed; private hashes;
   normal launch with expected tabs/workspaces/theme and working terminals.

For slices1–4 and6–8: recommended reasoning **high**, proof **strong focused tests
plus actual packaged Mac journeys**. For styling-only changes: reasoning **medium**,
proof **visual/keyboard checks across the named states plus impacted native journeys**.
Do not rerun unrelated Core tests. This is not an Empire Core project.

## Definition of done and review discipline

- A source patch being present is not completion. A command working is not completion.
- Each row is mapped to a test or an explicit, visible, justified limitation.
- Every important destructive action has a cancellation or failure test.
- Screenshots are inspected, not merely captured; numbers report exactly what ran.
- App-level cases use synthetic profiles and test-owned shells only.
- Code review checks races, cleanup, privacy, reversibility and unintended browser changes.
- Final package and installed-app checks rerun after final code changes; old passes
  stay labelled with their build and scope.
- 'Functionally tested', 'visual review passed', 'private deployment ready' and
  'public release ready' are separate claims. No more one broad `proved` label.
- Genuine new product decisions discovered later are surfaced one at a time; existing
  saved answers and the founder's autonomous-build instruction must be used first.
