# Concurrent final-close cleanup

## Observed failure

The native six-terminal performance run ended all six jobs but left one durable
`pendingDelete` record after 30 seconds. Its saved profile and
`performance156-v2-results.json` establish the symptom, not the precise tool error.

A new isolated actual-tmux regression reproduced the failure in round two of six
concurrent deletions. Its subprocess adapter captured `list-sessions` returning
exit 1 and `server exited unexpectedly`. Two deletion records remained pending.
The last server was shutting down while other deletion checks queried it.

Before log: `.terminal-test/concurrent-cleanup-before.log`.

## Fix

Only deletion's inventory checks now retry an unknown result after 100 ms and
then 250 ms. The operation remains inside the existing per-session queue. There
are at most three probes; each retains the existing eight-second tool timeout.
There is no repeating background timer, no new global observer and no change to
startup or restart consent.

Crucially, `server exited unexpectedly` still means **unknown**, never absence.
The record is removed only when a later ordinary inventory check establishes
absence using the pre-existing strict rules. If every probe is unknown, the
saved deletion intent remains pending for later recovery. A hung tool can take
roughly 24.35 seconds across these three bounded probes; each timed-out child is
terminated, and the intent is retained.

## Evidence

- `test-terminal-concurrent-cleanup.mjs`: **10 rounds × 6 actual tmux jobs passed**.
  It creates an isolated temporary profile/socket, launches explicit `/bin/sleep`
  jobs without user shell commands, and checks all records and processes are gone.
  The successful run captured **5 real `server exited unexpectedly` responses**;
  subsequent probes confirmed absence and cleared all 60 records.
- `test-terminal-session-persistence.mjs`: **21 passed**, including deterministic
  unknown → unknown → absent recovery and permanently unknown preservation.
  The timeout check confirms all three hung probe children are terminated.
- `test-terminal-session-ownership.mjs`: **6 passed**.
- `git diff --check`: passed.

After log: `.terminal-test/concurrent-cleanup-after.log`.

This is actual tmux evidence through the production manager with a Node
subprocess adapter, not native browser acceptance. The parent owns rebuilding
and rerunning the native six-terminal performance journey.
