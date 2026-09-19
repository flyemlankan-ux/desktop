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
| ZT-IO | C03 C09 | exact input and terminal rendering | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-plan-location.md for the full plan on Chubs. Personal migration on hold until product review closes.` |
| ZT-LIFE | C04 C05 C06 | session lifetime and cleanup | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-plan-location.md for the full plan on Chubs. Personal migration on hold until product review closes.` |
| ZT-RECIPE | C07 C08 | ordered startup recipes | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-plan-location.md for the full plan on Chubs. Personal migration on hold until product review closes.` |
| ZT-UI | C01 C02 | native containers and tab behavior | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-plan-location.md for the full plan on Chubs. Personal migration on hold until product review closes.` |
| ZT-RELEASE | C10 C11 C12 | isolated packaging and delivery | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-plan-location.md for the full plan on Chubs. Personal migration on hold until product review closes.` |
| ZT-MIGRATE | C13 | private profile copy | `blocked` | `implemented` | 26 synthetic safety tests; private hash checks; compatible native browser launch | automated | no | no | ZT-RELEASE | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-plan-location.md for the full plan on Chubs. Personal migration on hold until product review closes.` |
| ZT-ORGANIZE | C15 | mixed native organization | `in_progress` | `implemented` | Native mixed-project10 pass; Essentials/shared restore in review; pointer proof pending | automated/native | no | no | none | Preserve native rules; method-call tests are not pointer UX acceptance. |
| ZT-SETUPS | C16 | saved starting folders | `in_progress` | `implemented` | Native Settings9 pass; literal folder/cwd and edits proved; native picker pending | automated/native | no | no | none | Existing jobs ignore later invalid edits; no shell expansion of paths. |
| ZT-SECURITY | C17 | deliberate entry and session ownership | `in_progress` | `implemented` | Native safety9 pass plus explicit private-modal not_run; module negatives pass | automated/native | no | no | none | Keep lost-session restart consent. Full sharing/extensions/navigation audit pending. |
| ZT-PRODUCT | C18 | complete review and current-engine release | `in_progress` | `partial` | Full plan on Chubs; latest156 fixtures prepared, one strict patch incompatibility found | automated/native/manual | no | no | ZT-ORGANIZE ZT-SETUPS ZT-SECURITY | No final deployment or personal migration until acceptance. |
