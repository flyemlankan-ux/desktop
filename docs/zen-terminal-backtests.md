# Zen Terminal Backtests — required checks

## B01: C01
Check: Keep real Zen navigation, browser tabs, folders and workspaces; terminal tabs belong to native containers.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B02: C02
Check: Native Settings is the single place to create web or terminal containers; mixed launch list, no duplicate terminal menus.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B03: C03
Check: A terminal accepts every keystroke exactly once, Unicode and paste; Ctrl-C, arrows and fullscreen programs work.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B04: C04
Check: A running session survives reload, app quit/relaunch and app crash; recipes do not rerun on reattachment.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B05: C05
Check: Explicit tab close or container deletion destroys only the matching session; failed cleanup remains retryable.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B06: C06
Check: Missing tmux permits a plain shell but visibly says session saving is unavailable; full Mac reboot recovery is deferred.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B07: C07
Check: Startup steps can be added, removed and reordered; local commands run in sequence; SSH must connect before remote commands run.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B08: C08
Check: Reject ambiguous connection steps rather than running remote commands locally; preserve old recipes.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B09: C09
Check: Smooth bounded output rendering, correct terminal size on resize, usable copy and paste.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B10: C10
Check: Custom app has a distinct identity and no stock auto-updater; no global security weakening or changes to normal Zen.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B11: C11
Check: Test the actual installed test app, not only file contents or mocked tests. Use isolated profiles and disposable sessions.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## B12: C12
Check: Keep original product scope. No Core integration, agent decision engine, isolated agent accounts, recipe recording, auto labelling, or forced remote permission bypass.
Record both successful use and a failed/forbidden path. Proof source: focused tests plus packaged-app exercise where applicable.

## Browser / Playwright proof
Exercise the real terminal.xhtml and xterm files in Playwright with a local disposable shell bridge; record 1280x800 and 800x600 screenshots, exact text input including repeated letters and Unicode, paste and selection, resize/reflow and streaming output. This supplements but does not replace the Mac app. Use Marionette for privileged Firefox chrome: create/edit/delete containers, open via menu, normal new web tab, tab rename and workspace movement, close and quit/relaunch with disposable sessions. Capture actual packaged app screenshots and result JSON. Do not claim native menus were tested by a DOM mock.

## Failure cases
Lost/duplicated input; shell startup fails; page closes while awaiting subprocess; malformed preference data; unreachable SSH never executes the remote command locally; command substitution stays at its intended host; tmux missing/broken, unknown session existence, explicit deletion followed by rapid restore, no unwanted recipe rerun, ordinary Zen untouched, updater absent. Large pasted and streamed data must stay bounded and ordered.

## Current evidence
September 7 baseline: check-terminal-tabs, session persistence, 20 recipe tests and terminal polish tests pass. These do not prove the real app works. Cloud rebuild run 34163489997 started for baseline recovery.

## B13 — personal copy without data loss or disclosure
Synthetic multi-profile fixture preserves names, default selection, nested profile data and key/cookie files byte-for-byte; source hashes unchanged. Reject source/destination overlap, existing destination, locked profiles, escaping paths, symlinks and incompatible older engine. Aborted copies leave no published partial destination. Distributable scans contain no profiles/cookies/key4/logins. Actual private copy waits for source browser to close and occurs only after compatible packaged build passes. Record metadata and counts, never credential values.
### Clarification Refresh unknown

- Added: `2026-09-07T21:51:57Z`
- Artifact: `backtests`
- Reason: R13 direct founder instruction supplies complete personal migration intent; no new question needed.
- Update note: B13 synthetic failure cases and private hash verification
- Impacted index tags: `ZT-MIGRATE`
- Contradiction review: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-q-and-a-contradiction-review.md`
