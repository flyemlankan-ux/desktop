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
| ZT-IO | C03 C09 | exact input and terminal rendering | `proved` | `proved` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `September 8:26 checks pass on actual installed recovered development app; real DMG inspection and ten rendered-page checks. Not Apple-notarized; manual updates. High reasoning, strong native proof.` |
| ZT-LIFE | C04 C05 C06 | session lifetime and cleanup | `proved` | `proved` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `September 8:26 checks pass on actual installed recovered development app; real DMG inspection and ten rendered-page checks. Not Apple-notarized; manual updates. High reasoning, strong native proof.` |
| ZT-RECIPE | C07 C08 | ordered startup recipes | `proved` | `proved` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `September 8:26 checks pass on actual installed recovered development app; real DMG inspection and ten rendered-page checks. Not Apple-notarized; manual updates. High reasoning, strong native proof.` |
| ZT-UI | C01 C02 | native containers and tab behavior | `proved` | `proved` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `September 8:26 checks pass on actual installed recovered development app; real DMG inspection and ten rendered-page checks. Not Apple-notarized; manual updates. High reasoning, strong native proof.` |
| ZT-RELEASE | C10 C11 C12 | isolated packaging and delivery | `proved` | `proved` | Targeted unit/process tests; Playwright rendered display and native packaged browser interaction proof | automated | no | no | `none` | `September 8:26 checks pass on actual installed recovered development app; real DMG inspection and ten rendered-page checks. Not Apple-notarized; manual updates. High reasoning, strong native proof.` |
| ZT-MIGRATE | C13 | private profile copy | `blocked` | `implemented` | 26 synthetic safety tests; private hash checks; compatible native browser launch | automated | no | no | ZT-RELEASE | `26 safety tests plus actual final-path profile selection pass. Personal copy waits only for original Zen to close; destination remains absent. High reasoning, full private hash/source-preservation checks.` |
