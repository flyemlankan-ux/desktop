# Current156 source checks and remaining acceptance

## What passed in this slice
Ran the exact current development workflow's test/build-helper command list plus terminal wiring: **35 commands, all exit0**. Includes current156 settings/associations, output pipeline, accessibility lifecycle, search/navigation, organization/entrypoints, deletion/concurrent cleanup, ownership/sharing, clipboard transaction safety (not OS clipboard), synthetic copy, actual helper compilation/PTY, signed tiny-DMG fixture, build ordering, pinned156 assembly/repack, install-manager safety, package privacy, packaging and verifier tests. Final frozen-source receipts: `final-folder-source-regression.{json,log}` (source committed as `0c2b163`). Includes 12 folder Undo groups, the no-op close guard, 11 asset-verifier tests, 18 reduced-motion cases and 13 rendered search-layout cases with the old failure reproduced as a negative control. Earlier receipts remain unchanged.

Ran exact current asset verifier on `.terminal-test/Zen Terminal Test 156.app`: **14 terminal assets, Firefox156.0, real GRE/browser resource layout**. Native patch fixtures selected by verifier are156 settings,156 associations and156 AllTabs; pristine155 files are retained historical baselines, not used to claim156 compatibility. This proves current overlay source bytes, not a fresh compiled product.

No native UI was launched for this source audit; parent-owned native receipts were inspected. Inspected `browser-pipeline/terminal-page-results.json`:13 checks, no error. Root-level `terminal-page-results.json` is a different overwritten diagnostic and must NOT be substituted for that passing receipt. Native regression counts: main26, saved9, grouping10, project-method11; keyboard10 plus2 explicit not_run; accessibility4 plus1 not_run; SSH4 plus1 not_run; compatibility11 plus1 not_run; synthetic155→156 migration6. Three pipeline-performance receipts each retain all10 measured checks. Counts include scope/setup checks and are not a count of unique product features.

New bounded native overlay evidence:
- Pointer reorder: `pointer156-ready{,-v2,-v3}-project-workflows.json`, three runs with 12 passing checks each. Actual pointer reorder is proved; drag-to-split is separate work and remains open.
- Folder Undo: `web-folders156-noop-standard-results.json` and `web-folders156-noop-childlast-v2-results.json`, 11 passing checks each, covering both descendant orders. `folders156-noop-final-results.json` has eight passing mixed-folder checks, including real Rename/Delete/Undo and explicit Start again without silent recipe rerun. Separate `web-folders156-orderfixed-{restart,clear,disabled}-results.json` receipts each pass five checks; clear/disabled use actual notification/preference methods, not Settings UI.
- Trusted Gecko composition and search: `input156-v{3,4,5}-results.json`, three runs with five passes and one explicit not_run each. This does not prove the macOS input-source candidate UI, dead keys or VoiceOver.
- Share import: `share-import156-extended-share-import.json`, ten passes and one explicit not_run through production validation/UI/import code with loopback service transport. No real service upload or account workflow was exercised.

These receipts test isolated Firefox156 overlay apps, not a newly compiled final package. Earlier failures remain available; passing replacements do not erase their history.

Local build checklist notes updated, all acceptance rows remain in_progress and personal migration remains blocked. No remote plan edits; its headings/inventory were read only.

## Release blockers / incomplete full-product acceptance
Grouped under the canonical remote plan's headings, without copying its plan onto this device:
- **Delivery:** completed fresh source build for current code, exact compiled identity/resources, clean real package, required language/license contents, install/update/rollback/remove on disposable data, then key native journeys on that package. The current overlay does not replace these.
- **Group / Split / Windows:** repeatable pointer reorder now passes three times. Actual drag-to-split and the remaining adoption/move matrix still need evidence. Nested mixed-folder rename/delete/Undo and ordinary-web folder edge checks now pass in the bounded journeys above; do not generalize them to every window/group arrangement.
- **Save setup:** actual macOS folder-picker Choose/Cancel flow still blocked in overlay Accessibility attempts, although literal folder/editor flows pass.
- **First launch / Open / Workspace / Security:** remaining real-input launch surfaces, live share-service/account behavior, extension interactions, and workspace/change/remove cases beyond the tested folder fallback must be reconciled against the full remote inventory rather than marked complete from module tests. Website separation6, private refusal3, compatibility11 and navigation8 are strong bounded evidence, not blanket acceptance.
- **Personal copy:** remains blocked until release acceptance and original browser closed. Synthetic6 does not authorize or prove actual personal login migration. No private copy done.
- **Public signed/notarized distribution:** requires legitimate Apple signing/notarization credentials and successful final submission/verification. A sealed development DMG is not notarized. This is an external dependency, not a silently approved deferral.

## Manual / not-run coverage (not automatic waivers)
- OS clipboard content/format/race-safe journey remains not_run; helper transaction tests alone are not actual clipboard acceptance.
- OS input-source candidate UI/dead keys, VoiceOver spoken output, full keyboard-only task traversal. Trusted Gecko composition has three passing repetitions, but is not the complete OS IME journey. Browser accessibility objects and motion checks are not substitutes.
- Navigation via actual bookmark and URL drag/drop, mirrored-window away notice and non-tmux native wording are explicit not_run rows in navigation receipt.
- Appearance matrix still needs review across final compiled identity, accents, compact/fullscreen/split/narrow views; selected small-window screenshots are only that subset.
- Authenticated or paid AI-agent launch deliberately not invoked. Real harmless SSH and CLI --version do not prove account/tool workflows.
- Intel build acceptance is not established by an Apple Silicon run; do not advertise an untested target.

## Explicit supported limits / approved deferrals already recorded
- Full Mac reboot recovery is deferred; current persistence covers browser/process lifecycle with tmux, not OS reboot resurrection.
- Clickable links/file-path launch were previously deferred in the remote inventory; do not add unsafe implicit launch as cosmetic polish.
- A terminal setup is not a separate OS user or security sandbox; it shares the user's machine/tool environment.
- Non-tmux fallback is explicitly unsaved; closed/killed jobs cannot honestly be revived by undo.
Any additional gap needs a named supported-limit decision, not relabeling it deferred here.

## Cloud snapshot and next handoff
At this documentation handoff, parent reports current-source run35448450404 (`0c2b163`) in progress, with the two older runs still compiling. This is a reported snapshot, not an independently refreshed cloud status or a successful build receipt. No build success, cancellation or dispatch is claimed.

Next: parent monitors source build and closes compiled-package/native acceptance. High reasoning for security, migration and native input; focused evidence plus final-package tests. This slice changed only evidence/checklist, not production behavior. UI was not launched; original browser/data untouched. The remaining work stays aligned with the full Zen experience, not just a narrow terminal demo.
