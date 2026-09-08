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
| ZT-IO | C03 C09 | exact input and terminal rendering | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-product-review.md. Personal migration on hold until product review closes.` |
| ZT-LIFE | C04 C05 C06 | session lifetime and cleanup | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-product-review.md. Personal migration on hold until product review closes.` |
| ZT-RECIPE | C07 C08 | ordered startup recipes | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-product-review.md. Personal migration on hold until product review closes.` |
| ZT-UI | C01 C02 | native containers and tab behavior | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-product-review.md. Personal migration on hold until product review closes.` |
| ZT-RELEASE | C10 C11 C12 | isolated packaging and delivery | `in_progress` | `implemented` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-product-review.md. Personal migration on hold until product review closes.` |
| ZT-MIGRATE | C13 | private profile copy | `blocked` | `implemented` | 26 synthetic safety tests; private hash checks; compatible native browser launch | automated | no | no | ZT-RELEASE | `R14: complete product acceptance reopened; previous narrow test evidence retained. See zen-terminal-product-review.md. Personal migration on hold until product review closes.` |
