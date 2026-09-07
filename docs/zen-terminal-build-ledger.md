# Zen Terminal Build Ledger

This file tracks the implementation step-by-step against the contract.

## Meta

- Project: `Zen Terminal`
- Source Q&A: `/Users/ar/zen-terminal-research/desktop/docs/zen-terminal-q-and-a.md`
- Plan: `/Users/ar/zen-terminal-research/desktop/docs/zen-terminal-plan.md`
- Contract: `/Users/ar/zen-terminal-research/desktop/docs/zen-terminal-contract.md`
- Index: `/Users/ar/zen-terminal-research/desktop/docs/zen-terminal-index.md`
- Checklist: `/Users/ar/zen-terminal-research/desktop/docs/zen-terminal-build-checklist.md`
- Backtests: `/Users/ar/zen-terminal-research/desktop/docs/zen-terminal-backtests.md`
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
