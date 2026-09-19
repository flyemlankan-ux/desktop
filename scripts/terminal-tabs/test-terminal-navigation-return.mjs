#!/usr/bin/env node
// MPL-2.0. Native notification/menu lifecycle with production class, synthetic UI.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const base='chrome://browser/content/zen-terminal/terminal.xhtml';
const source=readFileSync('src/zen/terminal/ZenTerminalTabs.mjs','utf8').replace(/^import[\s\S]*?from\s+"[^"]+";\n/gm,'').replace(/^export /gm,'');
const records=new Map(),custom=new WeakMap(),events=new Map(),observers=new Set();
let progress,iconChanges=0,loads=[],deleted=0,errors=[],identities=[{userContextId:2}];
const menu={items:[],events:new Map(),appendChild(item){this.items.push(item);},addEventListener:(name,fn)=>menu.events.set(name,fn),removeEventListener:name=>menu.events.delete(name)};
const win={delayedStartupPromise:Promise.resolve(),setTimeout(){},addEventListener:(name,fn)=>events.set(name,fn),CreateContainerTabMenu(){},TabContextMenu:{}};
function makeBox(){return {PRIORITY_INFO_LOW:1,notification:null,appendCount:0,held:false,release:null,getNotificationWithValue(){return this.notification;},appendNotification(value,options,buttons){this.appendCount++;this.notification={value,options,buttons};const note=this.notification;return this.held?new Promise(resolve=>{this.release=()=>resolve(note); }):Promise.resolve(note);},removeNotification(item){if(item===this.notification)this.notification=null;item?.options.eventCallback('removed');}};}
const browser={tabs:[],getTabForBrowser:b=>browser.tabs.find(t=>t.linkedBrowser===b),addTabsProgressListener:value=>progress=value,removeTabsProgressListener(value){assert.equal(value,progress);progress=null;},getNotificationBox(b){return b._notificationBox||=makeBox();},setIcon(){iconChanges++;},_setTabLabel(){}};
const context=vm.createContext({window:win,gBrowser:browser,console:{error:(...args)=>errors.push(args)},URL,URLSearchParams,normalizeTerminalSessionId:v=>/^[a-z0-9-]+$/.test(v||'')?v:'',isTerminalContainerId:id=>String(id)==='2',getTerminalContainerRecipe:()=>({recipe:{steps:[]}}),setTerminalContainerRecipe(){},getTerminalSessionRecord:id=>records.get(id)||null,retryPendingTerminalSessionDeletes(){},registerTerminalSession(){throw Error('Navigation must not create session');},destroyTerminalSession(){deleted++;},ZEN_TERMINAL_SESSION_DELETE_TOPIC:'test-delete',Services:{prefs:{getBoolPref:()=>true},io:{newURI:spec=>({spec})},scriptSecurityManager:{getSystemPrincipal:()=>({system:true})},obs:{addObserver:o=>observers.add(o),removeObserver:o=>observers.delete(o)}},SessionStore:{getCustomTabValue:(t,k)=>custom.get(t)?.[k]||'',setCustomTabValue(t,k,v){custom.set(t,{...custom.get(t),[k]:v});},deleteCustomTabValue(t,k){delete custom.get(t)?.[k];},getTabState:()=>JSON.stringify({})},document:{getElementById:id=>id==='tabContextMenu'?menu:null,createXULElement:()=>({attrs:{},events:new Map(),setAttribute(k,v){this.attrs[k]=v;},addEventListener(name,fn){this.events.set(name,fn);}})},ChromeUtils:{importESModule:()=>({PrivateBrowsingUtils:{isWindowPrivate:w=>!!w.isPrivate},ContextualIdentityService:{getPublicIdentities:()=>identities},BrowserWindowTracker:{orderedWindows:[{gBrowser:browser}]},RunState:{isQuitting:false}})}});
vm.runInContext(source,context);await new Promise(resolve=>setImmediate(resolve));
const manager=win.gZenTerminalTabs;
function tab(id,{persistent=true,privateWindow=false,owner=2,receipt=true,url='https://example.com/project'}={}){
 const attrs=new Map();const box=makeBox();
 const t={ownerGlobal:{isPrivate:privateWindow},closing:false,linkedBrowser:{currentURI:{spec:url},browsingContext:{originAttributes:{userContextId:owner,privateBrowsingId:privateWindow?1:0}},_notificationBox:box,loadURI(uri,options){loads.push({uri,options});}},hasAttribute:k=>attrs.has(k),getAttribute:k=>attrs.get(k)||'',setAttribute:(k,v)=>attrs.set(k,String(v)),removeAttribute:k=>attrs.delete(k)};
 if(receipt)custom.set(t,{zenTerminalOwnership:JSON.stringify({id,userContextId:'2'})});
 records.set(id,{id,userContextId:'2',startupAttempted:true,persistent});browser.tabs.push(t);return t;
}
let checks=0;
const t=tab('owned');progress.onLocationChange(t.linkedBrowser,{isTopLevel:true});await new Promise(r=>setImmediate(r));
const box=t.linkedBrowser._notificationBox;
assert.match(box.notification.options.label,/Closing its last copy/);assert.equal(box.notification.buttons[0].label,'Return to terminal');assert.equal(iconChanges,0);assert.equal(loads.length,0);checks++;
await manager.updateTerminalAwayNotification(t);assert.equal(box.appendCount,1);checks++;
box.notification.options.eventCallback('dismissed');box.removeNotification(box.notification);
await manager.updateTerminalAwayNotification(t);assert.equal(box.notification,null);checks++;
// Simulate restored tab custom data: dismissal survives reload/restart, not memory only.
const restored=tab('owned');custom.set(restored,{...custom.get(t)});await manager.updateTerminalAwayNotification(restored);assert.equal(restored.linkedBrowser._notificationBox.notification,null);checks++;
win.TabContextMenu.contextTab=t;menu.events.get('popupshowing')({target:menu});const item=menu.items[0];assert.equal(item.hidden,false);item.events.get('command')();
assert.equal(loads.length,1);const returned=new URL(loads[0].uri.spec);assert.equal(returned.searchParams.get('session'),'owned');assert.equal(returned.searchParams.get('userContextId'),'2');assert.equal(returned.searchParams.get('started'),'1');assert.equal(loads[0].options.triggeringPrincipal.system,true);assert.equal(deleted,0);checks++;
t.linkedBrowser.currentURI.spec=returned.href;await manager.updateTerminalAwayNotification(t);assert.equal(t.hasAttribute('zen-terminal-away'),false);assert.equal(custom.get(t).zenTerminalAwayDismissed,undefined);checks++;
t.linkedBrowser.currentURI.spec='https://example.com/next';await manager.updateTerminalAwayNotification(t);assert.ok(box.notification);assert.equal(box.appendCount,2);checks++;
const plain=tab('plain',{persistent:false});await manager.updateTerminalAwayNotification(plain);assert.match(plain.linkedBrowser._notificationBox.notification.options.label,/unsaved terminal disconnected/);checks++;
for(const options of [{privateWindow:true},{owner:3},{receipt:false}]){const rejected=tab('rejected-'+checks,options);await manager.updateTerminalAwayNotification(rejected);assert.equal(manager.canReturnToTerminal(rejected),false);assert.equal(rejected.linkedBrowser._notificationBox.notification,null);assert.equal(manager.returnToTerminal(rejected),false);checks++;}
records.get('owned').pendingDelete=true;for(const observer of observers)observer.observe();await new Promise(r=>setImmediate(r));assert.equal(box.notification,null);assert.equal(manager.returnToTerminal(t),false);checks++;
const late=tab('late');const lateBox=late.linkedBrowser._notificationBox;lateBox.held=true;
const pending=manager.updateTerminalAwayNotification(late);
late.linkedBrowser.currentURI.spec=base+'?session=late&userContextId=2';
await manager.updateTerminalAwayNotification(late);
lateBox.release();await pending;
assert.equal(lateBox.notification,null,'late append result cannot resurface after returning');checks++;
// Ignore subframe changes; a website frame must not create a chrome notice.
const subframe=tab('subframe');progress.onLocationChange(subframe.linkedBrowser,{isTopLevel:false});
assert.equal(subframe.linkedBrowser._notificationBox.notification,null);checks++;
// A receipt alone cannot offer a restart before the original startup was attempted.
const unstarted=tab('unstarted');records.get('unstarted').startupAttempted=false;
await manager.updateTerminalAwayNotification(unstarted);
assert.equal(manager.canReturnToTerminal(unstarted),false);assert.equal(unstarted.linkedBrowser._notificationBox.notification,null);checks++;
// An already-visible button must recheck ownership, not trust its captured receipt.
const staleButton=tab('stale-button');await manager.updateTerminalAwayNotification(staleButton);
const staleAction=staleButton.linkedBrowser._notificationBox.notification.buttons[0].callback;
const beforeLoads=loads.length;records.get('stale-button').pendingDelete=true;staleAction();
assert.equal(loads.length,beforeLoads);checks++;
const removedIdentity=tab('removed-identity');await manager.updateTerminalAwayNotification(removedIdentity);
identities=[];assert.equal(manager.returnToTerminal(removedIdentity),false);
await manager.updateTerminalAwayNotification(removedIdentity);assert.equal(removedIdentity.linkedBrowser._notificationBox.notification,null);
identities=[{userContextId:2}];checks++;
// A pending notification must not survive actual close or session deletion.
for(const reason of ['closed','deleted']){
 const waiting=tab('waiting-'+reason),waitingBox=waiting.linkedBrowser._notificationBox;waitingBox.held=true;
 const append=manager.updateTerminalAwayNotification(waiting);
 if(reason==='closed')waiting.closing=true;else records.get('waiting-'+reason).pendingDelete=true;
 waitingBox.release();await append;assert.equal(waitingBox.notification,null);checks++;
}
// Multiple tabs share job ownership, but dismissing one must not hide the other's notice.
const firstMirror=tab('mirror'),secondMirror=tab('mirror');
await manager.updateTerminalAwayNotification(firstMirror);await manager.updateTerminalAwayNotification(secondMirror);
const firstBox=firstMirror.linkedBrowser._notificationBox;
firstBox.notification.options.eventCallback('dismissed');firstBox.removeNotification(firstBox.notification);
await manager.updateTerminalAwayNotification(firstMirror);await manager.updateTerminalAwayNotification(secondMirror);
assert.equal(firstBox.notification,null);assert.ok(secondMirror.linkedBrowser._notificationBox.notification);checks++;
secondMirror.multiselected=true;win.TabContextMenu.contextTab=secondMirror;
menu.events.get('popupshowing')({target:menu});assert.equal(item.hidden,true);checks++;
assert.equal(observers.size,1);events.get('unload')();assert.equal(observers.size,0);assert.equal(progress,null);assert.equal(menu.events.has('popupshowing'),false);checks++;
assert.equal(errors.length,0,JSON.stringify(errors));assert.equal(iconChanges,0);assert.equal(deleted,0);
console.log(`PASS ${checks} terminal navigation-return cases; production class, no UI`);
