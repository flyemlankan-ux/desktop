# Current156 overlay: sequential native regression slice

## Where we are
Ran only the assigned disposable-profile native journeys, sequentially, against `.terminal-test/Zen Terminal Test 156.app`. This is current-source overlay proof on Firefox156, not acceptance of a newly compiled distributable. Exclusive UI ownership was released to parent after every spawned process finished cleanup.

## Results
- `final156-main`: **26 PASS**. Includes actual shell input, both installed CLI `--version` invocations (no paid calls), resize, rename save/cancel, reload, relaunch, crash recovery, and final session cleanup.
- `final156-saved-v2`: **9 PASS**. Real editor save/cancel, folder validation, independent terminals, edits affect new jobs only. Actual dialog screenshot inspected: folder field/chooser aligned, explanatory text readable, Save/Cancel visible; form vertically scrollable at this size, startup row near lower viewport edge. Horizontal form overflow check passed. This is not a claim that every control fits simultaneously without scrolling.
- `final156-grouping`: **10 reported PASS**. Mixed folder selection, intentional pin/unpin, unchanged separate-container Essentials refusal, explicit synthetic shared-Essentials preference switch/restart, Essential selection/restart same shell, regroup/collapse, reset-decoration guard, final grouped restart. Earlier parent message saying14 was corrected to actual current log count10.
- `final156-project-methods`: **11 PASS**, with pointer explicitly not_run. Independent saved-setup jobs, mixed folder, native method reorder, whole-folder workspace move, split resize/unsplit, mirrored window preservation, final viewer cleanup.
- `final156-project`: pointer attempt **FAIL**, preserved. Trusted mousedown and dragstart arrived, but no dragover/drop/end or desired reorder. Parent's prior direct-v3 completed pointer receipt remains a separate actual observation; repeatability is not established by this run.
- `final156-project-v2`: pointer retry **FAIL CLOSED**, preserved. Owned-app AXRaise returned-25206 before Gecko pointer sequence. No global-post fallback or other-app input attempted.

## Test-only fixes
The original saved-setup test awaited updateComplete for every Settings widget, including unrelated hidden panes, and then two animation frames. It timed out in that broad readiness wait. Replaced it with the actual Add control's updateComplete (rejects reported explicitly), visible/enabled geometry, and real dialog ready/accept control checks. No product behavior was replaced or error assertion waived. Kept original failure receipt.

Added owned-app activation/AXFrontmost guard before the Gecko mouse experiment: DOM window.focus does not guarantee AppKit application activation. The retry exposes the overlay accessibility failure instead of assuming correct foreground state. Production files unchanged.

## Scope, evidence, and next
All receipts are adjacent `final156-*.json`; process logs are `.terminal-test/final156-*.log`. Native screenshots are scoped to owned browser windows. No personal profiles, original Zen PID699, global input posting, or clipboard touched.

Overall project remains native Zen browsing with real terminal tabs and saved setups. This slice did not create a distribution package, resolve intermittent mouse delivery, or establish full OS accessibility acceptance. Parent should validate the separately compiled identity and rerun pointer proof there; require trusted completed drop and actual order, not method-only substitution. High reasoning for native input/focus issues; focused native proof plus exact-owned-process cleanup. No drift toward weakening acceptance to call the project finished.
