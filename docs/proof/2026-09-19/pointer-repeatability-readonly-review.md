# Pointer repeatability: bounded read-only diagnosis

## Observed results
- `final156-project-project-workflows.json`: timeout waiting for actual reorder. Log captured trusted mousedown and dragstart, but no completed native drop.
- `final156-project-v2-project-workflows.json`: stopped before input on AXRaise error-25206.
- `project156-geckopointer-direct-v3-project-workflows.json`: actual trusted completed pointer reorder passed, then a separate redundant native-method order assertion failed. That pointer evidence is genuine, but not repeatability proof.

No UI/input or production/test-code changes were made for this review.

## Grounded findings
1. **Mouse-up can precede native drag startup.** Official Firefox156 `widget/cocoa/nsDragService.mm`, blob `340a9ad81c5cb23bb7e5f927d11d5cffdde7ce70`, `InvokeDragSessionImpl` checks `gLastDragView`. Its source explicitly says this value exists between mouseDown and mouseUp; if absent, the OS no longer knows where to drop and it aborts to avoid a stuck drag session. It then starts an actual Cocoa `beginDraggingSessionWithItems` using the stored native mouse-down event. [Pinned source](https://github.com/mozilla-firefox/firefox/blob/FIREFOX_156_0_RELEASE/widget/cocoa/nsDragService.mm).
2. Current test awaits native dispatch completion, makes three destination moves with50ms pauses, then always releases. Dispatch completion is not confirmation that the asynchronous browser/native drag setup has reached a valid drop target. A readiness-dependent release is more grounded than increasing arbitrary pauses.
3. **AX error is misinterpretable.** Installed Apple SDK `AXError.h` maps-25206 to `kAXErrorActionUnsupported`, not denied Accessibility permission (-25211 is APIDisabled). The test should require the desired owned foreground/focused-window state, not insist a redundant Raise action succeeds when that state is already true.
4. Source/target rectangles are sampled before owned-app activation. Focus/compact-sidebar transitions can invalidate them. Recompute rectangles and hit tests after verifying actual owned window state, and require them to remain stable during the sequence.
5. Firefox's native MOVE still maps to NSEventTypeMouseMoved, not LeftMouseDragged. These recommendations improve synchronization and diagnosis; they do not establish a universal deterministic native drag API.

## Proposed exact test-only sequence
1. Confirm spawned PID/profile. Activate only that PID if necessary. Read AXFrontmost, AXFocusedWindow owner, and AX bounds. If the exact owned app/window is already active and agrees with Marionette bounds, do not require AXRaise. Otherwise attempt Raise and then verify the same facts; unsupported action without correct state must still fail.
2. Re-read tab geometry after activation. Require visible hit-tested source/destination inside the same owned window and stable geometry.
3. Install listeners before down, then native MOVE to source and native DOWN to source using the verified widget/device-pixel coordinates.
4. Native MOVE directly to the destination. Instead of unconditional release after150ms, wait (bounded, e.g.3seconds) for an actual trusted dragover at the intended destination with `application/x-moz-tabbrowser-tab` and accepted `dropEffect=move`. Capture dragstart on the intended terminal too. If needed, send another identical native MOVE while holding, only within the same verified window; do not dispatch a DOM drag/drop or call any reorder method.
5. On accepted native dragover, send native UP. In finally, release within the owned process even when readiness times out.
6. Require the existing complete evidence unchanged: trusted dragstart/drop/dragend, tab MIME, intended real folder ordering, same shell PIDs/recipe counts. A readiness timeout is a failure, not permission to synthesize drop or report method-level behavior as pointer acceptance.

This is a justified next experiment, not a claim of determinism before execution. It can distinguish early release from missing native drag support while keeping the acceptance bar unchanged.

## Remaining dependency
The separately source-built app identity remains pending. Repeat this on that identity with owned foreground/window evidence, then multiple successful native drops. A compiled identity is useful for removing overlay ambiguity but is not assumed to fix the event path. If readiness never appears, do not keep inventing event constants or switching to global HID input on the user's desktop. Use a controlled isolated macOS test session or manual drag acceptance instead.

Recommended reasoning high; proof actual native event/state sequence plus repeated completion. No original Zen activation, global mouse event posting, changed Accessibility permissions, or weakened assertions.

## Approved test-only refinement implemented and released
Parent approved implementation after this review. Project test now verifies actual foreground/focused owned-window state; only AXActionUnsupported(-25206) can fall back, and only if that exact state is independently verified. Tab geometry is resampled after activation. Native down is held until a trusted destination dragover exposes the tab MIME and move effect (observed after production handlers through a read-only microtask); bounded3second timeout still sends owned native up and fails. Strict final drop/end/order/session assertions remain unchanged. CSS screen coordinates remain unscaled in `start/end`; multiplication by devicePixelRatio occurs only in sendNativeMouseEvent arguments, so DOM event.screenX/Y are compared in the correct CSS units. Python syntax and scoped whitespace checks pass. Test file released for parent's native run; no UI launched by this worker and no new pointer-pass claim.

## First readiness-driven native completion
Inspected parent-run `pointer156-ready-project-workflows.json`: **12 PASS**, failure=null. Pointer record contains trusted dragstart, accepted destination dragover with `application/x-moz-tabbrowser-tab` and `dropEffect=move`, trusted drop and dragend, correct actual folder order, and unchanged shell/recipe invariants. The full subsequent native-method workspace/split/resize/mirror/last-view lifecycle also passed.

The captured native sequence required **six destination MOVE events** before acceptedOver became true, then released. This supports the early-release/readiness diagnosis and demonstrates why assuming three fixed moves was insufficient in at least this run. It is not a universal timing bound or proof that six fixed moves would always work; retain the condition-driven wait.

Scope is one successful readiness-driven run on current Firefox156 overlay using own-NSApp native event delivery. Parent will run two more repeats after the separate folder-order build. Until those receipts exist, repeated success and final compiled-package identity acceptance remain pending. Earlier failures remain preserved. No UI launched or code changed by this documentation update.

A future drag-to-split journey may reuse verified owned-window delivery and readiness-driven release, but needs source-confirmed split drop targets and native dragover acceptance conditions rather than reusing tab-reorder coordinates. No implementation was started; wait for a separately bounded task.

## Three consecutive readiness-driven native passes
Inspected `pointer156-ready-project-workflows.json`, `pointer156-ready-v2-project-workflows.json`, and `pointer156-ready-v3-project-workflows.json`. Each has failure=null and **all12 checks passing**. Each pointer record retains actual trusted dragstart/drop/dragend, native tab MIME/accepted destination, correct real folder order, and unchanged shell/recipe invariants. This establishes three consecutive successful native pointer-reorder journeys for the tested Firefox156 overlay, not merely method calls or source assertions.

The subsequent workspace/split/resize/mirror/cleanup portions also passed in each run, but **split creation is method-level integration: actual drag-to-split remains unproved**. Compiled-package acceptance remains pending while source builds run. Separate folder/workspace repairs are not claimed resolved by these pointer receipts. Previous failed attempts remain preserved. Docs-only update; no UI or code changes.
