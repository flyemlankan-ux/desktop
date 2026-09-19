# Current156 bounded-output native retest

These are local smoke measurements from disposable profiles on the same Mac, not hardware-independent guarantees. The app uses official156 compiled code plus current terminal resources; final compiled-fork replay remains required.

| Stage | Run | Six tabs ready (s) | Output complete (s) | Worst heartbeat (ms) | Cleanup (s) | Result |
|---|---:|---:|---:|---:|---:|---|
| before | 1 | 1.13 | 9.36 | 70.3 | 0.20 | PASS all 10 checks |
| before | 2 | 0.97 | 11.30 | 64.6 | 0.17 | FAIL: initial 10s output limit |
| before | 3 | 0.97 | 12.36 | 70.7 | 0.17 | FAIL: initial 10s output limit |
| after | 1 | 0.98 | 4.15 | 87.7 | 0.18 | PASS all 10 checks |
| after | 2 | 1.00 | 3.21 | 93.2 | 0.17 | PASS all 10 checks |
| after | 3 | 0.98 | 4.22 | 79.6 | 0.18 | PASS all 10 checks |

The controlled output is about2.3MiB spread across six actual PTY/tmux jobs. Before the change, producer completion was about0.12s and the selected terminal parsed in about0.2–0.3s, but hidden documents parsed roughly once per second. The new pipeline keeps callbacks and strict per-stream256KiB/64-write bounds while allowing several chunks to share one parsing turn. No browser-global timer rules changed.

All three post-fix runs passed the unchanged budgets. A browser-main-thread heartbeat is not compositor frame timing, VoiceOver responsiveness or a power-consumption measurement. Aggregate RSS double-counts shared pages; negative differences versus browser-only baseline reflect ordinary startup/background variation, not negative memory usage.

Stock156 launch/idle receipts are retained separately as stock156-paired-{1,2,3}-results.json. One stock idle run exceeded the same provisional25%-of-one-core threshold by0.31point. The first stock launch was cold-ish; repeated launch results are not rigorously cache-controlled. Do not claim the fork is faster than stock from these samples.

Next handoff: medium reasoning for routine final-build replay, high for a failed budget. Repeat real native workload three times; keep failures and inspect per-tab/producer measurements before changing any limit.
