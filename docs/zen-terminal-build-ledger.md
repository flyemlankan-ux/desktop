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

### Test-only isolation audit
Removed inherited XRE profile/restart and selectable-profile-reset environment variables before launching synthetic tests, since Firefox reads these before -profile. Main Mac test now checks the automation process ID and actual profile directory against its own child and disposable directory. All25 native checks passed again. Profile-selection script has the same pre-launch protection; its actual final-app run remains pending. No production source change or build restart needed. Active source build34183056904 uses19f7539.


## September 8 recovered build: inherited helper destination fixed

C10 / ZT-RELEASE. Cloud34183056904 (source19f7539) completed the browser compile
and uploaded the153MB raw-app recovery download, then failed the native helper
location check. The helper was compiled, but under
`Contents/Resources/browser/zen-terminal-pty`, not `Contents/MacOS`.
This was not an assembly-order race. Firefox's `browser/moz.build` exports
`DIST_SUBDIR = "browser"`; our `browser/base -> zen -> terminal` build inherited
it. My previous focused test supplied `dist/bin` directly and therefore missed
the real inherited setting. Its passing result did not prove full integration.

The terminal build now clears `DIST_SUBDIR` on Darwin, following pristine
Firefox155 `browser/app/moz.build`. The regression executes the exact pinned
upstream inherited-setting and destination-computation excerpts, then executes
our declaration. It uses the resulting directory when compiling the disposable
helper for the real upstream assembler, rather than inventing a staging path.
Before the production correction this test reproduced both the wrong destination
and missing main-app helper. Afterward all4 packaging tests passed, including two
bundle assemblies;10 PTY tests and wiring checks also passed. A negative control
still reproduces `dist/bin/browser` when the reset is removed.

Files changed in this slice: `src/zen/terminal/moz.build`,
`scripts/terminal-tabs/test-terminal-build-packaging.py`, this ledger. No commit
or full browser rebuild was performed in this slice. No personal data touched.
The recovered cloud helper is a regular0755 ARM64 executable, links only Apple's
libSystem, and can be moved into the correct location before re-signing and
full app testing. Recovery-helper SHA256:
`7c388b05baf8edb1514b1f55633f8d93d1647e59d98bc8e75eeacb65ac59fbb9`.

Next: parent owns recovery packaging and final native acceptance; these focused
checks do not substitute for those proofs. Recommended reasoning: high; proof:
whole-app signature/asset inspection plus actual native app behavior. Scope stays
Zen plus terminal; this slice adds no features or migration behavior.


## September 8 — recovered build packed, installed and proved; personal copy waits

Source receipt for C10/C11/C13: the agreed result is a separate blank app plus a
private copy of the founder's complete Zen setup. The full cloud compile19f7539
was saved successfully but needed real packaging. Build rule: never touch the
original Zen, never treat a merely signed raw app as native acceptance, and never
copy active profiles.

Recovered8406 files were verified against cloud run34183056904's saved archive.
The first recovered attempt exposed a real startup crash: Firefox's sandbox
setup tried to find the absent cloud build directory. Independent inspection
matched crash line2395. Removing plist keys alone is NOT sufficient: Firefox's
packaged-build check requires the genuine GRE resource archive. Pinned Firefox
155 mozpack now produces actual GRE+browser archives, removes the two upstream
developer-only plist keys and self-deleting cache marker, omits two exact fake
test-plugin directories, preserves43 native binaries before signing, and writes
provenance. Original archive and extracted input remain byte-identical. This is
not the complete mach package/multilocale release pipeline; retained native
build utilities and development signing are explicitly disclosed in provenance.
No sandbox permission was weakened and no dummy archive was used.

The source build also clears inherited DIST_SUBDIR so future full builds put the
helper in the correct main-app location. The independent regression reproduces
the original wrong-folder failure before that fix.

The inspector now requires both real archives with valid CRCs, engine resource
registration,12 exact terminal assets, exact native integration files, no build
machine plist keys, no self-deleting cache marker, isolated identity/profile,
no updater/private profile files, and whole-app strict signature. Eight targeted
verifier tests pass, including optimized Python rejecting invalid inputs.
Nine recovery tests pass. Pinned tool fetching was reproduced independently with
28 verified public source files. No uncompressed-layout acceptance remains.

Native browser proof initially clicked the form before Firefox's dialog-ready
promise settled. The test now awaits actual readiness plus layout frames, not a
forced click or arbitrary delay.26 native checks pass on the finished app AND
again on `/Applications/Zen Terminal.app`, installed directly from the inspected
DMG with file-by-file equality and atomic no-overwrite publication. Strict app
signature still passes after launch, quit, restart and crash tests. Ten rendered
page checks and10 cloud-compiled-helper process checks pass. CLI checks launch
Codex/Claude version commands only, not authenticated or paid agent work.

The final-path synthetic profile test exposed another real bug: Python emitted
`Name = value`, but Firefox's nsINIParser preserves those spaces. Firefox ignored
the intended profile and created a blank replacement. The copier now writes
both INIs without delimiter spaces.26 synthetic safety tests pass; a byte-level
regression fails with the old writer. Actual ordinary launch at the final app
path now chooses the intended copied profile, retains all three synthetic
profiles, and leaves the synthetic source unchanged. Target install hash:
`CA24B52DD8BD79BC`. This hash applies to this final installed path on this Mac.

Evidence: docs/proof/2026-09-07/packaged-macos-results.json,
installed-app.json, installed-profile-selection.json,
recovered-package-provenance.json, packaged-dmg-inspection.txt and source audit.
Historical failures are retained and explicitly labelled, not promoted to passes.

ZT-IO/LIFE/RECIPE/UI/RELEASE are proved for this private development distribution.
ZT-MIGRATE remains blocked on original Zen closing normally (PID699 last check).
No personal data has been copied. Destination `~/Library/Application Support/zen-terminal`
still does not exist; all app tests used explicitly isolated synthetic storage.
Do not launch the new app with ordinary personal settings before the copy unless
prepared to handle the copier's intentional no-overwrite refusal.

Next handoff: high reasoning, full private hash/source-preservation proof and
normal launch after copying with source engine152.0.5,target155.0.1 and the saved
install hash. Recheck source closure, versions and destination absence first.
Never quit the founder's original Zen automatically. Some sites may require
reauthentication. No Apple notarization or automatic update service is claimed;
manual tested browser rebuilds remain necessary for security updates.
Scope remains normal Zen plus terminal tabs; no Core integration or agent
permission bypass was added.
