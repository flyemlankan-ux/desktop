#!/usr/bin/env node
// MPL-2.0. Exact upstream source patches and real menu-building callback, no UI.
import assert from 'node:assert/strict';
import {readFileSync,cpSync,mkdtempSync,rmSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {tmpdir} from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
const root=path.resolve(import.meta.dirname,'../..');
const fixtures=path.join(import.meta.dirname,'fixtures/firefox-alltabs');
const receipt=JSON.parse(readFileSync(path.join(fixtures,'receipt.json')));
const patch=path.join(root,'src/browser/components/tabbrowser/content/browser-allTabsMenu-js.patch');
let count=0;
for(const file of receipt.files){
 const original=readFileSync(path.join(fixtures,file.version,file.path));
 assert.equal(createHash('sha256').update(original).digest('hex'),file.sha256);
 assert.equal(createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${original.length}\0`),original])).digest('hex'),file.git_blob_sha);
 const temp=mkdtempSync(path.join(tmpdir(),'zen-alltabs-proof-'));
 try{
  cpSync(path.join(fixtures,file.version),temp,{recursive:true});
  execFileSync('patch',['--dry-run','--batch','--fuzz=0','-p1','-i',patch],{cwd:temp});
  execFileSync('patch',['--batch','--fuzz=0','-p1','-i',patch],{cwd:temp});
  const source=readFileSync(path.join(temp,file.path),'utf8');
  const callback=source.match(/this\.containerTabsView\.addEventListener\("ViewShowing", e => \{([\s\S]*?)\n    \}\);/);
  assert.ok(callback,'actual ViewShowing callback found');
  const identities=[{userContextId:1,name:'Web A',icon:'briefcase',color:'blue'},{userContextId:2,name:'Shell',icon:'briefcase',color:'purple'},{userContextId:3,name:'Web B',icon:'fingerprint',color:'red'}];
  let terminalIds=new Set([2]),rendered=[],hide;
  const context=vm.createContext({ContextualIdentityService:{getPublicIdentities:()=>identities},ChromeUtils:{importESModule(uri){assert.equal(uri,'chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs');return{isTerminalContainerId:id=>terminalIds.has(id)};}},document:{createDocumentFragment(){return {children:[],appendChild(item){this.children.push(item);}};},createXULElement(tag){assert.equal(tag,'toolbarbutton');return{attrs:{},setAttribute(k,v){this.attrs[k]=v;},classList:{add(){}},remove(){this.removed=true;}};}},containerTabsMenuSeparator:{parentNode:{insertBefore(frag){rendered=frag.children;}}}});
  vm.runInContext('globalThis.show=function(e){'+callback[1]+'};',context);
  const event={target:{addEventListener(name,fn){assert.equal(name,'ViewHiding');hide=fn;}}};
  context.show(event);
  assert.deepEqual(rendered.map(x=>x.attrs['data-usercontextid']),[1,3]);
  assert.ok(rendered.every(x=>x.attrs.command==='Browser:NewUserContextTab'));
  assert.deepEqual(rendered.map(x=>x.attrs.label),['Web A','Web B']);
  hide();assert.ok(rendered.every(x=>x.removed));count++;
  terminalIds=new Set();context.show(event);assert.deepEqual(rendered.map(x=>x.attrs['data-usercontextid']),[1,2,3]);count++;
  terminalIds=new Set([1,2,3]);context.show(event);assert.equal(rendered.length,0);count++;
  console.log(`PASS Firefox${file.version} exact patch; mixed, web-only, all-terminal native-list cases`);
 }finally{rmSync(temp,{recursive:true,force:true});}
}
console.log(`PASS ${count} All Tabs menu cases; 2 pinned upstream patch applications; no UI launched`);
