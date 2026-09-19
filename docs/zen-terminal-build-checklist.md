# Zen Terminal Build Checklist

This file turns index-tagged contract areas into actionable build slices.
Use it to choose the next contract-aligned implementation step and keep status honest.

## Status Meanings

- `todo`: not started yet
- `in_progress`: active implementation or partial implementation exists
- `blocked`: cannot proceed until a dependency or clarification is resolved
- `proved`: implemented and explicitly verified enough to count as proved

## Checklist

| Tag | Contract Area | Area | Checklist Status | Index Status | Planned Proof | Proof Class | Human Signoff | Probation Required | Dependencies | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ZT-IO | C03 C09 | exact input and terminal rendering | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Current156: source workflow30 commands pass; rendered bridge13 pass; native main26 and keyboard/search10 pass; bounded-output native performance3 repeats pass. OS clipboard/IME and final compiled-app replay remain open. |
| ZT-LIFE | C04 C05 C06 | session lifetime and cleanup | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Current156 native main26 includes reload/relaunch/crash/final-close; mixed-project11 includes mirror/last-view cleanup; navigation8 passes preserve away/return ownership. Final compiled-app acceptance still required. |
| ZT-RECIPE | C07 C08 | ordered startup recipes | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Current156 saved-setup9 and real trusted Chubs SSH4 checks pass; harmless remote ordering and exit23 failure-stop proved. No authenticated/paid AI-agent command invoked. |
| ZT-UI | C01 C02 | native containers and tab behavior | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Current156 main26, saved-setup9, grouping10 and mixed-project method11 pass. Native pointer completed once in earlier experiment but repeat not established; owned AX folder picker remains open. |
| ZT-RELEASE | C10 C11 C12 | isolated packaging and delivery | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | Zen1.22.2b/Firefox156 source and exact overlay assets14 verify; current build workflow30 commands pass. Latest source build0d0b370 in progress; compiled package/install/upgrade/rollback acceptance not complete. |
| ZT-MIGRATE | C13 | private profile copy | `blocked` | `implemented` | 26 synthetic safety tests; private hash checks; compatible native browser launch | automated | no | no | ZT-RELEASE | BLOCKED pending final product/package acceptance and original Zen closed. Synthetic155-to156 copy/open6 checks pass; original profiles untouched. Never downgrade copied data or include personal data in distributable. |
| ZT-ORGANIZE | C15 | mixed native organization | `in_progress` | `implemented` | Native mixed-project11 and grouping10 pass; repeatable pointer proof pending | automated/native | no | no | none | Current156 grouping10 passes including separate/shared Essentials and same-shell restart; mixed-project method11 passes workspace/split/mirror. Pointer repeat, nesting/rename/delete mixed-folder and full adoption matrix remain open. |
| ZT-SETUPS | C16 | saved starting folders | `in_progress` | `implemented` | Native Settings9 pass; literal folder/cwd and edits proved; OS picker pending | automated/native | no | no | none | Current156 actual Settings9 pass; literal folder/cwd, save/cancel, independent jobs and edits proved. Compact dialog screenshot reviewed; native macOS picker Choose/Cancel still unproved. |
| ZT-SECURITY | C17 | deliberate entry and session ownership | `in_progress` | `implemented` | Native compatibility11, web-isolation6, private refusal3 and navigation8 pass; broader matrix open | automated/native | no | no | none | Current156 compatibility11, web-isolation6 and actual private alert refusal3 pass; native navigation8 passes. Sharing negatives/source audits pass; full share-import UI/extensions and remaining navigation inputs not fully accepted. |
| ZT-PRODUCT | C18 | complete review and current-engine release | `in_progress` | `partial` | Full plan on Chubs; current156 strict fixtures and exact overlay assets verified; compiled acceptance pending | automated/native/manual | no | no | ZT-ORGANIZE ZT-SETUPS ZT-SECURITY | Current156 engine upgrade/strict fixtures complete; source workflow30, bridge13 and paired performance baseline plus3 bounded-output repeats pass. Final compiled identity/package and remaining full-product acceptance open; keep in_progress. |
