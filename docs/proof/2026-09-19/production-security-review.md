# Independent terminal entry-point review, second pass

2026-09-19. Scope: current production source and Firefox155 packaged upstream;
future Zen1.22.2b sharing source read with git show at
04e7db5d3a84ec754c14d6fc6930fa3ccd00c836 (Firefox156). No UI launch,
private-profile inspection or production changes were made during the audit.
Implementation after the review is recorded separately below.

## Priority1: incoming shares accept non-web addresses before trusted opening

Future `src/zen/share/ZenShareManager.mjs` at1.22.2b:
- Outgoing `#serializeTab:237-242` filters to HTTP/HTTPS.
- Incoming `#importTab:796-805` calls `gBrowser.addTrustedTab(item.url,...)`.
- `share.schema.json:100-113` requires a URI-shaped string, not HTTP/HTTPS.
- `ZenShareClient.fetchSharePreview:218-223` validates only that schema.
- `ZenShareManager:373-425` automatically imports split-view shares, without the
  folder/workspace confirmation used at553-562.

This is a concrete inbound/outbound validation asymmetry and trusted-open path
from server data. Do not infer that ordinary serializer output limits malicious
server input. Current terminal page actual-container guard blocks mismatched
terminal URLs, so this audit does NOT claim demonstrated terminal code execution.
Other privileged/internal address behavior has not been run. Refuse the complete
share document before creating anything if ANY nested tab is not a parsed absolute
HTTP/HTTPS address; validate again at the import boundary. Test chrome, resource,
file, data, javascript, about, protocol-relative, malformed and mixed nested lists,
including eager split-view import. Zero tabs, folders, shells or partial import
on refusal. Outgoing terminal tabs must remain excluded.

## Priority2: All Tabs has a separate unfiltered container list

Pinned155 `browser/components/tabbrowser/content/browser-allTabsMenu.js:174-198`
builds rows directly from `ContextualIdentityService.getPublicIdentities`, then
assigns `Browser:NewUserContextTab`. It does NOT call `createUserContextMenu`.
Current `ZenTerminalTabs:181-194` filters only the shared builder. Consequently
this alternate list can present a saved terminal setup but open an ordinary web
tab in that identity. This is an entry-point consistency leak, not demonstrated
shell execution. Filter terminal IDs at this native list construction, retaining
all web IDs and the one existing manager. Native visibility can depend on Zen
customization; source existence is not a claim every user sees the menu.

The native File/New Container menu DOES call the shared builder
(`browser-menubar.js:191-193`) and is filtered to web identities. URL-bar, link,
main-popup and tab-context callers also use that builder. Whether File/New
Container should deliberately be another terminal opener is a product consistency
choice; do not silently broaden executable entry points to fix the All Tabs bug.

## Priority2: extension/service removal bypasses terminal lifecycle cleanup

Pinned155 `toolkit/components/extensions/parent/ext-contextualIdentities.js:326-353`
removes through `ContextualIdentityService.remove` directly. The service emits
`contextual-identity-deleted` at its500-522 block. Current terminal code has no
observer for that event. Terminal-specific deletion logic only lives in native
Settings patches. Therefore extension/service deletion can leave terminal recipe
preferences and live/background jobs for a removed identity. Page startup rejects
the missing public identity, but already-running processes are unaffected.

Recommended policy before implementation: deleting a real container should have
one consistent cleanup implementation shared by Settings and the service observer.
Deletion is an explicit owner action, so mark matching sessions pending immediately
and stop only those exact profile-scoped jobs; do not depend on a visible tab or
broad kill-server. Keep durable failed-cleanup intent; remove obsolete recipes.
Observe once per browser profile, not independently in every window. Existing
Settings confirmation remains; extensions already authorized to remove containers
must not get an unrelated way to delete other setups. Test service deletion with
visible+background jobs, neighboring setup, multiple windows, unavailable tmux,
creation-in-flight and next-launch retry. No change has been made yet.

A related time-of-check risk: page validates public identity before asynchronous
tool lookup; `getNewSessionSettings` later normalizes `getStartupRecord()?.recipe`.
If an external removal lands between those steps, stale recipes may remain and
there is no deletion marker. The shared observer plus a final current-owner check
before fresh creation closes this race. Normal Settings deletion already marks
pending before removing, which is materially safer.

## Priority2: URL-looking tabs can claim cleanup without successful attachment

`ZenTerminalTabs:36-64` trusts a saved session attribute/custom value, or any URL
whose string starts with terminal.xhtml. `#onTerminalTabClose:430-456` uses that ID
without validating the actual setup owner or successful session attachment.
`destroyTerminalSession` creates pending intent even when no record existed.
A rejected/malformed privileged page can therefore acquire terminal styling or
request session cleanup. Another valid visible view prevents final deletion, but
an orphan/background job with that known ID could be targeted by a trusted open.
This is a concrete cleanup trust mismatch, NOT a demonstrated website attack;
websites are still unable to load the privileged page through ordinary principals.

