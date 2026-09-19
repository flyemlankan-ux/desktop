#!/usr/bin/env node
// MPL-2.0. Actual pinned xterm/search/fit + production markup/CSS/search function.
// No terminal subprocess or native Zen; actual Gecko/TIP remains separate proof.
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { chromium } from 'playwright';
const read = name => readFileSync(name, 'utf8');
const root = 'src/zen/terminal/';
const markup = read(root + 'terminal.xhtml').match(/<body>([\s\S]*)<\/body>/)[1];
const source = read(root + 'ZenTerminalPage.mjs');
const search = source.slice(source.indexOf('function runTerminalSearch('), source.indexOf('function openTerminalSearch('));
const css = read(root + 'zen-terminal-page.css');
const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const browser = await chromium.launch({ executablePath: process.env.CHROME_EXECUTABLE || (existsSync(chrome) ? chrome : undefined), headless: true });
let checks = 0;
try {
  for (const [width, negative] of [[900,false], [480,false], [240,false], [900,true]]) {
    const page = await browser.newPage({ viewport: { width, height: 650 } });
    await page.setContent('<html><body>' + markup + '</body></html>');
    await page.addStyleTag({ content: read(root + 'vendor/xterm.css') });
    await page.addStyleTag({ content: css + (negative ? '\n#zen-terminal-find-result:empty { display:none; }' : '') });
    for (const file of ['xterm.js','addon-fit.js','addon-search.js']) {
      await page.addScriptTag({ content: read(root + 'vendor/' + file) });
    }
    await page.evaluate(() => {
      window.terminal = new Terminal({fontSize:13,lineHeight:1.18,allowProposedApi:false});
      window.fitAddon = new FitAddon.FitAddon();
      window.searchAddon = new SearchAddon.SearchAddon();
      terminal.loadAddon(fitAddon);terminal.loadAddon(searchAddon);
      terminal.open(document.getElementById('zen-terminal-output'));
      document.getElementById('zen-terminal-find').hidden = false;
      document.getElementById('zen-terminal-surface').setAttribute('terminal-search-open','');
      window.resizeEvents = [];
      terminal.onResize(size => resizeEvents.push(size));
      window.fitObserver = new ResizeObserver(() => requestAnimationFrame(() => fitAddon.fit()));
      fitObserver.observe(document.getElementById('zen-terminal-output'));
      fitAddon.fit();
    });
    await page.addScriptTag({ content: search });
    await page.evaluate(() => new Promise(resolve => terminal.write('SEARCH雪 one\r\nSEARCH雪 two\r\n',resolve)));
    async function settle() {
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(resolve)))));
    }
    async function state() {
      return page.evaluate(() => ({
        result: document.getElementById('zen-terminal-find-result').textContent,
        findHeight: document.getElementById('zen-terminal-find').getBoundingClientRect().height,
        outputHeight: document.getElementById('zen-terminal-output').getBoundingClientRect().height,
        rows: terminal.rows, selection: terminal.getSelectionPosition() || null,
        resizes: resizeEvents.length,
      }));
    }
    await settle();
    const before = await state();
    // Fast Unicode query arrives as one update, matching the native IME failure.
    await page.evaluate(() => {
      document.getElementById('zen-terminal-find-input').value = 'SEARCH雪';
      runTerminalSearch(false,true);
    });
    const immediate = await state();
    assert.ok(immediate.selection, 'Real addon must initially select a Unicode match');
    assert.equal(immediate.result, 'Match found');
    await settle();
    const after = await state();
    if (negative) {
      assert.ok(after.findHeight > before.findHeight, 'Old empty-result rule must reproduce growing toolbar');
      assert.ok(after.rows < before.rows, 'Negative control must trigger a real terminal row resize');
      assert.equal(after.selection, null, 'Actual xterm resize must reproduce the lost first selection');
      console.log('NEGATIVE CONTROL reproduced first-result resize:', JSON.stringify({ before, after }));
      checks++;
    } else {
      assert.equal(after.findHeight,before.findHeight);
      assert.equal(after.outputHeight,before.outputHeight);
      assert.equal(after.rows,before.rows);
      assert.equal(after.resizes,before.resizes);
      assert.deepEqual(after.selection,immediate.selection);
      checks++;
      for (const query of ['absent-query','','SEARCH雪']) {
        await page.evaluate(query => {
          document.getElementById('zen-terminal-find-input').value=query;
          runTerminalSearch(false,true);
        }, query);
        await settle();
        const next=await state();
        assert.equal(next.findHeight,before.findHeight);
        assert.equal(next.outputHeight,before.outputHeight);
        assert.equal(next.rows,before.rows);
        assert.equal(next.resizes,before.resizes);
        if (query === 'SEARCH雪') {
          assert.equal(next.result, 'Match found');
          assert.ok(next.selection, 'Re-entering query after clear must regain real match selection');
        }
        checks++;
      }
    }
    await page.close();
  }
  console.log(`PASS ${checks} search-layout cases: actual vendored renderer/addons, production CSS/function; headless Chromium only`);
} finally {
  await browser.close();
}
