#!/usr/bin/env node
// MPL-2.0. Real production classes in a synthetic browser; not native UI proof.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const timers=[], listeners=new Map(), custom=new WeakMap();
const sid='11111111-1111-4111-8111-111111111111';
const url='chrome://browser/content/zen-terminal/terminal.xhtml?session='+sid;
const window={setTimeout(fn){timers.push(fn);},addEventListener(name,fn){listeners.set(name,fn);},CreateContainerTabMenu(){}};
const gBrowser={tabs:[],setIcon(tab,icon){tab.image=icon;tab.linkedBrowser.mIconURL=icon;tab.setAttribute('image',icon);listeners.get('TabAttrModified')?.({target:tab,detail:{changed:['image']}});},_setTabLabel(tab,label){tab.setAttribute('label',label);},unpinTab(){throw Error('Marker must not unpin');},pinTab(){throw Error('Marker must not pin');}};
const context=vm.createContext({console,URL,URLSearchParams,window,gBrowser,
 nsZenDOMOperatedFeature:class {},
 getTerminalContainerRecipe:()=>({recipe:{steps:[]}}),isTerminalContainerId:()=>true,setTerminalContainerRecipe(){},
 normalizeTerminalSessionId:value=>value===sid?value:'',retryPendingTerminalSessionDeletes(){},destroyTerminalSession(){throw Error('Organization must not destroy sessions');},
 Services:{prefs:{getBoolPref:()=>true}},
 SessionStore:{getCustomTabValue(tab,key){return custom.get(tab)?.[key]||'';},setCustomTabValue(tab,key,value){custom.set(tab,{...custom.get(tab),[key]:value});},getTabState:()=>JSON.stringify({entries:[{url}],index:1})},
 ChromeUtils:{importESModule(){return {ContextualIdentityService:{},BrowserWindowTracker:{orderedWindows:[{gBrowser}]},RunState:{isQuitting:false}}}},
 document:{l10n:{setArgs(){}}}
});
function production(path){return readFileSync(path,'utf8').replace(/^import[\s\S]*?from\s+"[^"]+";\n/gm,'').replace(/^export /gm,'');}
vm.runInContext(production('src/zen/terminal/ZenTerminalTabs.mjs'),context);
vm.runInContext(production('src/zen/tabs/ZenPinnedTabManager.mjs'),context);
const marker=window.gZenTerminalTabs, pins=window.gZenPinnedTabManager;
function tab({pinned=true,essential=false,pending=false,split=false}={}) {
 const attrs=new Map([['label','My job'],['zen-workspace-id','workspace-2'],['zenDefaultUserContextId','4'],['zen-pinned-changed','true'],['had-zen-pinned-changed','true']]);
 if(essential)attrs.set('zen-essential','true'); if(pending)attrs.set('pending','true');
 const style=new Map([['--zen-original-tab-icon','old']]);
 return {pinned,group:{parent:{name:'outer folder'},hasAttribute:()=>split},_zenPinnedInitialState:{entry:{url},image:'icon'},linkedBrowser:{currentURI:{spec:pending?'about:blank':url}},
 hasAttribute:key=>attrs.has(key),getAttribute:key=>attrs.get(key)||'',setAttribute:(key,value)=>attrs.set(key,String(value)),removeAttribute:key=>attrs.delete(key),
 style:{removeProperty:key=>style.delete(key),setProperty:(key,value)=>style.set(key,value)},querySelector:()=>({})};
}
let checks=0;
for(const mode of [{},{essential:true},{pending:true},{split:true},{pinned:false}]){
 const t=tab(mode), group=t.group, initial=t._zenPinnedInitialState; gBrowser.tabs=[t];
 marker.markTerminalTab(t,{terminalSessionId:sid,preserveExistingLabel:true});
 marker.markTerminalTab(t,{preserveExistingLabel:true});
 listeners.get('TabSelect')({target:t});listeners.get('SSTabRestored')({target:t});
 while(timers.length)timers.shift()();
 assert.equal(t.pinned,mode.pinned!==false); assert.equal(t.hasAttribute('zen-essential'),!!mode.essential);
 assert.equal(t.group,group);assert.equal(t._zenPinnedInitialState,initial);
 assert.equal(t.getAttribute('zen-workspace-id'),'workspace-2');assert.equal(t.getAttribute('zenDefaultUserContextId'),'4');
 assert.equal(t.image,'chrome://browser/skin/zen-icons/selectable/terminal.svg');
 assert.equal(t.zenStaticIcon,undefined);
 assert.equal(t.getAttribute('label'),'My job');assert.equal(t.getAttribute('zen-terminal-session-id'),sid);
 t.setAttribute('zen-pinned-changed','true');t.setAttribute('had-zen-pinned-changed','true');pins.pinHasChangedUrl(t);
 assert.equal(t.hasAttribute('zen-pinned-changed'),false);assert.equal(t.hasAttribute('had-zen-pinned-changed'),false);
 assert.equal(t._zenPinnedInitialState,initial);checks++;
}
for(const split of [false,true]){
 const website=tab({split});website.removeAttribute('zen-pinned-changed');website.removeAttribute('had-zen-pinned-changed');
 pins.pinHasChangedUrl(website);
 assert.equal(website.hasAttribute(split?'had-zen-pinned-changed':'zen-pinned-changed'),true);checks++;
}
const t=tab();marker.markTerminalTab(t);t.pinned=false;marker.markTerminalTab(t);while(timers.length)timers.shift()();assert.equal(t.pinned,false);checks++;
for(const customIcon of ['data:image/svg+xml,my-icon','https://example.invalid/chosen-icon.svg']){
 const customTab=tab({essential:true});customTab.zenStaticIcon=customIcon;
 marker.markTerminalTab(customTab,{preserveExistingLabel:true});
 assert.equal(customTab.image,customIcon);assert.equal(customTab.zenStaticIcon,customIcon);checks++;
}
// Replay the real Firefox location-change sequence after restored marking:
// browser icon reset, native image removal, then its TabAttrModified event.
for(const pending of [false,true]){
 const restored=tab({pending});marker.markTerminalTab(restored,{preserveExistingLabel:true});
 restored.linkedBrowser.mIconURL='';restored.removeAttribute('image');
 listeners.get('TabAttrModified')({target:restored,detail:{changed:['image']}});
 assert.equal(restored.getAttribute('image'),'chrome://browser/skin/zen-icons/selectable/terminal.svg');
 assert.equal(restored.linkedBrowser.mIconURL,restored.getAttribute('image'));
 assert.equal(restored.zenStaticIcon,undefined);checks++;
}
const customRestored=tab();customRestored.zenStaticIcon='data:image/svg+xml,chosen';
marker.markTerminalTab(customRestored);listeners.get('TabAttrModified')({target:customRestored,detail:{changed:['image']}});
assert.equal(customRestored.getAttribute('image'),customRestored.zenStaticIcon);checks++;
const navigated=tab();marker.markTerminalTab(navigated);navigated.linkedBrowser.currentURI.spec='https://example.invalid/';
navigated.removeAttribute('image');listeners.get('TabAttrModified')({target:navigated,detail:{changed:['image']}});
assert.equal(navigated.hasAttribute('image'),false,'Never force terminal icon onto a navigated website');checks++;
console.log(`PASS ${checks} native organization logic cases (synthetic browser; real classes)`);
