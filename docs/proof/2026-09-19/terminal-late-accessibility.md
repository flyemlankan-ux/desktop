# Terminal accessibility activated after the tab opens

## Change

A terminal already open now follows the browser accessibility service instead of choosing its screen-reader mode only once at startup.

`ZenTerminalPage.mjs` subscribes once to `a11y-init-or-shutdown` after xterm opens, then rechecks the current service state. Data `1` enables xterm's screen-reader mode; data `0` disables it. PDF-only (`pdf`) and unknown notifications do nothing. Stopped pages ignore notifications. Shell/page teardown removes the observer once.

Source basis: pinned Firefox156 `nsAccessibilityService.cpp`, already downloaded at `.terminal-test/nsAccessibilityService.cpp`. Initialization emits `pdf` for PDF-only service, `1` for full initialization and promotion to full service, and `0` on shutdown. No macOS VoiceOver process or OS accessibility preference is started or modified by this change.

## Focused proof

- `node scripts/terminal-tabs/test-terminal-accessibility-lifecycle.mjs`: pass. Executes the actual production lifecycle functions, covering initially on/off, late full activation, shutdown, PDF/unknown ignored, unrelated topic, duplicate subscription, stopping guard and repeated teardown.
- `node scripts/terminal-tabs/test-terminal-polish.mjs`: pass. Existing input, warning, motion and helper checks remain green. Its isolated motion harness stubs the separate accessibility lifecycle.
- `node --check src/zen/terminal/ZenTerminalPage.mjs`: pass.
- Browser bridge observer mock updated for the now-required observer interface; no browser UI launched in this slice.

## Native test prepared, not yet run by this agent

`scripts/terminal-tabs/test-terminal-accessibility-macos.py`:

1. Launches a separate Firefox156 test app with a fresh synthetic HOME, profile and app-data and checks actual PID/directories.
2. Requires that accessibility is initially inactive. If already active, fails honestly instead of disabling a real service to force a late-activation result.
3. Opens an actual terminal and confirms screen-reader mode is off and the page added one observer.
4. Requests the actual `nsIAccessibilityService` inside the owned browser; it does not fake an observer notification.
5. Checks that the existing real xterm instance creates its accessibility tree.
6. Sends a harmless printf command to the exact test job and requires the output marker as a complete accessibility row, not merely the echoed command.
7. Reads real Firefox accessible objects under the owned terminal surface and verifies the terminal label and output marker, plus labelled input and polite live-status markup.
8. Closes the real tab and checks one observer disappears and the exact test job stops.

Native test syntax and `--help`: pass. Native app execution is reserved for the parent after rebuild. No native pass is claimed here. Actual macOS VoiceOver speech, navigation experience and operating-system IME composition remain separate unproved work.

## Slice recap

1. Existing terminal tabs can now respond when browser accessibility starts later.
2. Added observer subscription, live option updates and cleanup, without changing terminal job behavior.
3. Overall goal remains ordinary Zen browsing with fully usable terminal tabs.
4. This slice did not implement VoiceOver, change OS settings, or prove spoken output/IME.
5. Focused lifecycle and existing polish checks passed; actual native tree proof is prepared.
6. Next: parent rebuilds and runs the native accessibility test in its exclusive UI slot.
7. Drift check: this fixes a real late-activation gap rather than adding a separate accessibility UI or claiming labels alone prove usability.

Recommended next handoff: medium reasoning for the native run; high if real accessibility objects differ from expectations. Proof level: actual owned-browser service activation plus real terminal output, with VoiceOver speech explicitly separate.

## Native-test correction after parent's first attempt

The initial native run stopped before service activation because the total browser observer count did not increase by exactly one. Other Firefox components initialize asynchronously, so a global total is not an exact count of this terminal's subscriptions. The test now records those totals as diagnostics only, not pass/fail assertions or page-specific cleanup claims. Exact one-time subscription/removal remains covered by the focused test executing the production lifecycle functions. The native test still checks actual service activation, actual accessible output and actual exact-job cleanup after tab close. This correction does not weaken product behavior or fabricate an accessibility pass; the native service/tree checks still need the rerun.
