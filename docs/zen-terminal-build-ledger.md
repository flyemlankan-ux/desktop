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
