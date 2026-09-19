#!/usr/bin/env node
// MPL-2.0. Exercises production methods with synthetic browser objects, not native UI.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync('src/zen/terminal/ZenTerminalTabs.mjs','utf8').replace(/^import[\s\S]*?from\s+"[^"]+";\n/gm,'').replace(/^export /gm,'');
let privateWindow=false, alerts=0, adds=0;
const identities=[{userContextId:1},{userContextId:2}];
function popup(){return {rows:[],querySelectorAll(){return this.rows.filter(r=>!r.removed);}};}
function row(id){return {id,removed:false,getAttribute(){return String(id);},setAttribute(){},removeAttribute(){},addEventListener(){},remove(){this.removed=true;}};}
const window={setTimeout(){},addEventListener(){},createUserContextMenu(event){event.target.rows=[row(0),row(1),row(2)];return true;},CreateContainerTabMenu(event){return window.createUserContextMenu(event,{showDefaultTab:true});}};
const context=vm.createContext({window,console,URL,URLSearchParams,
 getTerminalContainerRecipe:()=>({recipe:{steps:[]}}),isTerminalContainerId:id=>String(id)==='2',setTerminalContainerRecipe(){},retryPendingTerminalSessionDeletes(){},normalizeTerminalSessionId:()=>'',destroyTerminalSession(){},
 Services:{prefs:{getBoolPref:()=>true},prompt:{alert(){alerts++;}},uuid:{generateUUID(){throw Error('private launch must not allocate session');}}},
 gBrowser:{setIcon(tab,icon){tab.image=icon;},_setTabLabel(tab,label){tab.setAttribute('label',label);},addTab(){adds++;throw Error('private launch must not create a tab');}},
 ChromeUtils:{importESModule(){return {ContextualIdentityService:{getPublicIdentities:()=>identities},BrowserWindowTracker:{orderedWindows:[]},RunState:{isQuitting:false},PrivateBrowsingUtils:{isWindowPrivate:()=>privateWindow}};}}
});
vm.runInContext(source,context);let checks=0;
const tabs=window.gZenTerminalTabs;
for(const customIcon of [undefined,'data:image/svg+xml,chosen']){
 const attrs=new Map([['label','My terminal']]);
 const tab={zenStaticIcon:customIcon,style:{removeProperty(){}},setAttribute:(key,value)=>attrs.set(key,value),getAttribute:key=>attrs.get(key),removeAttribute:key=>attrs.delete(key)};
 tabs.markTerminalTab(tab,{preserveExistingLabel:true});
 assert.equal(tab.image,customIcon||'chrome://browser/skin/zen-icons/selectable/terminal.svg');
 assert.equal(tab.zenStaticIcon,customIcon);checks++;
}
for(const kind of ['link','tab reopen','workspace default']){
 const p=popup();window.createUserContextMenu({target:p},{isContextMenu:true});
 assert.deepEqual(p.querySelectorAll().map(r=>r.id),[0,1],kind);checks++;
}
for(const opener of [p=>tabs.populateUnifiedContainerMenu({target:p}),p=>window.CreateContainerTabMenu({target:p})]){
 const p=popup();opener(p);assert.deepEqual(p.querySelectorAll().map(r=>r.id),[0,1,2]);checks++;
}
privateWindow=true;
assert.equal(tabs.openTerminalTab({userContextId:2}),null);assert.equal(alerts,1);assert.equal(adds,0);checks++;
const privatePopup=popup();tabs.populateUnifiedContainerMenu({target:privatePopup});assert.deepEqual(privatePopup.querySelectorAll().map(r=>r.id),[0,1]);checks++;
// Evaluate the exact production page validator; no reimplementation of its logic.
const page=readFileSync('src/zen/terminal/ZenTerminalPage.mjs','utf8');
const validator=page.slice(page.indexOf('function validateTerminalPageContext()'),page.indexOf('async function startShell('));
let requested='2',actual=2,isPrivate=false,publicIds=identities;
const pageContext=vm.createContext({window:{docShell:{QueryInterface:()=>({usePrivateBrowsing:isPrivate,originAttributes:{userContextId:actual}})}},Ci:{nsILoadContext:{}},getTerminalUserContextId:()=>requested,ChromeUtils:{importESModule:()=>({ContextualIdentityService:{getPublicIdentities:()=>publicIds}})}});
vm.runInContext(validator+';globalThis.validate=validateTerminalPageContext;',pageContext);
pageContext.validate();checks++;
for(const bad of ['1','02','0','-1','2e0','2x','9007199254740993','']){
 requested=bad;assert.throws(()=>pageContext.validate(),/does not match/);checks++;
}
requested='2';isPrivate=true;assert.throws(()=>pageContext.validate(),/private windows/);checks++;
isPrivate=false;publicIds=[];assert.throws(()=>pageContext.validate(),/no longer exists/);checks++;
assert.ok(page.indexOf('    validateTerminalPageContext();')<page.indexOf('    if (!getStartupRecord())'));
assert.ok(page.indexOf('    validateTerminalPageContext();')<page.indexOf('      !registerTerminalSession('));checks++;
console.log(`PASS ${checks} terminal entry-point and page-context cases (synthetic browser; production methods)`);

const spaces=readFileSync('src/zen/spaces/ZenSpaceManager.mjs','utf8');
const method=spaces.slice(spaces.indexOf('  getContextIdIfNeeded('),spaces.indexOf('  getTabsToExclude('));
const methodContext=vm.createContext({isTerminalContainerId:id=>id===2});
vm.runInContext('globalThis.getContext=({'+method+'}).getContextIdIfNeeded;',methodContext);
const workspace={workspaceEnabled:true,shouldForceContainerTabsToWorkspace:false,getActiveWorkspaceFromCache:()=>({containerTabId:2})};
assert.equal(methodContext.getContext.call(workspace,undefined,false,null)[0],0);
assert.equal(methodContext.getContext.call(workspace,1,false,null)[0],1);
assert.equal(methodContext.getContext.call(workspace,2,false,null)[0],2,'explicit terminal opener retains its requested identity');
workspace.getActiveWorkspaceFromCache=()=>({containerTabId:1});
assert.equal(methodContext.getContext.call(workspace,undefined,false,null)[0],1);
console.log('PASS 4 stale workspace-default cases (production method)');
