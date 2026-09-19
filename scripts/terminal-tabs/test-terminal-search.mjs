import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
const root = new URL('../../', import.meta.url);
const read = path => fs.readFileSync(new URL(path, root), 'utf8');
const page = read('src/zen/terminal/ZenTerminalPage.mjs');
const receipt = JSON.parse(read('src/zen/terminal/vendor/addon-search-receipt.json'));
assert.equal(receipt.gitHead, 'f447274f430fd22513f6adbf9862d19524471c04');
for (const [file, hash] of Object.entries(receipt.sha256)) {
  assert.equal(crypto.createHash('sha256').update(read('src/zen/terminal/vendor/' + file)).digest('hex'), hash);
}
const elements = Object.fromEntries(['find', 'find-input', 'find-result'].map(id => ['zen-terminal-' + id, {hidden:true, value:'', textContent:'', focus(){this.focused=true;}, select(){this.selected=true;}}]));
const calls=[];
const context=vm.createContext({document:{getElementById:id=>elements[id]}, terminal:{focus(){calls.push('focus');}, clearSelection(){calls.push('clear');}}, stopping:false, surface:{toggleAttribute(){}}, scheduleTerminalFit(){}, searchAddon:{clearDecorations(){},findNext(q,o){calls.push({q,...o,next:true}); return q==='literal.*';},findPrevious(q,o){calls.push({q,...o,next:false}); return true;}}});
vm.runInContext(page.slice(page.indexOf('function runTerminalSearch('), page.indexOf('function getShellCommand()')), context);
function key(key, extra={}) {const event={key,type:'keydown',preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;},...extra}; context.event=event;vm.runInContext('handleTerminalSearchKey(event)',context);return event;}
assert(key('f',{metaKey:true}).prevented);
assert.equal(elements['zen-terminal-find'].hidden,false);
assert(elements['zen-terminal-find-input'].focused);
elements['zen-terminal-find-input'].value='literal.*';
vm.runInContext('runTerminalSearch(false,true)',context);
assert.equal(calls.at(-1).regex,false);assert.equal(calls.at(-1).incremental,true);
assert.equal(elements['zen-terminal-find-result'].textContent,'Match found');
assert(key('Enter',{shiftKey:true}).stopped);assert.equal(calls.at(-1).next,false);
elements['zen-terminal-find-input'].value='missing';key('Enter');assert.equal(elements['zen-terminal-find-result'].textContent,'No matches');
assert.equal(key('Enter',{isComposing:true}).prevented,undefined);
assert(key('Escape').prevented);assert.equal(elements['zen-terminal-find'].hidden,true);assert.equal(calls.at(-1),'focus');
assert.equal(key('Enter').prevented,undefined);assert.equal(key('f',{altKey:true,ctrlKey:true}).prevented,undefined);
assert(key('f',{ctrlKey:true}).prevented);
elements['zen-terminal-find-input'].value='';vm.runInContext('runTerminalSearch()',context);assert.equal(elements['zen-terminal-find-result'].textContent,'');
assert.match(page,/scrollback: 10000/);assert.match(page,/allowProposedApi: false/);
console.log('Terminal search focused tests passed: exact vendor bytes, literal incremental search, previous/next, shortcut interception, IME Enter, close focus, blank/no-match and bounded scrollback. Native key dispatch is a separate acceptance test.');
