# Zen Terminal Coverage Matrix

Recovered source decisions, not fabricated interview answers.

| Q&A Answer | Short meaning | Role | Plan Area | Contract Clause | Index Tag | Backtest / Proof | Build Slice | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R01: step-one handoff: product and mental model | Keep real Zen navigation, browser tabs, folders and workspaces; terminal tabs belong to native containers. | enforced | ZT-UI | C01 | ZT-UI | B01 | ZT-UI | planned |
| R02: phase2 B | Native Settings is the single place to create web or terminal containers; mixed launch list, no duplicate terminal menus. | enforced | ZT-UI | C02 | ZT-UI | B02 | ZT-UI | planned |
| R03: test plan: keyboard and shell; July 4 input fix | A terminal accepts every keystroke exactly once, Unicode and paste; Ctrl-C, arrows and fullscreen programs work. | enforced | ZT-IO | C03 | ZT-IO | B03 | ZT-IO | planned |
| R04: phase2 A1 | A running session survives reload, app quit/relaunch and app crash; recipes do not rerun on reattachment. | enforced | ZT-LIFE | C04 | ZT-LIFE | B04 | ZT-LIFE | planned |
| R05: phase2 A1; existing SessionManager | Explicit tab close or container deletion destroys only the matching session; failed cleanup remains retryable. | enforced | ZT-LIFE | C05 | ZT-LIFE | B05 | ZT-LIFE | planned |
| R06: phase2 A1 | Missing tmux permits a plain shell but visibly says session saving is unavailable; full Mac reboot recovery is deferred. | enforced | ZT-LIFE | C06 | ZT-LIFE | B06 | ZT-LIFE | planned |
| R07: phase2 A2 | Startup steps can be added, removed and reordered; local commands run in sequence; SSH must connect before remote commands run. | enforced | ZT-RECIPE | C07 | ZT-RECIPE | B07 | ZT-RECIPE | planned |
| R08: step-one recipe execution; current recipe tests | Reject ambiguous connection steps rather than running remote commands locally; preserve old recipes. | enforced | ZT-RECIPE | C08 | ZT-RECIPE | B08 | ZT-RECIPE | planned |
| R09: phase2 D; build path | Smooth bounded output rendering, correct terminal size on resize, usable copy and paste. | enforced | ZT-IO | C09 | ZT-IO | B09 | ZT-IO | planned |
| R10: phase2 C; current packaging inspector; Sept 7 user autonomy | Custom app has a distinct identity and no stock auto-updater; no global security weakening or changes to normal Zen. | enforced | ZT-RELEASE | C10 | ZT-RELEASE | B10 | ZT-RELEASE | planned |
| R11: test plan proof levels; Sept 7 request to test everything | Test the actual installed test app, not only file contents or mocked tests. Use isolated profiles and disposable sessions. | enforced | ZT-RELEASE | C11 | ZT-RELEASE | B11 | ZT-RELEASE | planned |
| R12: step-one deferred scope; standalone project | Keep original product scope. No Core integration, agent decision engine, isolated agent accounts, recipe recording, auto labelling, or forced remote permission bypass. | enforced | ZT-RELEASE | C12 | ZT-RELEASE | B12 | ZT-RELEASE | planned |
| R13: direct founder request September 7 | Personal Zen setup copied; clean distributable | enforced | ZT-MIGRATE | C13 | ZT-MIGRATE | B13 | ZT-MIGRATE | planned |