Use exact parsed URL identity rather than startsWith. Before destructive cleanup,
require an existing record with the matching actual container and a tab-owned
session receipt (including lazy/restored legitimate tabs). Preserve C05: only final
actual tab close destroys the job. Tests: terminal.xhtml.evil prefix, malformed ID,
rejected mismatched-context page with a real orphan ID, pending lazy valid tab,
valid duplicate final-close, adopted windows. Do not 'fix' by clearing every saved
ID on navigation, which would leak the job or silently change its owner.

## Priority3: container identity reuse is not an ordinary creation bug

Pinned `ContextualIdentityService.create:391-402` increments persisted
_lastUserContextId; deletion does not decrement it. Normal remove-and-create does
not recycle IDs, and fresh page startup requires a current public identity.
Manually corrupted/rolled-back identity storage could still associate retained
recipes with reused IDs; this is local data corruption, not demonstrated remote
reachability. The service-removal cleanup above reduces stale data. Do not claim
all arbitrary edits to local profile files are an attacker isolation boundary.

## Extension and website exposure: protections and missing proofs

Pinned `browser/.../parent/ext-tabs.js:721-740` validates extension URLs with
`context.checkLoadURL` before creating, passing the extension principal. There is
no custom extension message bridge or exposed content command to the terminal
module. Existing native principal test rejects a normal website loading terminal
chrome; new native safety tests prove actual docShell mismatch/private rejection.
No universal extension privilege bypass was found in this source pass.

Missing negative integration proof: real webpage iframe/top navigation/window.open,
HTML link/drop, ordinary extension tabs.create/update with terminal chrome,
content-script execution attempts in a terminal, and malicious share import.
Run isolated throwaway extensions only; do not grant system/experiment privileges
then call their expected power a browser escape. Shared-builder filtering protects
choices, not all callable native services.

## Navigation-away: deliberately still open

Terminal page pagehide/beforeunload detaches only its viewer. Tab attributes and
SessionStore custom ID retain shell ownership until final TabClose; unmark has no
callers. A terminal replaced with a website can therefore hide live work and the
website tab's later close kills that work. This preserves existing C05 lifetime
but is not a finished user experience. Do not add process destruction on navigation
or globally intercept all browser loads without a deliberate policy. Native test:
type a web URL into terminal, Back, duplicate after navigation, last close, quit,
and changed-container reopen. Measure exact PID and recipe counter throughout.

## Existing hardening retained

Session ID characters/length are bounded, tmux arguments are separated from shell
commands, exact session targets and profile-specific sockets prevent cross-profile
attachment/deletion. Same-ID owner reassignment is refused. Pending deletion
survives failure; unknown inventory cannot replace jobs. Known ended work requires
explicit Start again, with startup intent recorded before launch and a stricter
history marker for Undo Close. These protections are specific, not a complete
claim that terminal access is sandboxed: it intentionally runs as the local user.

Suggested proof bar: high reasoning for identity/import/deletion changes; focused
module tests plus actual native/browser/extension negative tests. No broad unrelated
Core tests. Product migration remains held while these end-to-end gaps are open.

## Authorized follow-up implemented: All Tabs native list only

Added `src/browser/components/tabbrowser/content/browser-allTabsMenu-js.patch`.
It consults the existing terminal recipe store and omits terminal identities at
this specific native website-container list. No second manager, command routing,
terminal opener or tab lifecycle changes were added.

Downloaded pristine Firefox155.0.1 and156.0 files from official Mozilla GitHub
release tags into `scripts/terminal-tabs/fixtures/firefox-alltabs`, with source URLs,
SHA256 and Git-blob hashes. `test-terminal-alltabs.mjs` verifies both receipts,
applies the patch with zero fuzz, then executes the actual patched menu callback.
Six cases passed across both versions: mixed identities retain only web rows,
web-only rows stay unchanged, all-terminal lists are empty; native commands,
labels and hide cleanup are preserved. No UI launched. Native entry-point
acceptance and inclusion in the test overlay/final packaged asset checks are
parent integration work, not claimed complete by this source test.

## Authorized follow-up implemented: incoming and outgoing share safety

Added the packaged `ZenShareSafety.sys.mjs` helper under the existing
`modules/zen/share` directory. Both the client validator and manager import path
check the complete nested document for parsed absolute HTTP/HTTPS addresses before
creating anything. The eager split-view import has the same whole-document check;
the final single-tab trusted-open method also refuses non-web addresses. Raw
control/space characters, backslashes, relative and protocol-relative addresses
are rejected rather than normalized into something unexpectedly valid.

Outgoing serialization excludes a tab carrying the terminal marker even when its
current URL looks HTTP(S). Genuine web tabs remain. An export with zero web tabs,
including a tree of empty folders after terminals were excluded, neither asks for
upload confirmation nor sends a request. The client independently refuses empty
uploads. Existing structure/schema validation, normal share UI, metadata and web
behavior remain upstream-owned.

