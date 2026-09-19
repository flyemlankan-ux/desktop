# Reduced-motion cursor protection

## What was wrong

The terminal page sets xterm's cursor-blink option when the motion preference
changes. A shell application can subsequently change it. More importantly,
xterm 6 also has a separate application-selected cursor mode that its DOM
renderer uses before the ordinary option. Therefore `cursorBlink === false`
alone does not prove that the rendered cursor is steady; conversely, requiring
`cursorBlink === true` when reduced motion is off rejects legitimate application
choices.

Pinned upstream evidence:

- [xterm 6 InputHandler](https://github.com/xtermjs/xterm.js/blob/6.0.0/src/common/InputHandler.ts):
  DEC private mode 12 changes the option. `setCursorStyle` stores the application
  cursor shape and blinking state separately.
- [xterm 6 DOM renderer](https://github.com/xtermjs/xterm.js/blob/6.0.0/src/browser/renderer/dom/DomRenderer.ts):
  application cursor state takes precedence when rendering; block, underline and
  bar blinking use generated CSS animations. Each shape also has a static style.

## Minimal change

Inside the existing reduced-motion media query, the production stylesheet now
sets `.xterm .xterm-cursor { animation: none !important; }`. This preserves the
application's chosen shape but prevents it from overriding the user's preference
against animation. Ordinary motion mode keeps native xterm behavior. No escape
sequence is discarded, parser internals accessed, proposed API enabled, timer
added or terminal-page code changed. Smooth scrolling remains controlled by the
existing preference listener.

This protection applies to the currently shipped DOM renderer. Adding a canvas
or WebGL renderer requires revisiting this protection and its tests.

## Proof and limits

`node scripts/terminal-tabs/test-terminal-reduced-motion.mjs`: **18 passed**.
The test loads the actual vendored xterm and production stylesheet in headless
Chromium. It checks computed cursor animation and visible static shape after
CSI `?12h` / `?12l`, blinking block/underline/bar requests, steady variants, and
motion preference changes in both directions. It does not mock xterm's parser.

Negative control: removing only the new CSS rule makes the same test fail on the
first blink request, with computed animation `blink_bar_1` rather than `none`.
Log: `.terminal-test/reduced-motion-negative-control.log`.

Existing `test-terminal-polish.mjs` and `test-terminal-native-polish.mjs` passed.
This is rendered Chromium evidence, not native Zen acceptance. No native app
was launched or rebuilt by this agent. Parent owns the final native test.
