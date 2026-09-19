#!/usr/bin/env node
// MPL-2.0. Strict Firefox156 patches + real production methods, synthetic DOM.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtempSync,readFileSync,mkdirSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import vm from 'node:vm';
const root=path.resolve(import.meta.dirname,'../..');
const fixture=path.join(import.meta.dirname,'fixtures/firefox156-associations');
const receipt=JSON.parse(readFileSync(path.join(fixture,'receipt.json')));
assert.equal(receipt.tag,'FIREFOX_156_0_RELEASE');
const patched=new Map(), temporary=mkdtempSync(path.join(tmpdir(),'zen-associations156-'));
try {
 for(const file of receipt.files){
  const bytes=readFileSync(path.join(fixture,file.path));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),file.sha256);
  assert.equal(createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${bytes.length}\0`),bytes])).digest('hex'),file.git_blob_sha);
  const dest=path.join(temporary,file.path);mkdirSync(path.dirname(dest),{recursive:true});writeFileSync(dest,bytes);
  const patch=path.join(root,'src',path.dirname(file.path),path.basename(file.path).replaceAll('.','-')+'.patch');
  execFileSync('patch',['--batch','--fuzz=0','--dry-run','-p1','-i',patch],{cwd:temporary});
  execFileSync('patch',['--batch','--fuzz=0','-p1','-i',patch],{cwd:temporary});
  patched.set(path.basename(file.path),readFileSync(dest,'utf8'));
 }
} finally {rmSync(temporary,{recursive:true,force:true});}
let ids=[{userContextId:2,icon:'briefcase',color:'blue'},{userContextId:7,icon:'circle',color:'purple'}];
const terminal=new Set([7]), associations=[], alerts=[];
const service={getPublicIdentities:()=>ids,getUserContextLabel:id=>'Identity '+id,getContainerIconURL:icon=>'icon:'+icon,setSiteAssociation:(site,id)=>associations.push([site,id]),getSiteAssociation:()=>0,normalizeSite:site=>site.includes('.')?site:null};
class Element {
 constructor(tag='select'){this.localName=tag;this.attrs=new Map();this.listeners=new Map();this.children=[];this.value='';this.updateComplete=Promise.resolve();this.inputEl=this;}
 addEventListener(name,fn){this.listeners.set(name,fn);}
 setAttribute(name,value){this.attrs.set(name,value);}
 removeAttribute(name){this.attrs.delete(name);}
 hasAttribute(name){return this.attrs.has(name);}
 toggleAttribute(name,value){if(value)this.setAttribute(name,'');else this.removeAttribute(name);}
 append(...children){this.children.push(...children);}
 focus(){this.focused=true;}
}
const stripImports=source=>source.replace(/^import[\s\S]*?from "[^"]+";\n/gm,'');
const context=vm.createContext({console,MozSelect:Element,MutationObserver:class{observe(){}},html(){},customElements:{define(){}},
 isTerminalContainerId:id=>terminal.has(Number(id)),Services:{prompt:{alert:(_win,title,text)=>alerts.push({title,text})}},
 ChromeUtils:{defineESModuleGetters:target=>target.ContextualIdentityService=service}});
vm.runInContext(stripImports(patched.get('container-select.mjs')).replace('export default class ContainerSelect','globalThis.ContainerSelect = class ContainerSelect').replace(/^export /gm,''),context);
let checks=0;
const options=()=>Array.from(context.containerOptions(),o=>({...o}));
assert.deepEqual(options(),[{value:'2',label:'Identity 2',iconsrc:'icon:briefcase',itemclass:'identity-color-blue'}]);checks++;
ids=[ids[1]];assert.deepEqual(options(),[]);checks++;
ids=[{userContextId:2,icon:'briefcase',color:'blue'},{userContextId:7,icon:'circle',color:'purple'}];
for(const value of ['7','7tail','2tail','0','-2','','9007199254740992','999']){
 const select=new context.ContainerSelect();select.site='example.invalid';select.value=value;select.listeners.get('change')();assert.equal(select.value,'');assert.equal(select.hasAttribute('aria-invalid'),true);assert.equal(associations.length,0);checks++;
}
const valid=new context.ContainerSelect();valid.site='example.invalid';valid.value='2';valid.listeners.get('change')();assert.deepEqual(associations.pop(),['example.invalid',2]);checks++;
terminal.add(2);valid.value='2';valid.listeners.get('change')();assert.equal(associations.length,0);assert.equal(valid.value,'');checks++;terminal.delete(2);
assert.equal(alerts.length,9);

// Drive the actual site dialog acceptance callback, not a recreated validator.
const elements=[],docEvents=new Map(),windowEvents=new Map();
const document={createElement(tag){const e=new Element(tag);elements.push(e);return e;},getElementById(){return new Element('form');},querySelector(){return {getButton:()=>({disabled:false})};},addEventListener:(event,fn)=>docEvents.set(event,fn),l10n:{setAttributes(el,id){el.setAttribute('data-l10n-id',id);}}};
const dialog=vm.createContext({document,window:{addEventListener:(event,fn)=>windowEvents.set(event,fn),resizeDialog(){}},Services:{io:{newURI(value){const u=new URL(value);return {scheme:u.protocol.slice(0,-1),host:u.hostname};}}},ChromeUtils:{importESModule(url){return url.includes('container-select')?{containerOptions:context.containerOptions,isWebContainerId:context.isWebContainerId}:{ContextualIdentityService:service};}}});
vm.runInContext(patched.get('siteContainer.js'),dialog);await windowEvents.get('DOMContentLoaded')();
const input=elements.find(e=>e.localName==='moz-input-text'),select=elements.find(e=>e.localName==='container-select'),error=elements.find(e=>e.id==='siteContainerError');
assert.deepEqual(select.children.map(e=>e.attrs.get('value')),['2']);checks++;
for(const value of ['7','2tail','999','']){
 input.value='example.invalid';select.value=value;let prevented=false;docEvents.get('dialogaccept')({preventDefault(){prevented=true;}});
 assert.equal(prevented,true);assert.equal(select.value,'');assert.equal(associations.length,0);assert.match(error.textContent,/Choose an existing web container/);checks++;
}
terminal.add(2);input.value='example.invalid';select.value='2';let cancelled=false;docEvents.get('dialogaccept')({preventDefault(){cancelled=true;}});assert.equal(cancelled,true);assert.equal(associations.length,0);checks++;terminal.delete(2);
input.value='https://example.invalid/path';select.value='2';docEvents.get('dialogaccept')({preventDefault(){throw Error('valid website must remain accepted');}});assert.deepEqual(associations.pop(),['example.invalid',2]);checks++;
// Both native settings chooser producers must use the filtered shared options.
const config=patched.get('containers.mjs');
assert.equal((config.match(/this\.containers = containerOptions\(\);/g)||[]).length,2);
assert.equal((config.match(/this\.containers = lazy\.ContextualIdentityService\.getPublicIdentities\(\);/g)||[]).length,1); // Main manager must still show ALL setups.checks++;
const registrations=[];
const cfgContext=vm.createContext({
  containerOptions:context.containerOptions,
  Preferences:{AsyncSetting:class{},addAll(){},addSetting:setting=>registrations.push(setting)},
  SettingGroupManager:{registerGroups(){}},
  history:{state:null}, URL:{fromURI:()=>new URL('about:preferences')},
  document:{documentURIObject:{},addEventListener(){}},
  ChromeUtils:{defineESModuleGetters:target=>target.ContextualIdentityService=service,defineLazyGetter(){}},
});
vm.runInContext(stripImports(config),cfgContext);
const AddSite=registrations.find(setting=>setting.id==='site-containers-add-button');
assert.ok(AddSite);const addSite=new AddSite();
ids=[{userContextId:7,icon:'circle',color:'purple'}];addSite.beforeRefresh();assert.equal(await addSite.disabled(),true);checks++;
ids.push({userContextId:2,icon:'briefcase',color:'blue'});addSite.beforeRefresh();assert.equal(await addSite.disabled(),false);checks++;
console.log(`PASS ${checks} Firefox156 website-association cases; 3 strict pinned-source patch applications. No native UI proof.`);
