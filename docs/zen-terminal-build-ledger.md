# Zen Terminal Build Ledger

This file tracks the implementation step-by-step against the contract.

## Meta

- Project: `Zen Terminal`
- Source Q&A: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-q-and-a.md`
- Plan: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-plan.md`
- Contract: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-contract.md`
- Index: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-index.md`
- Checklist: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-build-checklist.md`
- Backtests: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-backtests.md`
- Build started: `2026-09-07T21:34:14Z`

## Steps

### Step 1

- Added: `2026-09-07T21:58:34Z`
- Contract ref: `C03 C09`
- Index tag: `ZT-IO`

#### Summary

Native Mac terminal helper replaces script/Python launch; framed lossless input and resize, bounded output, Unicode split-event repair, reconnect and clear failure display.

#### Files Changed

- none recorded

#### Verification

- 10 real native-helper tests, 13 persistence tests, 24 recipes, polish tests and 9 Playwright rendered-page checks pass; native Mac test app creates Settings container, types repeated Unicode, reloads, quits/relaunches and closes session successfully.
### Step 2

- Added: `2026-09-07T21:58:34Z`
- Contract ref: `C04 C05 C06 C07 C08`
- Index tag: `ZT-LIFE`

#### Summary

Serialized session creation/deletion, durable delete requests, unknown-versus-absent distinction, bounded tool timeouts, atomic startup ownership and safe recipe grouping.

#### Files Changed

- none recorded

#### Verification

- Independent review findings fixed; 13 executing persistence tests include isolated real tmux and failures, 24 recipe tests execute real shells and fake nested SSH.
### Step 3

- Added: `2026-09-07T22:15:20Z`
- Contract ref: `C07 C08`
- Index tag: `ZT-RECIPE`

#### Summary

Bounded command grouping and SSH validation, ordered dialog editing and visible save errors.

#### Files Changed

- none recorded

#### Verification

- 24 executing recipe tests and real native Settings reject unsafe SSH, reorder steps, save and execute both commands.
### Step 4

- Added: `2026-09-07T22:15:20Z`
- Contract ref: `C01 C02`
- Index tag: `ZT-UI`

#### Summary

One-time plain Terminal choice; real native container form resizes when editing; lazy restore marks terminal tabs on actual restore/select events.

#### Files Changed

- none recorded

#### Verification

- Actual native Mac proof covers default choice, Settings, menus, keyboard, fullscreen editor, local CLI version starts, resize, name persistence and app restart.
### Step 5

- Added: `2026-09-07T22:15:20Z`
- Contract ref: `C13`
- Index tag: `ZT-MIGRATE`

#### Summary

Private copy preserves all five registered profile slots; an unused times-only profile is valid; never copies a live source.

#### Files Changed

- none recorded

#### Verification

- 22 synthetic tests pass; personal dryrun reaches correct safe stop because stock Zen is running. No personal copy performed.

## Stable browser upgrade started
C10–C13 / ZT-RELEASE, ZT-MIGRATE: preserved prior branch6fd14b2, created separate stable1.22b working copy. Prior cloud run34165359251 failed importing upstream UrlbarUtils patch; no installer produced. Fresh upstream source avoids stale unrelated browser patch edits. Prior screenshots remain historical integration evidence only until repeated on155.0.1. Settings changes independently assigned; no personal profile copy or original app mutation.

### Stable focused proof
24 recipe cases,14 persistence cases (including real profile isolation),22 safe-copy cases,10 native helper cases, Unicode/polish checks and10 rendered-page checks passed in stable working copy. Native155 app Settings and fresh installer remain unproved. Safe dependency patch updates reduce npm audit from7 to2 findings: remaining high entries are the build-only Surfer/sharp image processor chain; no compatible automatic fix is published by npm audit. Do not process untrusted third-party image assets through this build tool. Runtime browser assets do not ship node_modules.

### Stable native Mac integration proved, installer still pending
Official Zen1.22b engine with strict source overlay passed14 actual Mac checks, including native Settings, repeated Unicode, Ctrl-C, vi, resizing, reload/quit persistence and explicit close. Its ad-hoc test signature preserves ordinary browser capabilities but removes official Apple-team-only entitlements; never impersonates the upstream signing team. This remains overlay proof, not installer acceptance. Verified development DMG signing/seal and refusal to overwrite using a tiny synthetic app. Migration now25 tests including final installation-hash default selection. Added upstream MIT notice for vendored xterm6.0.0/addon-fit0.11.0 to the shipped assets. Cloud34167253933 intentionally cancelled before compile to include optimized-ZIP inspection and Finder metadata fixes.

### Native visual and safety follow-up
Fixed shared Settings editor horizontal overflow exposed by screenshots; helper text wraps, action buttons remain visible, command input shrinks correctly. All20 native stable-overlay checks now pass, including geometry, ordinary website rejection, duplicate-close preserving other view, background lazy restoration with rename, Codex/Claude version commands and previous interactive tests. Source patches still apply cleanly and9 Settings behavior tests pass. Cloud34167720005 cancelled before compile so this final visual correction is included. No user data touched. Final installer remains pending.

### Real rename and crash review
Actual Mac crash test passed: only the test browser was killed; saved terminal kept its process and recipe did not rerun. A coverage review found the fast overlay was missing the changed ZenUIManager module and tests used its label setter rather than the native rename editor. Corrected harness coverage exposed a real Escape bug: terminal click-away saving also saved on Escape. Production now restores the prior input on Escape before blur, retaining normal cancel behavior. Cloud34167975669 cancelled during source download before compile to include correction; final native rerun pending. Inspector now checks browser integration module bytes and native menu as well as terminal assets.

### Final local source freeze
25 actual native stable-overlay checks now pass, including real rename Enter/click-away/Escape, explicit temporary app-data isolation, actual app crash and all earlier interactions. Final focused rerun also passed24 recipe,14 persistence,9 Settings,25 safe-copy,10 native helper and10 rendered-page tests plus wiring/polish checks. These results justify a final source build, not personal-copy completion. Added a real-app profile-selection test; only syntax/help/unsafe-app rejection have run so far because it requires final compiled identity. It must run at the final installed app path before personal copying.

## September 8 compiled identity correction
Cloud34168510949 imported all stable source patches and passed focused tests, then failed configuration:155 project_flag MOZ_APP_PROFILE accepts an implied source value, not an exported mozconfig value. Moved the isolated zen-terminal default into the existing toolkit/moz.configure source patch and removed rejected export. This is the same C10/C13 requirement, not a relaxation. Added wiring regression to reject the invalid export. No installer was produced and no private data copied.

## Full compile passed; final packaging corrected
Cloud34169782381 completed the full Firefox155/Zen build, then packaging failed because the manual wildcard found plugin-container.app and put the helper inside the wrong app. The main browser is reassembled from dist/bin for every package pass. Native helper now uses the browser's own standalone Program build declaration, and MacOS-files.in explicitly sends it into main Contents/MacOS. Pinned pristine155 assembler tests cover two complete bundle rebuilds and helper placement/execution/linkage. Workflow saves a fully dereferenced main app as a separately labelled raw recovery download BEFORE packaging; it is not a validated installer. Packaging now directly runs browser and multilanguage package commands and stops on actual failures, without invoking or ignoring stock updater-file generation. Original source build is proved; corrected full native build/package integration and final Mac acceptance still pending. No personal data copied.
