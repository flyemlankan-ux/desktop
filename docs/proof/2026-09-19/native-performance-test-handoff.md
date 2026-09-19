# Native performance acceptance test — prepared, not run

`test-terminal-performance-macos.py` is ready for the parent's exclusive UI slot. No browser was launched for this slice. Production source is unchanged.

## What the real source permits us to measure

- Existing isolated native tests already verify the exact browser PID, profile directory and app-data directory through Marionette (the browser's test-control connection).
- `gBrowserInit.delayedStartupFinished` plus `gZenTerminalTabs` gives a meaningful browser-ready point, not merely process existence.
- The actual terminal surface exposes `terminal-ready`; the shared session manager supplies a profile-specific tmux socket. Exact tmux jobs can be checked without affecting other sessions.
- The real xterm instance can be observed using the constructor observer already used by the native keyboard test. The constructor still runs unchanged. This proves bytes arrived in the actual terminal buffer, not that every pixel was painted.
- Page `readPipe` awaits xterm's write callback for each chunk. Real simultaneous shell output exercises this path and browser-main-thread responsiveness.
- macOS process counters supply cumulative CPU and resident memory for the owned browser and its descendants. Add the verified profile's detached tmux server and its descendants. Never collect other applications' arguments, paths or UI.
- Native contextual-identity removal exercises production cleanup, then exact job absence and record deletion can be measured.

## Proposed acceptance budgets

These are explicit initial acceptance limits, **not measured results**. They are intentionally generous smoke limits for this Mac and must not be marketed as hardware-independent guarantees.

| Measurement | Budget | Reason |
|---|---:|---|
| Launch to browser ready | 20 seconds | A clean profile plus driver handshake must not look stuck; includes test-control overhead. |
| Each real terminal ready | 8 seconds | Allows first helper/tool discovery but catches unusably slow launch. |
| Six terminals ready, total | 30 seconds | Independent jobs must remain practical to create. |
| Browser plus six idle terminals | 25% of one CPU core | Idle work should leave most of a single core free; normal multicore percentage is not substituted. |
| Extra idle CPU versus same-run browser-only baseline | 15 percentage points | Separates browser startup/background work from terminal idle overhead. |
| Extra aggregate resident memory for six terminals | 512 MiB | Broad guard against runaway allocation; not a physical-memory claim because shared pages are counted repeatedly. |
| Six bounded output bursts complete | 10 seconds | About 2.3 MiB total actual PTY output should not stall the browser. |
| Main-thread heartbeat p95 / maximum during burst | 150 / 500 milliseconds | A 50ms heartbeat should normally remain responsive; any half-second block is flagged. This is not compositor frame timing. |
| Six-job native cleanup | 10 seconds | Removal must finish promptly and not leave test jobs behind. |

Idle measurements wait 3 seconds to settle, then sample for at least 8 seconds, every 250ms. CPU includes only positive cumulative-counter deltas. Very short processes can be missed. RSS and CPU values remain in the report even if a budget fails. Budget failures do not prevent collecting later independent measurements; the script ultimately exits nonzero.

Output is six actual `/usr/bin/awk` commands, each 4,096 fixed-width lines plus a unique final marker. The final marker must appear as its own line near the tail of each real xterm buffer, preventing the echoed command itself from satisfying completion. No network, package install, user files or unbounded output is needed.

## Safe run

Parent must own the only UI slot:

```sh
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 -B \
  scripts/terminal-tabs/test-terminal-performance-macos.py \
  --app '.terminal-test/Zen Terminal Test 156.app' \
  --label native-performance156
```

Prefer the genuinely compiled separate fork for final acceptance. The overlay is useful preliminary evidence only. The test rejects an unexpected engine or headless environment, uses a new synthetic home/profile/app-data, and checks ownership before interacting with terminal jobs. Normal cleanup uses the actual native setup deletion service. Failure cleanup kills only recorded exact test session names, never a shared tmux server. Browser shutdown is scoped to the process launched by this script.

Repeat at least three times on the final compiled app with no overlapping UI tests. Keep all runs, median and worst values. Do not silently loosen limits after a failure; first identify host load, test overhead or a real product bottleneck. Broad browser startup, thermal behavior, long-running sessions, energy impact, compositor smoothness and low-memory machines remain separate acceptance work.

## Proof completed here

- Python syntax parsing: pass.
- `--help`: pass, no app launched.
- macOS CPU time parser: four offline cases pass, including day/hour forms.
- Actual bounded awk payload: 4,097 lines, 397,330 bytes in the offline fixture; pass.
- Native timings, CPU, memory, six-tab burst and cleanup budgets: **pending, not measured**.

## Slice recap

1. We now have a runnable, isolated performance smoke test with explicit limits.
2. This slice added measurement and honest failure reporting, not production optimizations.
3. The overall goal remains normal Zen browsing with dependable integrated terminal tabs.
4. No native performance pass, hardware-wide benchmark or smooth-animation claim was created.
5. Offline checks validate script syntax, counter parsing and bounded output only.
6. Next: parent runs the test in its exclusive UI slot, then repeats on the final compiled app.
7. Drift check: the test measures actual jobs and browser responsiveness; it does not redefine the product around synthetic benchmark scores.

Recommended handoff: medium reasoning for an ordinary run; high reasoning if a budget fails. Proof level: actual isolated macOS app plus real terminal jobs, then three final-build runs before release acceptance.

## Investigation after parent runs (no additional UI launched here)

The parent's `performance156-fixed.log` records a **failed** 12.2866605-second burst against the unchanged 10-second limit. Its maximum browser heartbeat was about 80ms, and native cleanup completed in about 0.312 seconds. An earlier run reportedly completed the burst in about 6.22 seconds. These are variable preliminary results, not a reason to silently relax the limit. Existing evidence files remain untouched; the script now refuses to overwrite an existing result label.

Source inspection finds a plausible explanation to measure, not yet a proven diagnosis:
- The shipped xterm write queue uses `setTimeout` to start or continue `_innerWrite`, including yields after roughly 12ms of parsing.
- Production Page `readPipe` awaits each xterm write callback before reading another chunk.
- Five of six test terminals are background tabs. If their document timers are throttled, browser responsiveness can remain good while background terminal ingestion is slow.
- The original burst measurement also included twelve sequential tmux client invocations (literal input plus Enter per job) and repeated test-control polling. It did not separate producer completion from viewer completion.

New diagnostic metrics, without changing the 10-second budget or product code:
- Each tab's command-dispatch start/finish and separate literal/Enter subprocess durations.
- Total dispatch duration.
- A synthetic per-job file written only after awk finishes flushing to its real PTY. Its modification timestamp gives producer-side completion relative to burst start; it does not claim xterm has consumed those bytes.
- Per-tab selected/hidden state, xterm parsed-event count and last parsed time.
- Per-tab final-marker observation time, sampled every 100ms from the browser chrome window rather than six hidden-page timers.
- Total sampler execution time, allowing measurement overhead to be seen rather than ignored.

The sampler observes actual xterm buffers and does not switch tabs, force callbacks, alter throttling preferences, or change scheduling. Completion is still a full exact marker line, not the command echo. Filesystem marker times use wall-clock time and browser completion uses browser monotonic time; they are diagnostic offsets, not a nanosecond-accurate cross-clock trace.

### Separate stock Firefox156-based Zen comparison

The same harness has `--stock-baseline`, which runs only launch and browser-only idle measurements, with identical fresh-profile/app-data isolation and settling/sample durations. It requires an explicit **copied official app under this project's `.terminal-test`**, matching the expected official bundle identifier and binary. It refuses the original installed-app path. It never controls, quits or examines the already-running original Zen.

Parent, in its exclusive UI slot:

```sh
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 -B \
  scripts/terminal-tabs/test-terminal-performance-macos.py \
  --stock-baseline --app '.terminal-test/Official Zen 1.22.2b.app' \
  --label stock156-performance-baseline-1
```

This official copy's platform.ini was read without launching: Milestone156.0, binary `zen`. The actual launched PID, profile and app-data must still be verified during the future run. A stock browser cannot provide terminal burst comparison; compare launch/idle values only. Run stock and fork sequentially, preferably three interleaved repetitions, preserving every result. Do not make an overhead claim from one noisy pair.

Current proof of these improvements: Python syntax and help pass. **No new native performance or stock comparator run occurred in this slice.** Recommended handoff: high reasoning to interpret producer/viewer/hidden-tab evidence; actual isolated native runs with the unchanged acceptance budget. Drift check: do not optimize test timing by forcing background tabs foreground or disabling normal browser behavior.
