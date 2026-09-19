# Extended navigation acceptance: native 12-check pass

1. **Where we are:** The existing eight native navigation checks remain unchanged. A new opt-in `--extended` branch adds four checks before the existing Back/reload/dismiss/restart journey.
2. **What changed:** Test-only additions in `scripts/terminal-tabs/test-terminal-navigation-macos.py`. It creates one bookmark in the disposable profile through native Places, reveals the native toolbar, then clicks the actual generated bookmark button. It requires navigation in the same owned terminal tab, no extra tab, ordinary website principal, live original shell, native away notice, and a real Return button click. It then creates a native mirrored window, verifies process/profile identity and actual synchronized tab, types a local address through the address bar, clicks its Return button, closes only that window, and requires the original shell to remain alive.
3. **Overall target:** Normal web navigation must not silently destroy an owned terminal job, and the user must have a visible way back.
4. **Not built or claimed:** No production edits. The native run below used only an isolated test profile. Native Places setup, toolbar visibility, window creation/selection and closing are labelled method-based; bookmark and Return activation and address-bar typing are actual rendered input. Actual URL drag/drop and non-tmux notice wording remain explicitly not_run. No personal bookmark data or browser profile is touched. A failing bookmark toolbar or mirror check fails rather than substituting a direct navigation/return method.
5. **Proof so far:** Python compilation and focused diff whitespace check pass. The completed isolated native run has 12 pass records, two not_run records, and no failure; details below.
6. **Next:** Repeat against the final compiled app when ready. The command below reproduces the overlay check. Recommended reasoning: high for failure diagnosis, medium for a clean run. Proof level: actual owned-app native integration plus live shell PID and startup-count checks; no broad source rerun needed for this test-only addition.
7. **Drift check:** This extends real user actions, not production mock methods. All test bookmarks and local pages are synthetic; the external Internet and personal browser remain outside scope.

```
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 \
  scripts/terminal-tabs/test-terminal-navigation-macos.py \
  --app '.terminal-test/Zen Terminal Test 156.app' \
  --label navigation156-extended --extended
```

Result: `docs/proof/2026-09-19/navigation156-extended-navigation-workflows.json`.

## Native result inspected

Parent ran `navigation156-extended` on the actual isolated overlay. Inspected `navigation156-extended-navigation-workflows.json`: **12 pass, 2 not_run, failure null**. Synthetic run directory: `.terminal-test/mac-cbe766ac`.

The four additions passed: actual generated toolbar bookmark click navigated the same owned terminal tab; actual Return reconnected its original shell; actual address-bar navigation in the mirrored window showed its native away notice; actual mirrored Return followed by closing that window preserved the original terminal job. All original eight checks also passed, including dismissal persistence across restart and final-view cleanup.

Remaining explicit not_run cases are actual URL drag/drop into terminal and non-tmux native away wording. This receipt proves the synthetic local website/bookmark and tmux-backed navigation journeys only; it does not prove those two remaining cases or a compiled release build. The earlier readiness statements above describe preparation before this run; this section records the completed native evidence. No production changes or further UI launch were made while recording it.
