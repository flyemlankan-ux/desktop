# Real native dialog automation: source diagnosis and test handoff

New scripts:
- `macos-test-dialogs.py`: reusable owned-PID Accessibility helper.
- `test-terminal-native-dialogs.py`: actual folder picker Cancel/Choose/Save and private alert OK journey.

Syntax and help checked. No UI launched and no native control interaction performed. Read-only `AXIsProcessTrusted()` returned true for the current local interpreter; no permission grant, reset or request was made.

## Why known alert text does not prove acceptance

Read the actual packaged Firefox155 sources in GRE omni.ja:

- Python `Alert.accept()` sends `WebDriver:AcceptAlert`.
- `driver.sys.mjs` first registers `PromptListener.dialogClosed()`, calls the dialog's accept, and waits for the closed event **without a timeout**. Only afterwards does it await AnimationFramePromise.
- `Prompt.sys.mjs` accepts by `button0.click()`. `getText()` independently reads `ui.infoBody.textContent`; therefore readable text proves neither enabled button nor successful closure.
- `PromptListener.sys.mjs` filters close events to the current browser window. For a Window event target it computes `event.target.opener || event.target`; for other targets it uses `documentGlobal`.
- `Sync.sys.mjs` bounds the subsequent animation wait to1500ms in optimized builds. A30second socket timeout is therefore much more consistent with waiting for the close notification or a button that did not close than with a normal background animation wait.

**Uncertainty:** existing log does not record whether the real modal disappeared. Thus the exact branch—disabled/not-ready button versus an ignored/missing close event—cannot honestly be resolved without live observation. The parent/private-window opener filter is a concrete diagnostic target, not a proved cause. Do not change production security/UI based on this inference alone.

## Robust alternative click route

