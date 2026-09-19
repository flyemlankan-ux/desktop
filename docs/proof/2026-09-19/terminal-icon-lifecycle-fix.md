# Terminal icon lifecycle repair

Inspected actual `safety-overlay-v7-safety-ended-session.png`: terminal icon was again a placeholder square after page reload. Initial icon assignment alone was insufficient.

## Root cause checked in actual packaged source

Read `chrome/browser/content/browser/tabbrowser/tabbrowser.js` from the disposable app's real browser `omni.ja`:

- Native location change computes `shouldRemoveFavicon` from absent `zenStaticIcon`, absent browser `mIconURL`, nonblank navigation and lack of built-in default icon.
- It removes the tab's `image` attribute, then emits `TabAttrModified` with `detail.changed` containing `image`.
- `src/zen/tabs/zen-tabs/vertical-tabs.css` explicitly renders `.tab-icon-image:not([src])` as a colored square. This explains the screenshot.

## Repair

`ZenTerminalTabs.mjs` now listens to that native image-change notification. For marked terminal tabs still on the exact terminal page (or pending restored terminal tabs), it restores the ordinary native icon slot. It does not poll, add timers, change custom icon state, suppress overlays or change native navigation. It leaves user-picked icons alone. Image equality prevents recursive setIcon notifications. Tabs navigating to websites are not forced back to a terminal icon.

## Proof

Expanded `test-terminal-organization.mjs` uses production classes and a native-like setIcon notification mock. It replays the actual browser-icon-reset → image removal → TabAttrModified sequence, including a pending restored tab. It checks the final image attribute AND browser mIconURL, custom icon preservation, no invented custom icon and no overwrite after website navigation.

- 14 organization cases pass.
- 21 entry-point/context + 4 workspace default cases pass.
- Native polish checks pass.
- Wiring/syntax checks pass.

Actual Mac after-reload screenshot and final icon slot inspection remain parent-run and pending. No UI launched or final native visual acceptance claimed.
