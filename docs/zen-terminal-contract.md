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
- Contradiction review: `/Users/ar/zen-terminal-research/desktop/docs/zen-terminal-q-and-a-contradiction-review.md`