Use ordinary macOS Accessibility on only the PID launched for the synthetic test. Apple exposes an application root for a specified PID, and a standard press action for controls: [AXUIElementCreateApplication](https://developer.apple.com/documentation/applicationservices/1459374-axuielementcreateapplication?language=objc), [kAXPressAction](https://developer.apple.com/documentation/applicationservices/kaxpressaction?language=objc).

The helper:
- Checks existing Accessibility trust without prompting.
- Verifies every accessed/pressed UI element belongs to the explicit test PID.
- Searches the owned modal/window tree for the expected dialog text and one actual enabled AXButton with the requested label. Ambiguity/disabled/missing/foreign-process elements fail closed.
- Performs AXPress on the real control. No injected prompt response, mocked dialog callback, forced button enablement or global coordinate click.
- Sends Go-to-Folder keyboard input using CGEventPostToPid, not whichever app happens to be frontmost. It requires a labelled focused folder/path field before typing.
- Exposes optional native mouse drag with AXRaise, explicit testPID, caller-provided owned DOM/window bounds and bounds-checked endpoints. That helper is not yet an actual pointer proof.

The private test deliberately does NOT call WebDriver AcceptAlert: it reads the genuine message, clicks genuine AX OK, then verifies that the original opener returned null and session records/tab counts remain unchanged.

## Parent execution

```
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 -B \
  scripts/terminal-tabs/test-terminal-native-dialogs.py \
  --app '/path/to/test/Zen Terminal.app' --label native-dialogs-156
```

Folder journey uses two test-created folders: Cancel preserves A and saves nothing; actual picker navigation chooses B; returned field must exactly equal B before native Settings Save; saved record must equal B. It never sets the desired result directly into the browser after picker opening.

## Still pending / possible platform limitations

Native AX role/label exposure for the current macOS picker has not been observed. If the panel is exposed by a separate XPC process, strict ownership checks will stop rather than broaden access. Go-to-Folder labels can differ by OS language; English labels reflect this test environment but are not universal support. Failure records a bounded owned-app control summary, not a system-wide tree. No whole-desktop screenshot is taken.

One initial actual run should be diagnostic, not declared acceptance before all semantic assertions pass. The helper is a test aid only; no production files were modified.

## Actual AX investigation (later on 19 September)

**Native picker and private-alert click proof remains incomplete. This is not a passing UI test.**

The helper and standalone test were exercised against the separate Firefox 156 overlay app, using only new synthetic profile, home and app-data directories. The actual running process ID, profile directory and app-data directory were checked. AX trust was already true; no permission request or operating-system security change was made.

Observed:
- The owned application's AX root responds, but initially exposes no AXWindows. This is not an AX permission-denied response.
- Normal `AXFrontmost=true` activation exposes its native Zen Browser window. Optional `AXManualAccessibility` and `AXEnhancedUserInterface` writes were unsupported/not-settable and were not pursued.
- Clicking the actual Settings Choose folder control disables that button, with no inline picker error, but no accessible picker appears under the owned process.
- A minimal NSWorkspace frontmost-application identity check (PID and bundle ID only) finds the already-running original Zen, not an Apple panel service. Explicit reactivation briefly returns focus to the test PID, but the test still cannot find the native Cancel button. No original Zen window, tab, profile, dialog or other content was inspected or manipulated.
- LaunchServices launch of the exact test-app path reproduces the same outcome. `open --env` explicitly carries HOME, ZDOTDIR, MOZ_APP_DATA and MOZ_LOCAL_APP_DATA; actual profile/app-data checks still pass. This rules out merely missing `open` environment inheritance.
- The overlay's packaged AppConstants still reports `MOZ_APP_NAME: zen`, `MOZ_MACBUNDLE_ID: app.zen-browser.zen`, and `MOZ_MACBUNDLE_NAME: Zen.app`, while Info.plist and NSWorkspace identify the separate test bundle. This mismatch is real. It is a plausible overlay/native identity limitation, **not a proven causal explanation** of focus loss.
- Pinned Firefox 156's native picker code uses NSOpenPanel attached to the supplied parent NSWindow; the inspected picker code does not demonstrate a hardcoded bundle-ID activation. Do not claim source proved that causal chain. Source: https://raw.githubusercontent.com/mozilla-firefox/firefox/FIREFOX_156_0_RELEASE/widget/cocoa/nsFilePicker.mm (BeginPanelAsync / PresentFolderPanel).

Evidence:
- `.terminal-test/native-dialogs156-focusidentity.log`
- `.terminal-test/native-dialogs156-launchservices.log`
- `native-dialogs156-launchservices-results.json`
- `native-dialogs156-launchservices-owned-dialog-tree.json`
- `native-dialogs156-launchservices-failure.png`

Both owned browser processes quit. UI was released back to the parent. Production files remain unchanged by this investigation.

### Next proof boundary
Run the same native-dialog test on the genuinely compiled, correctly branded separate app before claiming the chooser and actual private-alert button work end to end. Use `--launch-services` if desired; isolation is explicit in either launch mode. The private-alert part has not yet run because the folder-picker failure occurs first. The shared helper's native pointer function exists but remains unproved; do not count it as a successful drag test.

Recommended next handoff: high reasoning for any continued diagnosis; real isolated macOS native-controls proof, not mocked callbacks or disabled prompts. Keep the existing manual folder field as the truthful usable fallback. Do not hide/quit the original Zen to make a test pass, and do not broaden AX access to unrelated processes.

### Slice recap
1. We can activate and inspect only the owned test app, and have isolated the failure more precisely.
2. Added bounded AX error reporting, ordinary owned-app activation, root-child fallback diagnostics, and explicit-isolation LaunchServices test support.
3. We are still building a separate Zen app with normal browser behavior plus terminal tabs.
4. This slice did not prove native picker selection/cancellation, private OK dismissal, or native drag/drop.
5. Proof checked owned process/profile/app-data and reproduced the picker failure in both launch modes; Python syntax passed.
6. Next is the real compiled app's native dialog journey.
7. Drift check: no production redesign, no original-browser manipulation, and no weakening of OS security to force a green result.