`test-terminal-share-safety.mjs`: **63 passed**, executing the actual helper and
production client/manager methods with synthetic services (test-only private
method visibility changes). Tests include nested valid-then-invalid lists and
eager split import with no partial creation; chrome/resource/file/data/javascript/
about/FTP, malformed and ambiguous addresses; stale HTTP terminal marker; genuine
web serialization; empty export; and a permissive schema mock that cannot bypass
the new client check. No UI or network was used. Native156 import/export acceptance
and exact final packaged module matching remain parent integration work.

## Authorized follow-up implemented: close ownership

`ZenTerminalTabs` now recognizes the exact parsed terminal-page address, not a
string prefix. Destructive close handling requires an existing session record
whose owner matches the browser's actual non-private container identity. A saved
`zenTerminalOwnership` receipt carries the session ID and owner through ordinary
navigation, lazy restoration and tab duplication. Legacy exact terminal pages can
establish a receipt only when actual browser identity and existing record agree.
URL text or an old session-ID attribute alone is not permission to kill a job.
Rejected viewers also do not count as legitimate viewers keeping another job alive.

The explicit opener registers the owner before creating a tab. This keeps early
close protected even before the page's startup code runs. Failed fresh tab creation
cleans its own registration; a failed duplicate creation never destroys an existing
job. Window adoption, quitting, existing actual-final-TabClose semantics and native
folders/pins remain unchanged. The Firefox156 RunState import is preserved.

`test-terminal-close-ownership.mjs`: **16 passed** against the production class,
covering malformed prefix, wrong/private identity, invalid ID, ordinary web tab
without receipt, legitimate lazy/restored receipt, website navigation retaining
ownership, duplicate last-close, invalid neighboring view, adopted/quit/windowclose,
creation-before-page-start and failed addTab cleanup. Organization14, entrypoints21,
workspace-default4 and native-polish logic also passed. No UI launched. Parent
must rerun actual native last-close, duplication, lazy restore and Undo Close with
the rebuilt receipt code before final acceptance.

## Authorized follow-up implemented: visible navigation-away ownership

The builder decision preserves native navigation and C05 process lifetime. An
owned terminal tab displaying a website now receives one native per-tab,
non-modal notification and a native **Return to terminal** context-menu action.
Website address, favicon and page security controls are not overridden. The
persistent-session wording explains final-close ownership; non-tmux wording says
its unsaved connection disconnected rather than promising live recovery.

Return reconstructs the internal address only from verified actual-container
ownership and a still-existing setup. It includes `started=1`, so return cannot
authorize a fresh recipe after the old process ended. There is no global redirect,
modal warning or process destruction on navigation. A dismissed notice is saved
in SessionStore for that session/owner and stays dismissed over web reload/restore;
returning to the real terminal clears the dismissal for the next away journey.
A native tab progress listener and restore/select events update the UI without
polling. The per-window deletion observer only removes obsolete UI and is removed
on window unload; shared process observers remain in SessionManager.

`test-terminal-navigation-return.mjs`: **14 passed** for notification/message,
one notice, persisted dismissal, context-menu return, started-marker address,
no automatic load/kill/icon changes, next journey, plain-helper wording, private/
wrong-owner/unowned refusal, deletion cleanup, late notification race and observer
teardown. Existing close16, organization14, entrypoints21/workspace4 also passed.

Added `test-terminal-navigation-macos.py` (syntax checked, NOT launched by this
worker). It drives actual address-bar typing and rendered notification controls,
Back/reload, persisted dismissal through quit/restart, native context return and
final close with exact shell PID/startup counters. Bookmark/URL-drag/mirrored-away/
non-tmux native journeys are explicitly not_run until separately exercised; module
logic is not substituted for those native acceptance cases.

### Independent follow-up: navigation ownership and callback review

Read the implemented return action, progress listener, saved dismissal, observer
cleanup and final-close ownership scan again. No confirmed privilege bypass or
new process-destruction path was found. Return reconstructs the terminal address
from the existing receipt and actual browser identity, rechecks the live record
at click time, and adds `started=1`; it never grants restart consent. Dismissal
belongs to one tab's saved data, not the shared job, so another copy keeps its
notice. Last-close detection scans all live browser windows, including trusted
website views retaining the receipt.

Expanded production-class tests (synthetic browser services; no native UI):

- `test-terminal-navigation-return.mjs`: **22 passed**. New checks cover ignored
  subframe navigation, an unstarted receipt, a formerly valid button after pending
  deletion, public identity removal, late append completion after close/deletion,
  independent dismissal across two views, and multiselect menu hiding.
- `test-terminal-close-ownership.mjs`: **19 passed**. New checks cover an away
  owner in another live window and private/wrong-container copies that must not
  prevent the real last owner from ending its job.

Native notification source calls the `dismissed` callback synchronously inside
`dismiss()`. A delayed native dismissal callback was therefore not treated as a
confirmed race. Remaining low-impact uncertainty: the product removes its window
observer/listener on unload, but does not explicitly invalidate an already-pending
notification append solely because the whole window unloaded. Native append has
its own disappearing-document error handling, and no automatic shell launch or
kill is reachable from that completion. This is not claimed as native acceptance.
The parent's actual navigation journey remains the evidence for rendered native
controls, quit restoration and real process lifetime.
