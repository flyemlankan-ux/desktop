# Read-only review: missing macOS pointer events and terminal address presentation

## What happened
`project156-nativepointer.log` records matching AX/browser geometry and visible tab hit tests, but `drag=[]`: even a mousedown never reached the captured browser window. This is earlier than tab reordering logic. W3C's earlier dragstart-without-drop is a different failure mode and should not be conflated.

## What the sources establish
The installed Apple SDK `CoreGraphics/CGEvent.h` documents `CGEventPostToPid` as routing into a specified application's event stream. Its description uses rerouting an already-annotated event as an example. It does not say freshly constructed mouse events acquire their target window automatically. `CGEventTypes.h` publicly defines mouse window fields91/92 and click-state field1.

Apple's [HID event-tap documentation](https://developer.apple.com/documentation/coregraphics/cgeventtaplocation/cghideventtap) places HID events at entry to the WindowServer. That is a global input path, not equivalent to PID delivery. [CGEvent postToPid](https://developer.apple.com/documentation/coregraphics/cgevent/posttopid(_:)) is the application-targeted operation.

Actual Firefox156 source was read from the official GitHub contents endpoint: `widget/cocoa/nsCocoaWindow.mm`, tag `FIREFOX_156_0_RELEASE` (lines403–507). Its `SynthesizeNativeMouseEvent` builds an `NSEvent` with an explicit owned NSWindow number, uses clickCount1, and delivers through that process's `NSApp`. It also warps the global cursor. Its wheel synthesis comment (lines561 onward) explains why Firefox uses direct Cocoa delivery instead of CGEventPost on newer macOS. The wheel comment is evidence of platform constraints, NOT proof that all PID mouse posting can never work. [Official source](https://github.com/mozilla-firefox/firefox/blob/FIREFOX_156_0_RELEASE/widget/cocoa/nsCocoaWindow.mm).

## Conclusion and safe next choices
- Do not label `CGEventPostToPid` fundamentally incapable of mouse delivery: the available primary evidence does not establish that universal claim.
- Do not change production drag code based on this test. No mouse event arrived.
- Do not switch to global `CGEventPost(kCGHIDEventTap)` on this desktop. A foreground/window check followed by a global post has a race: another app can gain focus between those steps. It cannot guarantee the original Zen is untouched.
- A bounded next experiment can obtain the actual owned window number, verify PID + bounds match exactly, set public mouse-window fields91/92 and click state1 on the already PID-targeted event, then require trusted mousedown/drop/dragend. Missing/ambiguous window IDs must fail. This is a hypothesis, not a proven repair.
- Gecko's own native mouse synthesis is an alternative for process-local delivery, but it warps the shared cursor and its Move case is NSEventTypeMouseMoved, not automatically a complete native drag loop. It therefore needs a separately honest acceptance scope; it is not an automatic replacement for a successful physical drag.
- Strongest final drag proof is an actual user drag or controlled isolated macOS test session with no personal apps present. A separately compiled app identity removes overlay identity ambiguity, but does not by itself fix event annotation or prove dragging.

No UI, input posting, process activation, or production change occurred during this review.

## Raw terminal URL: smallest safe presentation proposal
Current tabs use a real privileged terminal address containing setup/session identifiers. Do not replace the actual URI with a pretty string, redefine normal navigation, or hide a website origin.

Proposed small presentation-only change, subject to parent approval:
1. In the unfocused address bar only, show a non-interactive label `Terminal — <saved setup name>` for a strictly validated current terminal document whose browser identity matches its terminal setup. Derive this from trusted setup metadata, never shell output or an arbitrary tab marker alone.
2. Keep the actual address-bar value, current browser URI, principal, navigation history, certificate/site controls, and copy/drag/navigation handlers unchanged. Never write the friendly text into `gURLBar.value` or the stored URL.
3. Focusing/clicking the address bar or Cmd+L immediately removes the decorative label and exposes the real editable address. Copy while focused copies the actual URI, not the display label. Website navigation removes the label synchronously; a tab carrying old terminal ownership but displaying a website must show the real website address.
4. If native address-bar bindings cannot provide this without fragile text-hiding or accessibility mismatch, prefer leaving the honest raw URL for now over a misleading overlay. A new `about:terminal` registration would be a larger security/navigation change, not cosmetic polish.

Required proof before shipping: normal website origin and copy remain exact; typed URL value is never covered; real-site navigation/back/forward updates; terminal setup rename; Cmd+L selection/copy; address drag; screen-reader accessible value; split views; loading/error states; and stale terminal-tab marker with a website document. High reasoning for navigation/focus/security, focused actual native browser tests. No presentation edits were made here.

## Follow-up: bounded pointer experiment implemented, not executed
Opt-in command now adds `--annotate-native-window` alongside `--native-pointer-drag`. Existing default behavior is unchanged. Helper resolves one on-screen layer0 CG window by exact owned PID plus previously checked AX/browser bounds. It records no unrelated window data and captures no images. Before every non-release event it revalidates that exact window ID and bounds. It sets public click-state1, window fields91/92, and target PID40, then still calls only `CGEventPostToPid`. Release stays targeted to the original PID/window even if geometry changes. Missing or ambiguous metadata aborts; no global-post fallback exists. Python syntax and whitespace checks pass. Actual success remains unproven.

## Pinned address-bar method review before any prototype
Read pristine Firefox156 sources through official GitHub contents endpoints:
- `browser/components/urlbar/content/UrlbarInputBase.mjs`: Git blob `8be35b58c5369e123ca69426e852e3849bf75513`.
- `browser/components/urlbar/content/UrlbarInput.mjs`: Git blob `6f0fe16983c8b65295224c32bd2d71a31a88f0a0`.
The existing Zen patch explicitly targets the same base blob.

`UrlbarInputBase.setURI` (pristine line988) first accounts for typed input, current authentication-prompt URI, opened blank-target loading, and current browser URI. It then calls `setValue(..., {allowTrim:true,valueIsTyped:!valid})` around1100 and preserves selection across updates. `setValue` (3625) updates `_untrimmedValue`, trimming flags, `valueIsTyped`, the actual input value, formatting, and accessibility ValueChange. The value getter returns the actual input field. These are shared browser semantics, not a cosmetic label API.

Therefore do NOT prototype by replacing `setValue`, `setURI`, `value`, or `_untrimmedValue`, or by making a terminal string look like a website. The smallest feasible prototype would be a separate non-interactive decoration adjacent to the address input, shown only after all these predicates hold: selected browser's current *document* is the exact terminal page; currentURI also matches; context ID agrees; setup still exists; no currentAuthPromptURI; `userTypedValue === null`; not focused; no URL-bar popup/search/new-tab mode. It must hide synchronously on focus/input, tab selection, loading/location changes, popup opening, and setup removal.

There is no verified native hook yet that guarantees those transitions plus the accessible value stay aligned. Hiding real text with a CSS overlay can still obscure an authentication-origin update, so this worker has deliberately NOT implemented it. A safe narrower prototype is only an extra `Terminal — setup` label while retaining the visible real URL; it does not solve the raw-URL aesthetic, but has fewer security/focus risks. Parent should decide whether that minor addition is worthwhile or keep the honest raw address until a fully tested native decoration lifecycle is designed. Required tests from the previous section remain mandatory; preserving `_untrimmedValue` alone is not sufficient.
