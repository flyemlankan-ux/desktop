#!/usr/bin/env node
// MPL-2.0. Real pinned xterm DOM renderer and production CSS; no native Zen UI.
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { chromium } from 'playwright';
const read = path => readFileSync(path, 'utf8');
const localChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const browser = await chromium.launch({
  executablePath: process.env.CHROME_EXECUTABLE || (existsSync(localChrome) ? localChrome : undefined),
  headless: true,
});
let checks = 0;
try {
  const page = await browser.newPage({ viewport: { width: 900, height: 600 }, reducedMotion: 'reduce' });
  await page.setContent('<html><body><div id="zen-terminal-output" style="width:800px;height:500px"></div></body></html>');
  await page.addStyleTag({ content: read('src/zen/terminal/vendor/xterm.css') });
  await page.addStyleTag({ content: read('src/zen/terminal/zen-terminal-page.css') });
  await page.addScriptTag({ content: read('src/zen/terminal/vendor/xterm.js') });
  await page.evaluate(() => {
    window.term = new Terminal({ cols: 80, rows: 24, cursorBlink: false, cursorStyle: 'bar' });
    term.open(document.getElementById('zen-terminal-output'));
    term.focus();
  });
  async function write(sequence) {
    await page.evaluate(sequence => new Promise(resolve => term.write(sequence, resolve)), sequence);
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    return page.evaluate(() => {
      const cursor = document.querySelector('.xterm-cursor');
      if (!cursor) throw Error('No rendered cursor');
      const style = getComputedStyle(cursor);
      return { classes: cursor.className, animation: style.animationName, shadow: style.boxShadow,
        border: style.borderBottomStyle, background: style.backgroundColor, blinkOption: term.options.cursorBlink };
    });
  }
  function assertStaticVisible(state, shape) {
    assert.equal(state.animation, 'none', JSON.stringify(state));
    assert.ok(state.classes.includes('xterm-cursor-' + shape), JSON.stringify(state));
    if (shape === 'bar') assert.notEqual(state.shadow, 'none');
    if (shape === 'underline') assert.equal(state.border, 'solid');
    if (shape === 'block') assert.notEqual(state.background, 'rgba(0, 0, 0, 0)');
    checks++;
  }
  // Application requests override xterm's option; CSS must win at the real cursor.
  const requested = await write('\x1b[?12h');
  assert.equal(requested.blinkOption, true, 'Actual parser must execute DEC blink-on');
  assertStaticVisible(requested, 'bar');
  assertStaticVisible(await write('\x1b[?12l'), 'bar');
  for (const [code, shape] of [[1,'block'],[3,'underline'],[5,'bar']]) {
    assertStaticVisible(await write(`\x1b[${code} q`), shape);
    assertStaticVisible(await write('\x1b[?12h'), shape);
    assertStaticVisible(await write('\x1b[?12l'), shape);
  }
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  for (const [code, shape] of [[1,'block'],[3,'underline'],[5,'bar']]) {
    const state = await write(`\x1b[${code} q`);
    assert.ok(state.animation.startsWith('blink_'), JSON.stringify(state));
    assert.ok(state.classes.includes('xterm-cursor-' + shape));checks++;
  }
  // Turning reduced motion on must stop an existing application-selected mode
  // without requiring another shell write or a preference-driven blink option.
  await page.emulateMedia({ reducedMotion: 'reduce' });
  assertStaticVisible(await write(''), 'bar');
  // Explicit steady cursor modes remain steady when animations are permitted.
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  for (const [code, shape] of [[2,'block'],[4,'underline'],[6,'bar']]) {
    assertStaticVisible(await write(`\x1b[${code} q`), shape);
  }
  console.log(`PASS ${checks} reduced-motion cases: real pinned xterm, production CSS, headless Chromium (not native Zen)`);
} finally {
  await browser.close();
}
