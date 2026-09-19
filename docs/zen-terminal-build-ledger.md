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


## September 8 — founder reopens full product acceptance (R14)

The founder rejected functional-only completion and required every end-to-end
workflow and native visual quality to be planned/researched/built properly.
Recorded as an affected-area rewire, preserving prior decisions and evidence.
Personal migration is now on hold for product readiness, not just source closure.
Broad `proved` labels were reopened; ready_for_build is false during this review.

Recovered the original handoffs: native folders, workspaces and a saved starting
folder were already required. Checked official Zen workspaces, split-view,
window-sync and shortcuts documentation against local pinned code. Recorded a
complete workflow inventory and eight ordered delivery slices in
`zen-terminal-product-review.md`, covering entry points, saved setups, mixed
organization, recovery, visual/accessibility, security, load, packaging and migration.
This is an audit/planning slice, not a claim those workflows are implemented.

Actual installed-app diagnostic reproduced a concrete missed defect: after placing
a web tab and terminal in a native folder, selecting the terminal unpins it and
removes it from the folder. The web tab remains; shell remains alive. Native folder
creation pins tabs; terminal restore/selection marking forcibly unpins them.
Evidence: `proof/2026-09-08-product-audit/mixed-folder-diagnostic.json` and screenshot.
Reproducer `audit-terminal-native-grouping.py` exits nonzero on the existing bug.
It uses native methods, not pointer actions, and is explicitly labelled diagnostic.
All browser/profile/session state was synthetic; only owned test sessions cleaned.
No production source, installed app or personal profile was modified.

Next: close affected-area product rules/coverage before implementation, then
repair native organization with regression and actual drag/drop+restore proof.
Recommended reasoning high; proof strong focused native lifecycle/organization
checks, not unrelated broad Core regressions. Drift check: preserve Zen's single
native model; do not create a second terminal dashboard or call failed old
requirements new features.

### 2026-09-19 — C15–C17 implementation and first native review (ongoing)

Founder authorized autonomous completion. Full product-review plan remains on
Chubs; the local pointer is `zen-terminal-plan-location.md`.

Implemented native organization preservation, saved starting folders, immutable
session ownership, deliberate/private entry checks, and explicit restart consent.
These are working-tree changes under review, not final release acceptance.

Parent independently ran the latest disposable app: ten native-method mixed-project
checks passed (two independent shells, folder selection/collapse/reorder, workspace
move, split/resize/unsplit, mirrored second window, window-close survival, precise
final-tab cleanup). Evidence: `proof/2026-09-19/project-review-project-workflows.json`.
Pointer drag/drop was explicitly not run. Inspected screenshot: native layout is
retained, but address field exposes an ugly internal query string; visual acceptance
is NOT complete. The independent grouping test passes selection/pin/unpin but
fails Essentials; investigation remains open. Rendered-page testing passes first
seven checks then fails helper cleanup count after the new folder scenario.
These failures are not waived. Eight packaged-resource verifier checks pass.

Next: resolve both failures, native setup/recovery journeys, pointer actions and
visual polish, then upgrade to current Zen/Firefox and rebuild cleanly. Latest
upstream sharing features need explicit terminal-data exclusion review.
Reasoning: high. Proof: strong focused lifecycle/security/native checks, plus
fresh-package end-to-end acceptance before personal migration.
Drift: native Zen remains the product; passing method calls is not complete UX
proof. No personal data or installed application changed in this slice.

Follow-up proof: rendered-page failure resolved in test only. Playwright default
page.close skips unload handlers; secondary test pages now run real unload and
wait for their exact helper to exit without killing it. All 12 rendered checks
pass, including lost-session explicit consent/reload and copied-profile isolation.
Current evidence moved to `proof/2026-09-19/terminal-page-results.json`; original
tracked September7 evidence restored. Future outputs use current UTC date or an
explicit proof folder. Independent current module suite passes recipes27,
persistence19, ownership6, entrypoints19, organization8 and Settings12.
Native safety first two checks pass; real Mac alert dismissal testing remains
under investigation. Native saved setup first run proves missing-folder refusal,
layout containment and literal save; its PID lookup was corrected, then a separate
first-open dialog race was found. Neither pending native journey is marked passed.

