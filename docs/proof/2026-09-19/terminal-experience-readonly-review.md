# Terminal experience: focused read-only review

Scope: current Page/CSS/XHTML, bundled xterm configuration, existing native and
rendered tests, current build rules, original explicit deferrals, and canonical plan
read directly on Chubs. No UI launch or production edits. No claim this is visual
or accessibility acceptance.

## What is already supported by evidence
- Actual Firefox156 typing/Unicode, Ctrl-C, full-screen editor, resize and recovery
  passed parent native suite. This is not proof of all keyboard paths.
- Rendered Chromium harness injects ClipboardEvent with synthetic DataTransfer and
  checks exact text. It does not prove macOS system clipboard Cmd+C/V or browser
  context menu behavior. Split-surrogate tests are not a real IME composition test.
- Output waits for xterm.write callback before reading more; scrollback10000;
  frame input is bounded and oversized paste rejected whole. Rendered harness emits
  12050 lines and checks last line plus buffer bound. This is not CPU/memory/latency
  or real Firefox streaming-performance acceptance.
- ResizeObserver and animation-frame fitting exist; status labels, polite live
  status and visible reconnect-button focus style exist. Screen reader mode is set
  from accessibilityEnabled at startup. None establishes VoiceOver usability.

## Concrete findings and minimal priorities

### P1: recover honest ready state after rejected paste / temporary busy input
`writeToShell` oversized rejection and `writeFrame` queue overflow call
`setStatus(message, false)` although shellReady remains true. Later successful input
never restores status/terminal-ready. Consequently an operational terminal can remain
visually labelled not ready indefinitely. Existing test proves whole-paste rejection
but misses warning recovery. This is source-confirmed behavior, not a shell crash.

Minimal repair: distinguish ready-shell warning from disconnected shell. Retain
ready attribute when merely refusing input, or restore prior connection status after
queue drains/next successful input. Do not truncate or automatically retry paste.
Proof: reject oversized paste -> zero bytes written -> type safe small command ->
exact success and truthful ready/warning state; repeat under queue backpressure.
Reasoning high; focused logic and actual Firefox synthetic large-paste journey.

### P1: actual clipboard, key focus and IME proof before changing key mappings
Page has no custom copy/search/browser-shortcut routing; it relies on xterm and Zen.
`macOptionIsMeta=true` is an explicit policy, not proof international Option-key text
or macOS composition works. No direct bug claim until native tests.

Small proof slice: select synthetic output with pointer and Cmd+C; Cmd+V into a safe
quoted input; check exact Unicode/multiline text and no duplicate keys; Cmd+A meaning;
context menu Copy/Paste; Option word navigation versus Option accents; real composing
input, not insertText; browser Cmd+L/T/W and tab switch while terminal focused.
Do not globally swallow browser shortcuts or make Cmd+C send Ctrl-C. If tests fail,
fix only the failing focus/clipboard path. Clipboard tests should preserve/restore
user clipboard locally without logging its existing contents.

### P1: reduced motion currently does not reach xterm animation options
CSS prefers-reduced-motion changes scroll-behavior, but xterm config separately sets
cursorBlink=true and smoothScrollDuration=80. A CSS rule does not change these JS
configuration values. Minimal repair: derive both from matchMedia at startup and
update on media-query change; remove listener at stop. Normal behavior unchanged.
Proof: both media states and live toggle in actual Firefox; no cursor blink/smooth
scroll under reduce. Avoid claiming broad accessibility from this alone.

### P1: keyboard-only recovery and assistive-technology checks
Surface tabindex0 plus xterm textarea makes multiple focus targets; mouse down and
pageshow always focus xterm. Native shell Tab is intentionally shell completion,
so do not steal it. Need prove browser focus cycling reaches reconnect/Start again
and returns to shell, plus no hidden focus after split/restore. Screen reader flag
is read only at init; late VoiceOver activation has no explicit page update.

Proof first: keyboard-only open/setup/select/terminal/recovery; actual VoiceOver
labels/status/output including limited high-output announcements; inspect browser
accessibility tree. If mode must respond after init, observe appropriate browser
accessibility signal rather than forcing screenReaderMode for everyone. Small
region labels/focus tweaks are preferable to another toolbar/dashboard.

### P2: scrollback search is not implemented as a deliberate terminal feature
Only fit addon is loaded. No search addon, find control or shell-focused Cmd+F
policy exists. Ordinary browser find is not evidence of searching all terminal
scrollback, especially content not represented in visible DOM. Canonical plan lists
search; original handoff did NOT explicitly defer it.

Do not quietly mark it done or newly out-of-scope. Small implementation choice:
a restrained find-in-terminal bar using matched-version vendored xterm search addon,
only when requested, preserving browser Find for web tabs. Need previous/next,
no-match, Escape/refocus, offscreen history and Unicode tests. Standard native Find
shortcut integration must be tested in browser chrome, not just content key events.

### P2: native appearance and small panes need actual paired screenshots
Terminal and status force dark colors; this may be a deliberate terminal palette,
not itself a functional defect. Native integration in light/dark remains unaccepted.
Original handoff deferred terminal LOOK PERSONALISATION, not ordinary readable,
native light/dark controls under C18. Do not build a theme editor.

Minimal choice: keep clear terminal contrast, use native control tokens for added
status/error/recovery controls, verify light/dark/high-contrast/native accent. Test
200–320px split panes, long error text, large font/zoom, compact sidebar and full
screen; status can wrap and must not make essential controls unreachable. The
current ready status is11px; measure contrast/readability rather than label it good
because screenshot exists. Raw internal URL remains visible (inspected earlier
native screenshot); address presentation is a separate native-polish issue.

### P2: establish a measured Firefox baseline, not performance adjectives
Measure disposable stock156 versus matching terminal156 app: cold start with blank
profile, idle0/1/10 terminals, controlled long output, resize during output, repeated
open/close/reload. Track owned process tree CPU/memory, command-to-render latency,
last-line completion and surviving helper count. Keep generated output synthetic;
never run uncontrolled infinite-output workloads. Report measurements before setting
final targets; no invented pass thresholds or claims that PGO-disabled matches release.

Cleanup removes app listeners/observer/onData, but terminal.dispose is not called.
Document destruction may collect it; source alone does not prove a leak. Measure
repeated lifecycle first. Only add disposal if it does not break legitimate pagehide/
restore behavior and native tests establish safe lifecycle boundaries.

## Explicit deferrals remain explicit
Original step-one handoff deferred clickable terminal links, recorded recipes,
per-container separate OS homes/logins, look personalisation and automatic status
labels. Phase2 deferred live-process survival across Mac reboot. Do not expand these
into new work by accident. Saved setups surviving reboot and explaining lost jobs
are still required. Copy/paste, native grouping, ordinary theme/readability, keyboard
access, bounded responsive output and complete proof were not deferred.

## Recommended sequence
1. Small ready-warning and reduced-motion fixes with focused tests.
2. Native clipboard/focus/IME/VoiceOver checks; fix demonstrated issues only.
3. Decide/implement bounded terminal search without second manager UI.
4. Paired appearance and controlled performance measurements.

Reasoning high for input/focus/lifecycle, medium for isolated style; proof actual
packaged Firefox targeted journeys plus source tests. No broad Core tests or new
OS architecture. Personal migration remains held until declared product acceptance.
