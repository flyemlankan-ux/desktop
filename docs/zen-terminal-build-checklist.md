# Zen Terminal Build Checklist

This is a short progress checklist, not a copy of the full plan held on Chubs.
The C-number labels refer to that plan. Source checks, tests on a locally modified browser, and tests on a freshly compiled package are separate kinds of evidence.

## Status Meanings

- `todo`: not started yet
- `in_progress`: active implementation or partial implementation exists
- `blocked`: cannot proceed until a dependency or clarification is resolved
- `proved`: implemented and explicitly verified enough to count as proved

## Checklist

| Tag | Contract Area | Area | Checklist Status | Index Status | Planned Proof | Proof Class | Human Signoff | Probation Required | Dependencies | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ZT-IO | C03 C09 | exact input and terminal rendering | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Current156: source workflow35 commands pass; rendered bridge13 pass; native main26 and keyboard/search10 pass; bounded-output native performance3 repeats pass. Trusted Gecko composition/search passes 3 runs × 5 checks; OS clipboard, OS input-source candidate UI/dead keys and final compiled-app replay remain open. |
| ZT-LIFE | C04 C05 C06 | session lifetime and cleanup | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Current156 native main26 includes reload/relaunch/crash/final-close; mixed-project11 includes mirror/last-view cleanup; navigation8 passes preserve away/return ownership. Final compiled-app acceptance still required. |
| ZT-RECIPE | C07 C08 | ordered startup recipes | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Current156 saved-setup9 and real trusted Chubs SSH4 checks pass; harmless remote ordering and exit23 failure-stop proved. No authenticated/paid AI-agent command invoked. |
| ZT-UI | C01 C02 | native containers and tab behavior | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Current156 main26, saved-setup9, grouping10 and mixed-project method11 pass. Actual pointer reorder passes 3 runs × 12 checks; drag-to-split remains open; owned AX folder picker remains open. |
| ZT-RELEASE | C10 C11 C12 | isolated packaging and delivery | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Zen1.22.2b/Firefox156 source and exact overlay assets14 verify; current build workflow35 commands pass. Compiled0c2b163 installer inspection and native main27 pass; real compiled app-only install/upgrade/rollback/removal12 pass. Both split repairs await full compiled5d12ee6 build35455394170 acceptance; notarization remains open. |
| ZT-MIGRATE | C13 | private profile copy | `blocked` | `implemented` | 26 synthetic safety tests; private hash checks; compatible native browser launch | automated | no | no | ZT-RELEASE | BLOCKED pending final product/package acceptance and original Zen closed. Synthetic155-to156 copy/open6 checks pass; original profiles untouched. Never downgrade copied data or include personal data in distributable. |
| ZT-ORGANIZE | C15 | mixed native organization | `in_progress` | `implemented` | Native mixed-project11/grouping10; pointer3×12, web-folder11×2 and mixed-folder8 pass | automated/native | no | no | none | Current156 grouping10 passes including separate/shared Essentials and same-shell restart; mixed-project method11 passes workspace/split/mirror. Pointer reorder repeats3×12 pass; nested web-folder Undo11 passes in both orders; mixed-folder rename/delete/Undo8 passes. Empty-history restart/clear/disabled each5 pass. Actual drag-to-split and full adoption matrix remain open; all are overlay, not final-package proof. |
| ZT-SETUPS | C16 | saved starting folders | `in_progress` | `implemented` | Native Settings9 pass; literal folder/cwd and edits proved; OS picker pending | automated/native | no | no | none | Current156 actual Settings9 pass; literal folder/cwd, save/cancel, independent jobs and edits proved. Compact dialog screenshot reviewed; native macOS picker Choose/Cancel still unproved. |
| ZT-SECURITY | C17 | deliberate entry and session ownership | `in_progress` | `implemented` | Native compatibility11, web-isolation6, private refusal3 and navigation8 pass; broader matrix open | automated/native | no | no | none | Current156 compatibility11, web-isolation6 and actual private alert refusal3 pass; native navigation8 passes. Production share-import UI/negative validation10 passes with loopback service transport; live service/account behavior, broader extension interactions and remaining navigation inputs remain open. |
| ZT-PRODUCT | C18 | complete review and current-engine release | `in_progress` | `partial` | Full plan on Chubs; current156 strict fixtures and exact overlay assets verified; compiled acceptance pending | automated/native/manual | no | no | ZT-ORGANIZE ZT-SETUPS ZT-SECURITY | Current156 engine upgrade/strict fixtures complete; source workflow35, bridge13 and paired performance baseline plus3 bounded-output repeats pass. Final compiled identity/package and remaining full-product acceptance open; keep in_progress. |

## Latest evidence boundary

Source checkpoint: `0c2b163`. Exact workflow commands: 35/35 pass in `proof/2026-09-19/final-folder-source-regression.{json,log}`. Native progress receipts and remaining gaps are summarized in `proof/2026-09-19/current156-source-and-remaining-acceptance.md`. Counts include fixture/ownership checks, not unique features. No broad C18 or release completion is claimed. Personal copy remains blocked; the original profiles are untouched.


### Later compiled checkpoint

Compiled0c main27 and real delivery12 pass; sourceaudit38/38 pass (`post-split-source-regression.json`). Native split failure-state proves actual mixedsplit and samejobs after repair, but automated premature-release ordering remains a strict failure, not accepted gesture. Native picker failed twice even with correct compiledidentity; remaining OS/manual checks and personalmigration stay open. See compiled0c-native-acceptance and compiled-app-delivery-lifecycle reports.