Native saved-setup journey now passes all9 checks on the latest overlay: invalid
folder cannot save, long literal folder stays inside dialog, startup/shell cwd match
exactly, two opens are independent, cancel preserves setup, edits affect only new
jobs, reopen retains replacement folder. Native chooser interaction is NOT yet
covered. Screenshots inspected: native form retained but tall/wordy; further polish
and keyboard/chooser proof required. Latest icon fix has focused mock assertions
(organization10, entrypoints21, workspace-default4); no duplicate pseudoglyph.
Essentials failure isolated to legitimate upstream separate-container rule:
workspace0 versus terminal6 is ineligible, so native add returns false. Diagnostic
will test this refusal plus shared-Essentials preference explicitly; no production
bypass or broader success claim. False updater-toast default now applied from
source into overlay; actual release must compile the same preference.

Native safety now9pass with one explicit private-modal NOT_RUN. Actual rendered
restart clicks and Undo Close retain marker/require consent; lost/reload never
rerun commands silently. Evidence safety-overlay-v7-safety-workflows.json. Visual
inspection confirms honest ended-session message and visible Start again; native
icon is still overwritten on location change after reload, repair in progress.

Firefox156 preparation: parent retargeted only common Settings import anchor;
all5 production patches strictly apply and all12 Settings behavior tests pass on
BOTH155 and156 hash-verified fixtures. This does not prove new156 site-association
UI or native156 packaging. Official1.22.2b DMG hash verified and copied to disposable
storage; no installed app changed. Upstream merge not yet performed.

Security source review found additional non-accepted paths: All Tabs builds its own
container list (shared menu filter does not cover it), extension removal can bypass
terminal Settings cleanup, and156 sharing can import arbitrary URI through trusted
creation. These are source findings, not claims of demonstrated remote execution.
All Tabs strict-fixture repair is underway; extension cleanup and sharing remain
release blockers pending scoped implementation/proof. No acceptance narrowing.

Important packaging correction discovered by native proof: overlay/verifier were
checking UNUSED copies of pin/workspace managers, not the browser's registered
locations. Corrected to `chrome/browser/content/browser/zen-components/ZenPinnedTabManager.mjs`
and `modules/zen/ZenSpaceManager.mjs`, verified against jar/build/preloader and
actual official archive. Preparer now refuses nonexistent module destinations.
Added regression: a correct unused copy cannot hide a stale actually loaded module.
All9 verifier tests pass. Previous broad workflow results remain genuine observations
but do NOT prove these manager changes were exercised; corrected-overlay reruns
are required. Native Essentials itself restored same PID; status-text test was stale.

### September19 — current-engine integration and additional safety

Committed reviewed first repair set6a8c5c4, retained pinned fixtures ec0aa10,
and merged official1.22.2b at fa4e0d7 (upstream04e7db5...). Actual engine156.0,
Rust1.95.0. This is a source merge, NOT a final release. Corrected155 overlay
now passes full native organization/Essentials/shared preference/restart diagnostic;
see organization-correct-resources-native-organization.json.

C17 implementation continued: all nested share imports require absoluteHTTP(S)
before mutation, terminal-marked exports excluded, empty uploads refused (63cases);
service deletion exact-job cleanup and single shared-loader coordinator (8cases
including realtmux); close ownership with realcontainer/receipt validation and
creation-close race coverage (16cases);156 site-association selector+commit guards
(21cases/3strictpatches). All remain subject to native acceptance. Rendered page12
still passes. New AllTabs6cases pass155/156. Firefox156 native packaging fixtures
are independently pinned by Gitblob+SHA256; all7 files happened to match155bytes,
but provenance is refreshed and full inherited destination code is now verified;
actual assembler4cases pass. Verifier10cases now checks actual registered managers,
share modules and7 patched native UI assets, not unused copies.

