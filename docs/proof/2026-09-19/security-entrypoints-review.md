# Terminal safety and entry-point review

2026-09-19. Reviewed checkout e8b57e4b72b6167c5d2cf3a288753cdac1cf0932 before this round's implementation. This is a bounded source review, not complete product acceptance. No personal profiles read, no UI launched, no production files changed. Canonical product plan was read over SSH from Chubs and was not copied locally.

## Result

The current code protects websites from directly opening the privileged terminal page in the existing principal check. The process-saving layer has strong targeted tests. However, several everyday entry points and ownership rules are not closed. Do not call this security-complete or ready for migration.

### 1. A session's saved-setup owner can change (confirmed module reproducer; high priority)

`src/zen/terminal/ZenTerminalSessionManager.mjs:83-108` accepts an existing ID with a different `userContextId`, replacing the old owner. Page startup (`ZenTerminalPage.mjs:62-99,285-310`) obtains both values from the address, not from independently checked tab identity. A second view can therefore attach to the same shell while relabeling its owner. Deleting the old setup then misses this job; deleting the new setup can kill it. This is same-browser-profile ownership confusion, **not evidence that a website can exploit it**.

Executed a Node import of the real module with an in-memory preferences object (no subprocesses):

```js
registerTerminalSession('same-session', {userContextId:'10'}); // owner 10
registerTerminalSession('same-session', {userContextId:'20'}); // owner 20
listTerminalSessionsForUserContextId('10').length; // 0
listTerminalSessionsForUserContextId('20').length; // 1
```

Recommended: an existing session cannot change owner during registration. Reject mismatch before writes or subprocess lookup. Validate URL setup identity against the actual browser/tab identity and a still-existing public container. Mirrored same-owner tabs remain valid. Test same ID/same owner, changed owner, removed owner, malformed numeric identity, copied browser profile, pending deletion, and zero process launch on rejection.

### 2. Private browsing is hidden in the menu, not refused by the terminal machinery (source-confirmed missing guard; native reachability not tested)

`src/browser/base/content/zen-panels/popups.inc:11-16` hides the container menu in private browsing. Neither `ZenTerminalTabs.openTerminalTab:332-351` nor `ZenTerminalPage.startShell:285-347` checks private browsing. Both use the normal profile's durable records/socket. Opening the internal page from another trusted entry point or restoring/copying a terminal into a private window must not silently create normal saved shell state. Exact normal-user reachability needs native tests; no exploit claim is made.

Recommended safe default: terminals unavailable in private windows, with an understandable reason. Enforce this both at the opener and inside the page before registering anything or looking up tmux. Do not promise that private windows make shell history/files private. Test direct privileged page open and a dragged/adopted tab in a synthetic private window; assert no record, shell, recipe side effect, or shared attachment.

### 3. Workspace defaults can select a terminal setup as a web-cookie container (source-confirmed list inclusion; native journey pending)

`src/zen/spaces/ZenSpaceCreation.mjs:326-354` and `ZenSpaceManager.mjs:1219-1241` use the complete public container list without filtering terminal setups. `ZenSpaceManager.mjs:2972-3016` then inherits that identity for ordinary web creation. The terminal-specific menu patch only changes explicit New Tab container menus (`ZenTerminalTabs.mjs:108-180`); it does not convert ordinary new tabs. Thus a terminal-named container can unexpectedly act as an ordinary website cookie container. This is a product identity mismatch, not demonstrated command execution.

Recommended: retain ONE existing container list in management, but filter context-appropriate choices. Workspace default website identity, link-open-in-container and web-tab-reopen menus should offer web containers only. Explicit New Tab container selection can offer both types with a clear kind. Never replace a link-opening action with saved command execution. Repair or ignore already-saved workspace defaults that now point to a terminal setup. Test ordinary Cmd+T, external URL, link context menu, tab reopen menu, workspace create/edit, and converting an in-use web default to terminal.

Link/tab menu code paths are not demonstrated by the current installed-app suite. The audited project adds no explicit filtering patch for them. Their precise installed behavior remains a required native check, not a claimed reproduced bug.

### 4. Navigating away can leave a detached job and terminal identity on a web tab (source-confirmed incomplete lifecycle; native reproducer pending)

`ZenTerminalTabs.mjs:275-279` defines `unmarkTerminalTab`, but repository search found no call. It would remove only the terminal marker, not the session attribute/custom saved value. Session lookup prioritizes those values even before checking the current URL (`:34-63`). Page departure only detaches the viewer (`ZenTerminalPage.mjs:489-518`); session deletion is tied to TabClose (`ZenTerminalTabs.mjs:380-401`). A web page replacing the terminal can therefore retain hidden terminal ownership until the tab closes, and its close can terminate work no longer visible.

Recommended: choose and prove a deliberate navigation policy. Prefer keeping terminal tabs as terminal surfaces and opening web navigation in a normal web tab. Do not silently kill a running job on URL change. Test typed URL, link/drop, reload, back/forward, duplicate, restore and browser window adoption. Clear all terminal-specific state only when ownership is intentionally transferred/ended, never just the icon.

