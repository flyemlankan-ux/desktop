#!/usr/bin/env node
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync('src/zen/terminal/ZenTerminalPage.mjs','utf8');
const lifecycle=source.slice(source.indexOf('function startTerminalAccessibilityObserver()'),source.indexOf('function initTerminal()'));
for(const initiallyEnabled of [false,true]){
 const observers=new Set();let additions=0,removals=0;
 const context=vm.createContext({accessibilityObserver:null,stopping:false,terminal:{options:{screenReaderMode:false}},Services:{appinfo:{accessibilityEnabled:initiallyEnabled},obs:{
  addObserver(observer,topic){assert.equal(topic,'a11y-init-or-shutdown');observers.add(observer);additions++;},
  removeObserver(observer,topic){assert.equal(topic,'a11y-init-or-shutdown');assert(observers.delete(observer));removals++;}
 }}});
 vm.runInContext(lifecycle,context);
 vm.runInContext('startTerminalAccessibilityObserver();startTerminalAccessibilityObserver();',context);
 assert.equal(observers.size,1);assert.equal(additions,1);assert.equal(context.terminal.options.screenReaderMode,initiallyEnabled);
 const observer=[...observers][0];
 observer.observe(null,'unrelated','1');assert.equal(context.terminal.options.screenReaderMode,initiallyEnabled);
 for(const data of ['pdf','pdfonly','unexpected',null]){observer.observe(null,'a11y-init-or-shutdown',data);assert.equal(context.terminal.options.screenReaderMode,initiallyEnabled);}
 observer.observe(null,'a11y-init-or-shutdown','1');assert.equal(context.terminal.options.screenReaderMode,true);
 observer.observe(null,'a11y-init-or-shutdown','1');assert.equal(observers.size,1);
 observer.observe(null,'a11y-init-or-shutdown','0');assert.equal(context.terminal.options.screenReaderMode,false);
 context.stopping=true;observer.observe(null,'a11y-init-or-shutdown','1');assert.equal(context.terminal.options.screenReaderMode,false);
 vm.runInContext('stopTerminalAccessibilityObserver();stopTerminalAccessibilityObserver();',context);
 assert.equal(observers.size,0);assert.equal(removals,1);assert.equal(context.accessibilityObserver,null);
 vm.runInContext('startTerminalAccessibilityObserver()',context);assert.equal(additions,1);
}
assert.match(source,/terminal\.open\(output\);\s*startTerminalAccessibilityObserver\(\);/);
assert.match(source,/async function stopShell\(\) \{\s*stopTerminalAccessibilityObserver\(\);/);
console.log('PASS accessibility lifecycle: initially on/off, late full activation, shutdown, PDF/unknown ignored, duplicate subscription, stopping guard and idempotent teardown');