Built a NEW disposable156 output (never reuse155 executable), validates strict
signature and sourcebytes. RunState import moved to actual156 moz-src path.
First native156 project run proves startup/folders but realpointer reorder fails;
recorded as failure, not replaced by method acceptance. Separate method-only suite
is running to find unrelated regressions. Installed app/personal profiles untouched.
Next highreasoning/strongproof: native156 full lifecycle/negative tests, pointer
input and missing visual/native-picker checks, clean compiled release and rollback.

Current156 native results: saved-setup9checks pass, including actual currentworking
folder; mixed-project11checks pass after correcting test-only removed Firefox
_tabposition field (`_tPos` -> actual tabs array position). Workspaces/split/mirrored
windows/finalclose all preserve correct PIDs and recipe counts. Pointer run is
separate and still unaccepted; do not count native methods as drag proof.
New native negative scripts for service deletion, web/extensions and156 menus are
written but pending actual runs. Full current source suite passes; new tests also
wired into cloud workflow. Current engine156 overlay verifies actual sourcebytes
and signatures. No personal copy, installed app change, signing claim or final
release acceptance.

Current156 main native suite passes input, Ctrl-C, full-screen editor, installed
Codex/Claude version starts, resize, duplicate-view retention, rename/save/cancel,
reload, lazy restore, quit/relaunch, actual browser crash, and exact finalclose.
Current156 service-deletion native7checks pass including shared observer across
windows, creation/deletion race, actual direct non-tmux child cleanup and durable
retry. Web/ordinary-extension native6checks pass: same-container iframe/top/popup
cannot open terminal chrome; ordinary extension create/update refuse; rejected
wrong-context tab cannot kill a known orphan job. Compatibility native checks now
pass actual AllTabs lists,156 association lists/acceptance stalechoice refusal,
ordinary native NewTab supplied-address command routing to0, and packaged shared
client nested unsafe URLs refusal/safeHTTPS acceptance. Test-only readiness and
newcommand API assumptions were corrected, not product assertions waived.

Post-build UI source additions: bounded literal scrollback search (same released
xterm6 commit, npm integrity+license verified), nonfatal input-rejection state,
reduced motion, and native Return-to-terminal notification/contextmenu while
navigated away. Rendered page13checks pass including literal search not reaching
shell. Native UI proof still pending these new additions. Cloud dev build
35441216400 started at34375b2; it predates these additions and cannot be treated as
final current-source delivery without a subsequent build/package step.

### 2026-09-19 — native search/navigation acceptance and fresh-build failure

- Rebuilt the disposable official-engine156 overlay with all14 terminal assets; exact registered-resource verification and ad-hoc signature checks pass. This remains an overlay, not a compiled release.
- Native navigation journey `navigation156-navigation-workflows.json`: eight actual-browser checks pass, including real address-bar entry, native Return button, Back, dismissal/reload/restart, context-menu Return and exact final-close cleanup. Bookmark/URL-drop/mirror/direct-mode cases remain explicitly not run.
- Native keyboard journey: corrected a test-only injected-JS brace syntax error (first run failed). v2/v3 passed real Cmd+F/Ctrl+F isolation, literal search/no shell execution, reconnect/reload focus, same process and narrow light/dark layout. Motion-off asserted cursorBlink=true, but native evidence shows media=false and smoothScroll=80 while cursorBlink=false; programs may request a steady cursor. Removed that invalid assertion, retaining reduced-motion no-blink checks. Additional escape-output audit underway; no product motion waiver.
- Cloud35441216400 failed before compilation because Mozilla requires sorted EXTRA_JS_MODULES names. Reordered Manager/Safety entries without changing behavior; added four passing declaration checks and workflow preflight. It is not a successful build.
- Plan remains on Chubs; original Zen/profile untouched. Next handoff: high reasoning for native input/lifecycle failures; real browser proof plus focused source regression, fresh compiled-package tests required. Drift: no replacement browser shell, no claims that synthetic profile tests prove personal migration.
