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
