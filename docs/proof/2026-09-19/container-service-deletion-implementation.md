# C17 / B17: container-service deletion cleanup

Implemented and focused checks pass. Native Firefox 156 app/service proof remains pending. No UI launch, merge or commit; personal profiles untouched.

## Source receipt and design

Independent `production-security-review.md` identified extension/service container deletion bypassing Settings-only cleanup. Verified the native `ContextualIdentityService` notification shape in packaged source: `contextual-identity-deleted` with `subject.wrappedJSObject.userContextId`.

Important additional finding: `ZenPreloadedScripts.js` imports browser modules with `{ global: "current" }`. A module-local observer/queue would not necessarily be shared across windows. The implementation therefore obtains its operation map and observer ownership from the **default shared ChromeUtils module loader**. Window/page imports delegate observer installation to that shared module so a long-lived observer does not retain the first browser window.

## Implementation

- SessionManager installs one profile-wide observer through existing startup retry and session registration calls. No Tabs bootstrap change required.
- Service deletion removes only the matching terminal recipe, synchronously records deletion intent for every matching visible/background session, and starts exact session cleanup. Settings' existing cleanup remains idempotent with this observer.
- Failures/unavailable tmux retain pending records for the existing startup retry. Production never uses kill-server.
- Shared per-session queues order creation and deletion across different window/module copies. If deletion occurs during creation, queued cleanup wins after the in-flight operation settles.
- A fresh session checks that its stored owner still exists as a public native identity and has a terminal recipe immediately before launch. Page startup refreshes identity/setup validation after asynchronous tool lookup. Removed setups cannot silently become a plain HOME shell.
- Exact per-session deletion notifications stop attached page helpers too, including direct non-tmux shells. Pages remove their listener when stopped; a late helper creation is killed by the existing stopping guard. Visible text honestly says cleanup was requested rather than claiming background work was already confirmed stopped.

## Files

Production:
- `src/zen/terminal/ZenTerminalSessionManager.mjs`
- `src/zen/terminal/ZenTerminalPage.mjs`

Proof/fixtures:
- New `scripts/terminal-tabs/test-terminal-container-deletion.mjs`
- `test-terminal-session-persistence.mjs`, `test-terminal-polish.mjs`: shared-loader/current-owner service mocks.
- `test-terminal-browser.mjs`: native bridge mocks updated; syntax checked only, no browser launched.

No ContainerStore, Tabs or manifest change required.

## Proof run

New deletion suite: **8 passing cases**, including:
1. Two separately imported window-like module copies install one shared observer.
2. Service deletion marks visible and background jobs immediately, preserves neighbor, and repeated notifications do not double-kill.
3. Missing tmux preserves durable intent; later startup retry completes.
4. Identity deletion during settings lookup creates no process.
5. Final check rejects missing native identity or recipe even without observer notification.
6. Deletion during creation in a different module copy wins, with neighbor intact.
7. Exact page notification stops only its matching helper and hides reconnect; late-helper guard retained.
8. **Real isolated tmux**: real production creation and service deletion stop the two matching jobs and preserve the neighboring job. Test-only final cleanup removes the server belonging to its freshly created temporary profile; production cleanup never does this.

Additional checks:
- 19 persistence cases, including isolated real tmux: pass.
- 6 owner-immutability cases: pass.
- 27 recipe cases: pass.
- 12 Settings cases + source patches: pass (this test's historical filename says155; do not infer new156 native acceptance).
- Terminal polish, wiring and syntax checks: pass.
- Entry-point/context21 + workspace4 cases: pass.

## Still unproved

Actual packaged Firefox156 deletion through native service/extension, multiple native windows and direct-helper stopping need parent-run app proof. Synthetic page-observer evaluation is not a real browser helper-stop pass. This slice does not fix or claim imported-share validation, close-owner receipts, updater delivery or complete product acceptance.

Reasoning level for handoff: high. Proof level: focused native deletion and in-flight failure journeys with synthetic identities, plus existing safety regression. No unrelated Core tests.