### 5. Reconnect wording can conceal a restarted job (source-confirmed branch)

`ZenTerminalSessionManager.mjs:276-314` creates a session when tmux reports confirmed absence even for an old record. `ZenTerminalPage.mjs:373-383,487-488` shows 'saved work has not been deleted' and a Reconnect button that reloads. If the shell exited, tmux was stopped, or the Mac rebooted, reloading starts the recipe again. This is not recovery of the previous process.

Recommended: distinguish live reconnect from known-lost session. Show 'previous session ended' and require an explicit Start Again action before re-running a saved recipe. Unknown tmux state must continue to refuse replacement. Test normal shell exit, exact session stopped externally, missing tool, inaccessible tool, reboot-equivalent missing server, and intentionally closed/Undo Close. Startup commands can have real side effects; a success-like 'saved' message is insufficient.

## What was actually checked

- Executed `node scripts/terminal-tabs/test-terminal-session-persistence.mjs`: **14 passed**, including isolated real tmux. No application UI launch or personal socket access.
- Confirmed owner-reassignment reproducer using the actual module and memory-only preferences.
- Read the terminal tab/page/session/container sources and pinned Zen workspace source.
- Read the canonical Chubs plan remotely; no local plan reconstruction.
- Existing `test-terminal-macos-app.py:67-70` tests `checkLoadURIWithPrincipal` rejecting an ordinary website principal. It is valuable, but is not actual hostile iframe/navigation/extension/download coverage. Test honest scope accordingly.
- Existing native suite checks one duplicate-view close, quit/crash reconnect and explicit final close. It does not close private windows, cross-owner views, workspace default identity, link/tab reopening, navigation away, lost-session restart consent, or all simultaneous multi-window close races.
- Existing process tests cover profile-separated sockets, exact target names, missing-vs-unknown probes, failed-delete retention, serialized create/delete, bounded pipe output, timeout, resizing and copied-profile isolation. Preserve these strengths.

## Implementation order and proof bar

1. Refuse private launches and changed-owner attachments; narrow module tests plus real synthetic-profile rejection tests.
2. Restrict choices by context without adding a second manager; real menu/keyboard/link/workspace tests.
3. Specify lost-session and navigation behavior, then test actual process identities and startup side-effect counters.
4. Run cross-window/mirror/adoption/last-close matrix after grouping changes land; ensure no unrelated socket or surviving viewer is killed.

Recommended reasoning level: high for identity/lifetime changes. Proof level: focused module tests plus actual isolated native-browser tests; source-string checks alone cannot promote user journeys to complete. Migration remains held until full product acceptance.

## C17/B17 implementation follow-up: immutable owner

Implemented the narrow registration repair in `ZenTerminalSessionManager.mjs` after
coordinating file ownership with the saved-setup worker. Another view may keep the
same owner; an existing record cannot switch modern or legacy setup owner. An
omitted owner preserves the saved owner. Old ownerless records cannot be silently
claimed by a new setup. Refusal occurs before preference writes or process lookup.

New `test-terminal-session-ownership.mjs` first reproduced the previous failure,
then passed all **6** cases after the fix. Existing persistence suite, including
the other worker's lazy settings callback and folder guards, passed all **16**
cases including isolated real tmux. These are module/process checks, not a native
page identity or private-window acceptance claim. No user data accessed.

Next proof: native page rejects URL/browser identity mismatch and private context
before any saved record or shell launch. Reasoning high; proof focused module plus
isolated native browser. Session restart consent remains a separate unfinished
piece, not silently included in this repair's acceptance.

## C17/B17 implementation follow-up: entry points and page context

`ZenTerminalTabs` now refuses explicit private-window opens with an explanation,
before allocating a session ID or adding a tab. The existing shared native
container-menu builder retains terminal choices only for the unified New Tab and
long-press New Tab menus. Ordinary website-link, reopen and workspace pickers
filter terminal rows; the underlying saved-setup management list is unchanged.
The pinned packaged `browser.js:1532-1543` and `utilityOverlay.js:181-300` were
inspected to confirm the menu builder is synchronous and shared by these callers.

`ZenTerminalPage` now checks actual docshell private status and container identity,
and confirms a matching public container still exists, before reading the saved
setup or registering/starting a process. It refuses malformed, noncanonical or
mismatched address identities. The parent independently checked the actual
installed155 docshell identity source before this change; this worker did not
launch the browser. The page's system principal is deliberately not used as the
container identity source.

`test-terminal-entrypoints.mjs`: **19 passed**, exercising production methods in
a synthetic browser. Organization8, ownership6, persistence16 also passed.
These are NOT native rendered menu/private-window acceptance. Parent must test
real native calls and no process side effects. Already-saved workspace defaults
that refer to terminal containers still need a safe web-default fallback; the
menu filter alone does not repair historical choices. Lost-session restart
consent and navigation-away lifecycle remain unfinished.

## C17/B17 follow-up: stale defaults and ended jobs

