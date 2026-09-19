#!/usr/bin/env node
// Executes the actual patched Firefox156 removeTabs method. No browser launch.
import assert from 'node:assert/strict';
import {readFileSync, mkdtempSync, cpSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {execFileSync} from 'node:child_process';
import vm from 'node:vm';
const temporary=mkdtempSync(join(tmpdir(),'zen-empty-close-'));
let source;
try {
 cpSync('scripts/terminal-tabs/fixtures/firefox156-sessionstore/browser',join(temporary,'browser'),{recursive:true});
 execFileSync('patch',['--batch','--fuzz=0','-p1','-i',resolve('src/browser/components/tabbrowser/Tabbrowser-sys-mjs.patch')],{cwd:temporary});
 source=readFileSync(join(temporary,'browser/components/tabbrowser/Tabbrowser.sys.mjs'),'utf8');
} finally {rmSync(temporary,{recursive:true,force:true});}
let method=source.slice(source.indexOf('  removeTabs(\n'));
method=method.slice(0,method.indexOf('\n  removeCurrentTab(')).replaceAll('this.#','this.');
let resets=0,windowCloses=0,closeWithLastTab=false;
const sentinel=Error('entered unchanged real-tab history path');
const browser=vm.runInNewContext('({'+method+'})',{
 Services:{prefs:{getBoolPref:()=>closeWithLastTab}},
 lazy:{SessionStore:{resetLastClosedTabCount(){resets++;throw sentinel;}}},
});
browser.documentGlobal={closeWindow(){windowCloses++;}};
const placeholder={hasAttribute:name=>name==='zen-empty-tab'};
const ordinary={hasAttribute:()=>false};
browser.tabs=[ordinary];
browser.removeTabs([]);
browser.removeTabs([placeholder]);
browser.removeTabs([placeholder,placeholder],{skipSessionStore:true});
assert.equal(resets,0);assert.equal(windowCloses,0);
assert.throws(()=>browser.removeTabs([ordinary]),error=>error===sentinel);
assert.throws(()=>browser.removeTabs([placeholder,ordinary]),error=>error===sentinel);
assert.equal(resets,2);
browser.tabs=[];
closeWithLastTab=true;
browser.removeTabs([]);
assert.equal(windowCloses,0);
console.log('PASS strict pinned156 patch + actual removeTabs: empty and placeholder-only closes preserve Undo; real and mixed closes retain native history path; no empty-window close');
