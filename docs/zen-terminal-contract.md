# Zen Terminal Contract — build rules

These rules preserve the recovered founder intent.

## C01 — R01
Keep real Zen navigation, browser tabs, folders and workspaces; terminal tabs belong to native containers.

## C02 — R02
On first use, include a plain Terminal container with an empty startup recipe (phase2 B). Do not recreate it after deliberate deletion.
Native Settings is the single place to create web or terminal containers; mixed launch list, no duplicate terminal menus.

## C03 — R03
A terminal accepts every keystroke exactly once, Unicode and paste; Ctrl-C, arrows and fullscreen programs work.

## C04 — R04
Live terminal ownership belongs to the actual profile folder, not copied tab IDs. Copied profiles cannot attach to or delete the original profile's running terminals. Legacy shared-server sessions remain untouched.
A running session survives reload, app quit/relaunch and app crash; recipes do not rerun on reattachment.

## C05 — R05
Explicit tab close or container deletion destroys only the matching session; failed cleanup remains retryable.

## C06 — R06
Missing tmux permits a plain shell but visibly says session saving is unavailable; full Mac reboot recovery is deferred.

## C07 — R07
Startup steps can be added, removed and reordered; local commands run in sequence; SSH must connect before remote commands run.

## C08 — R08
Reject ambiguous connection steps rather than running remote commands locally; preserve old recipes.

## C09 — R09
Smooth bounded output rendering, correct terminal size on resize, usable copy and paste.

## C10 — R10
Custom app has a distinct identity and no stock auto-updater; no global security weakening or changes to normal Zen.

## C11 — R11
Test the actual installed test app, not only file contents or mocked tests. Use isolated profiles and disposable sessions.

## C12 — R12
Keep original product scope. No Core integration, agent decision engine, isolated agent accounts, recipe recording, auto labelling, or forced remote permission bypass.

## Release honesty
Never describe planned, mocked or source-only proof as a real app pass. Native browser chrome requires Firefox automation (Marionette) alongside Playwright rendered-page checks. Final proof must use the actual packaged build. Keep dev/test profiles separate. Do not ship credentials or test sessions. Session saving depends on tmux and ends at a Mac reboot. Standard agent permission prompts stay intact; examples must not automatically disable them.

## C13 — Personal setup copy, clean distributable (R13)
Copy every registered existing Zen profile to the private personal installation, preserving cookies, saved-login/key files, bookmarks, history, workspaces, tabs, containers, extensions and settings. Copy, never move. Never include this data in source, tests, installer or releases. Use a fresh separate destination and preserve profile names. Refuse shared source/destination, overwrites, active source/destination profiles, path escape and symlinks. Refuse engine downgrade; no --allow-downgrade. Verify copied critical files using hashes without revealing their contents. Test only synthetic credentials. Profiles are copied only with Zen closed, so SQLite databases and session files agree. Some sites may require reauthentication.
### Clarification Refresh unknown

- Added: `2026-09-07T21:51:57Z`
- Artifact: `contract`
- Reason: R13 direct founder instruction supplies complete personal migration intent; no new question needed.
- Update note: C13 forbids shared profiles, overwrites, active copying and downgrade
- Impacted index tags: `ZT-MIGRATE`
- Contradiction review: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-q-and-a-contradiction-review.md`


## C14 — complete product acceptance (R14, strengthens C01/C02/C11)
Passing isolated terminal checks does not establish the complete browser experience.
Use the workflow inventory in zen-terminal-product-review.md. Preserve native mixed
folders, workspaces, pins and split views; distinguish saved setups from running
sessions and whole-browser profiles. Every relevant entry point, destructive action,
recovery state and visual state requires scoped evidence or an explicit limitation.
Reopen broad proved labels; do not erase historical passing evidence. Hold personal
migration until the complete product review passes, even if original Zen closes.


## September19 implementation rules — R15
C15 (R01/R14/R15): tab marking must preserve pin, Essentials, group, workspace and
native saved pin state. Hide terminal URL-reset decoration only. Website behavior
unchanged. Actual permanent tab removal follows C05; pinned reset/unload does not.
C16 (R02/R07/R14/R15): saved setup has optional absolute startingDirectory; blank
means home, native folder picker and editable path. No shell/environment expansion
of this path. Missing/inaccessible directory prevents all configured commands in a
new session. Opening an existing live session ignores later setup edits. Setup
edits never mutate existing jobs. Legacy stored recipes remain readable.
C17 (R10/R14/R15): explicit terminal launch only; ordinary NewTab/link/navigation
remain web. Private windows refuse persistent terminals. Actual browsing identity
and immutable session ownership must agree with requested setup; no cross-owner
reattach/deletion. Browser profiles stay separate. No secrets in diagnostics.
C18 (R11/R14/R15): preserve native appearance in light/dark/compact and small split
panes; inspect screenshots, keyboard paths and focus. All full-product matrix rows
need evidence or an explicit supported-limit statement; latest compatible engine,
clean packaging and upgrade/rollback proof precede personal deployment. Public
notarization requires a real Apple identity; never impersonate one or weaken macOS.
### Clarification Refresh unknown

- Added: `2026-09-19T11:04:24Z`
- Artifact: `contract`
- Reason: R15 explicitly approves autonomous implementation; recovered original requirements and labelled conservative implementation decisions resolve build behavior, not acceptance evidence.
- Update note: C15-C18 define native preservation, safe saved directories, security entry points and complete acceptance
- Impacted index tags: `ZT-MIGRATE`, `ZT-UI`, `ZT-LIFE`, `ZT-RECIPE`, `ZT-RELEASE`
- Contradiction review: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-q-and-a-contradiction-review.md`