Implemented a narrow `ZenSpaceManager.getContextIdIfNeeded` fallback: an implicit
website creation whose saved workspace default was converted to Terminal uses
ordinary web identity0. Explicit terminal opens retain their requested identity;
ordinary web defaults are unaffected. Four production-method synthetic cases pass.

The process-saving module now records and flushes startup intent before launching
commands. Registration preserves that fact. Missing work that previously started
cannot silently run startup steps again; explicit restart consent is necessary.
The page carries `started=1` in its own history address, so Undo Close retains the
warning even after successful final-tab cleanup removed the session record. This
marker only makes checks stricter; it never grants restart permission. Only the
visible **Start again** click grants one local attempt. Reload does not. Unknown
process state refuses replacement even with consent. A missing tmux executable
for previously persistent work refuses fallback to an unrelated direct shell.

The page now distinguishes **Check session**, **Retry check**, and **Start again**,
and displays the actual reason instead of claiming lost work is saved. A live
existing session still reconnects without reading edited setup settings.

Persistence suite now **19 passed**, ownership6, entry points19, stale defaults4.
The real tmux copied-profile test now first proves refusal, then supplies explicit
restart consent; the original profile's shell remains untouched. Browser bridge
suite was extended (12 expected checks) for copied-profile consent and lost-job
reload/start-again side-effect counts, but this worker did NOT run UI. Parent must
run it plus actual native Undo Close/reload/private/mixed-workspace acceptance.

Navigation is not silently changed: current page departure detaches its viewer,
retains the owning tab's session identity, and only actual final TabClose deletes
its job (C05). This means replacing a terminal with a website can hide its running
job until Back or close. Parent was warned: do not add destruction on navigation;
a deliberate visible navigation policy and native evidence are still required.

Proof level for handoff: high reasoning, targeted module/process regression plus
actual native terminal exit, externally stopped session, missing tool, Undo Close,
reload and copied-profile confirmation. No native acceptance claim is made here.

## Native safety test handoff and bridge-cleanup diagnosis

Added `scripts/terminal-tabs/test-terminal-safety-workflows.py` for the parent to
run on the rebuilt disposable app. It checks actual private-window refusal and
modal explanation, direct private page rejection, mismatched container rejection,
externally ended tmux work, reload refusal, rendered Start again clicks, final
close cleanup, and Undo Close's stricter history marker. Python compilation passed;
**this worker has not launched or claimed passing native safety journeys**.

Parent's first updated rendered-page run stopped at two live helpers instead of
one. Inspection found the added secondary folder page used Playwright's default
`page.close()`. The installed official Playwright type documentation states this
skips unload handlers (`playwright-core/types/types.d.ts:2417-2422`). Production
cleanup is an unload handler, so the test was bypassing it. The bridge now runs
unload handlers explicitly and waits up to five seconds for that exact page's
owned helper to exit. It does not kill the helper to manufacture success or relax
the one-live-helper assertion. Page ownership and process arguments are recorded
for any remaining failure. Parent must rerun; this diagnosis is not a passing UI
claim.

## Native modal acceptance remains unproved

Parent's safety-v2 run displayed the real explanation but `WebDriver:AcceptAlert`
timed out after30seconds. This worker attempted two owned synthetic runs using
Gecko's actual dialog-button lookup (no prompt replacement); neither completed
reliably. Only those exact test process IDs were terminated. No production edits
or private-profile access occurred. Source shows the driver waits for a dialog
close event and an animation frame after clicking; the precise missed condition
is not established, so this is not claimed to be a known product or driver fix.

Removed the unproved workaround. The safety test now offers explicit
`--skip-private-modal`, recording that journey as **not_run**, never as passed.
Default behavior still attempts real modal acceptance. Direct private-page refusal
and lost-session/reload/Undo Close checks remain enabled with the option. This
unblocks independent proof without hiding the outstanding real-modal check.

## Actual native safety proof: v7

Executed the real isolated Mac app safety script on the parent's rebuilt overlay:
**9 checks passed; 1 explicitly not_run** (private-opener modal dismissal).
The direct private-page refusal did pass. Container mismatch, missing process,
reload refusal, real rendered Start again click, exact startup counts, final-tab
cleanup, Undo Close history marker, and real rendered Undo restart all passed.

Earlier v5/v6 failed because the test requested a terminal child-document element
from the chrome context and then tried to switch a top-level browser as a frame.
The final test locates the actual terminal WebDriver content-window handle and
uses `ElementClick` there; it does not substitute JavaScript button execution.
The tmux PID probe uses the valid display-message target and checks numeric output.

Evidence: `safety-overlay-v7-safety-workflows.json`,
`safety-overlay-v7-safety-ended-session.png`, and
`safety-overlay-v7-safety-complete.png`. Test log:
`.terminal-test/safety-review-v7.log`. Test exited0, its app exited, and only its
owned synthetic session IDs were cleaned up. UI ownership returned to parent.
This is current overlay acceptance, not final distributable acceptance; the
private modal and navigation-away product journey remain unclosed.
