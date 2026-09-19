# Saved terminal setups: bounded source review

Date: 2026-09-19. Status: design ready for coordinator review; production unchanged.
Canonical complete product plan remains only on Chubs. This file is a focused implementation review, not a replacement or local copy of that plan.

## Source receipt

- Read the canonical Chubs product plan over SSH at `/home/chubs/zen-terminal/docs/zen-terminal-product-review.md`.
- Original `docs/terminal-tabs-step-one-handoff.md` explicitly requires name/color/icon, starting folder and startup recipe. This is missed existing scope, not a new product decision.
- C02/C08/C14 and saved setup versus live tab distinction apply; C04 requires no recipe rerun on reattachment.
- Current store `ZenTerminalContainerStore.mjs` saves v3 ordered steps but normalizes away any folder. Current page launches in HOME. Settings has no folder control.
- Current page compiles updated steps before determining whether the old session exists. A malformed edited preference can therefore prevent reconnect to an otherwise healthy old session. Folder validation must not repeat this mistake.
- Existing native picker pattern: `ZenBoostsManager.sys.mjs` creates nsIFilePicker, initializes with parent browsingContext, opens callback. Local Gecko interface declares `modeGetFolder`, `displayDirectory`, `returnOK`.
- State is currently not ready for build. Coordinator must finish the affected-area update before implementation.

## Proposed user journey

In the existing Terminal section of the native container editor:

1. Add labelled **Starting folder** plain text input and **Choose folder…** native macOS folder picker.
2. Explain: **Leave blank to start in your home folder. Use a full path, such as /Users/you/Projects.** Folder picker cancellation does not alter the input or save anything.
3. Explain: **Changes apply to new terminal tabs. Running terminals keep their current work.**
4. Keep ordered commands separate below. No second setup manager and no secrets fields.
5. Save/cancel remain the existing native dialog actions. Invalid folder syntax or inaccessible/non-directory path produces an inline labelled error without creating/updating an identity. Recheck before creating a new shell because folders can disappear after saving.
6. Existing sessions reconnect without validating or applying the newly edited folder or command rows. New independent tabs use the new saved values.
7. Missing folder on launch shows a recoverable error telling the user to restore it or edit the setup, then reconnect. Never silently fall back to HOME.

## Data and safety details

- Add `recipe.startingDirectory` string, blank by default for legacy v2/v3 recipes; bump format to v4 explicitly. Preserve existing legacy one-command conversion, step IDs/order, and unknown records belonging to other containers.
- Preserve folder text exactly, including valid spaces at the start/end of a filename; do not trim a picked path. Reject nonempty relative paths, NUL/newlines/control characters, and invalid field types. Do not expand `$HOME`, `~`, shell substitutions or wildcard text. Blank alone means home. Show an actionable error instead of silently converting malformed explicit values to home.
- Use a shared syntax validator in a small new module (or recipe runner, if coordinator prefers fewer files). Do not concatenate an unquoted path into commands.
- Use native file checking (exists/isDirectory, with caught access errors), not shell `test` from Settings. A picker supplies `file.path`; a typed path passes the same checks.
- For launch, set direct process `workdir` or tmux `new-session -c` using the path as one distinct argument. Also use a safely single-quoted `cd -- PATH || exit` guard before configured startup commands to handle login startup files that change directory and a folder disappearing between check and launch. A path is data, never a startup command.
- Folder check occurs before launching a new process. The shell guard closes the later race without running configured startup steps in the wrong folder. User shell initialization files are still ordinary user-owned shell behavior; do not claim none of those can execute.
- Under the per-session serialized creation path, check whether the session exists before invoking a lazy callback that reads/validates current new-session options. This prevents changed/missing folders or invalid edited recipes from blocking attachment. Snapshot the options once for creation; no hot updates to live jobs.
- Direct non-tmux mode always creates a new job and validates current settings. Keep its no-persistence warning.
- Choose folder callback must ignore results after editor/document closes. Disable/re-enable only the picker button while open; do not cause auto-save or selection of a Web kind.

## Exact proposed ownership

Production:
- `src/zen/terminal/ZenTerminalContainerStore.mjs` — v4 normalization/storage.
- `src/zen/terminal/ZenTerminalRecipeRunner.mjs` — shared folder validation/quoting helpers if not separate module.
- `src/zen/terminal/ZenTerminalSessionManager.mjs` — lazy new-session options, validated cwd and shell guard.
- `src/zen/terminal/ZenTerminalPage.mjs` — new-session snapshot/validation, recovery error and direct-mode cwd.
- `src/browser/components/contextualidentity/content/ContainerEditor-mjs.patch` — native folder input/picker, validation and save.
- If a new module is selected: `src/zen/terminal/ZenTerminalStartingDirectory.mjs` plus its `jar.inc.mn` entry.

Proof owned by this slice:
- `scripts/terminal-tabs/test-terminal-recipes.mjs` — legacy migration, exact path preservation, rejection and quoting.
- `scripts/terminal-tabs/test-terminal-settings155.mjs` — fixture patch applies, picker success/cancel/error, invalid folder writes nothing, cancel preserves configuration, persisted edit/reopen.
- `scripts/terminal-tabs/test-terminal-session-persistence.mjs` — real tmux cwd and two distinct jobs; editing live setup affects only new job; missing edited folder does not block live reattach; missing initial directory runs no configured command.
- Coordinator-owned native Mac test extension should exercise real rendered editor and real picker separately; worker will not launch UI without coordination.
- Playwright terminal page test fixture may need new options mocks; coordinate rather than silently weakening the bridge.

## Required adversarial cases

1. Legacy strings/v2 command/v3 ordered recipes remain equivalent, folder blank.
2. Valid spaces, Unicode, apostrophe, dollar/backtick/semicolon characters are literal filesystem names; sentinel command never executes from path text.
3. Relative path, NUL/control character, non-string field, file instead of directory, deleted folder, inaccessible folder fail before any configured command or new session.
4. Folder disappears after preflight: guarded command fails closed, no configured startup marker.
5. New terminal A and B have different session IDs and initial PID, same requested cwd, recipe once each.
6. Edit setup folder/commands while A runs; A continues and reconnects unchanged; newly opened C uses updates.
7. Edit to missing folder or malformed command by synthetic preference mutation; A reconnects, C fails safely.
8. Picker cancel and dialog cancel do not modify saved recipe/name/color/icon.
9. Reorder/delete steps and save folder together, reopen, restart synthetic profile, verify durability.
10. Actual small-window, dark/light and keyboard focus checks for the rendered folder row. Inspect screenshots; unit DOM mocks cannot establish appearance or macOS picker behavior.
11. Startup file that changes cwd must not cause configured commands to run in the wrong folder; document ordinary user shell initialization and final prompt behavior precisely.
12. Existing delete/change-to-Web warnings and exact cleanup remain unchanged.

## Proof status and cleanup

Read-only audit only. No production files changed, tests run, UI launched, credentials read, or personal profiles touched. One focused report added. No canonical plan copied back to the Mac.

Recommended next handoff: high reasoning, focused unit/process safety tests plus real native Settings/picker and terminal journeys on synthetic profiles. Do not mark the slice accepted from this report or source tests alone.
