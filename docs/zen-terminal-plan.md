# Zen Terminal Plan

## Build order
- ZT-IO: first reproduce typing, process startup and resize problems; fix the narrow input/process layer. Reasoning: high. Proof: real local shell + Playwright rendered terminal, negative cases, full app follow-up.
- ZT-LIFE: session creation, attachment, quitting, closing and retryable deletion. Reasoning: high. Proof: failure injection and real disposable tmux processes, followed by packaged app lifecycle tests.
- ZT-RECIPE: validate ordered commands and preferences editing. Reasoning: high. Proof: local/remote sequencing fixtures, malformed and failed commands, actual dialog interactions.
- ZT-UI: unified container menus and normal Zen tab behavior. Reasoning: medium. Proof: targeted source checks + Playwright display checks + native browser interactions and screenshots.
- ZT-RELEASE: package, identity, updater exclusion, test fresh app with isolated profile; write install/recovery instructions. Reasoning: high. Proof: all focused suites plus real Mac app end-to-end, no unrelated Core regressions.

## What stays out
No redesign of Zen, new agent platform, Core connection, automatic agent permission bypass, public release signing without credentials, or reboot-proof live processes. No rebase of the full Firefox/Zen engine hidden inside a terminal bug fix; report inherited engine freshness separately.

## Source receipt
Original handoffs describe a proven early prototype plus a July 25 phase-two build. That build compiled; its hands-on acceptance is unconfirmed. Existing tests mostly check source strings and mocked services. Current code drops identical characters less than 25 ms apart and has startup/close races. Start by reproducing, never claim the project already passed based on old notes.

## ZT-MIGRATE — private personal setup
After clean packaged-app proof, run a dry-run inventory of registered Zen profiles and compatibility. Provide a fail-safe copy utility and synthetic tests first. Only copy once source Zen is closed. No automatic quit of the founder browser. Preserve an untouched source fallback. Reasoning high; proof strong synthetic failure cases, file-hash checks and targeted private post-copy checks with no password/token output. This is personal deployment, not a feature that embeds founder data in the product.
### Clarification Refresh unknown

- Added: `2026-09-07T21:51:57Z`
- Artifact: `plan`
- Reason: R13 direct founder instruction supplies complete personal migration intent; no new question needed.
- Update note: Added isolated personal copy after packaged app proof
- Impacted index tags: `ZT-MIGRATE`
- Contradiction review: `/Users/ar/zen-terminal-research/desktop-stable/docs/zen-terminal-q-and-a-contradiction-review.md`

Compatibility update: stock Zen reports Firefox 152.0.5. The prior terminal engine was 152.0.3. Build against 152.0.5 and use a non-downgrading app version; never bypass Firefox profile protection. Upstream development currently targets 155.0.1, so this is compatibility parity, not a claim of current public-release security maintenance. A full upstream rebase remains separate and must not be concealed.

## Explicit stable-browser upgrade — September 7
The 152.0.5 build failed because inherited upstream address-bar patches no longer applied. Independent source review found stable Zen 1.22b (pinned 4f3bcb2f3254c33a14ef7f16f6a125f27709b76d) uses Firefox 155.0.1. Under the user's autonomous completion instruction, ZT-RELEASE now explicitly includes a separate stable working copy, terminal-only transplant, native Settings port and complete fresh-app verification. This supersedes the earlier compatibility-parity plan, not the original-browser safety rules. Old branch remains preserved at 6fd14b2.

Source receipt: C10–C13 require a distinct safe personal app and blank installer. The current terminal works in the old test app but its browser engine is outdated. Build rule: retain upstream stable browser code, add only terminal integration, preserve all profile-copy safeguards, and do not describe prior-app evidence as proof of this new build. Reasoning: high. Proof: focused logic/native tests, new Settings failure cases, packaged real-Mac tests and private-copy verification.
