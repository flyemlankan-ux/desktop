#!/usr/bin/env node
// MPL-2.0. Production tab lifecycle in an isolated synthetic browser, no UI.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const base='chrome://browser/content/zen-terminal/terminal.xhtml';
const source=readFileSync('src/zen/terminal/ZenTerminalTabs.mjs','utf8').replace(/^import[\s\S]*?from\s+"[^"]+";\n/gm,'').replace(/^export /gm,'');
function fixture(){
 const records=new Map(),destroyed=[],timers=[],listeners=new Map(),custom=new WeakMap();
 const state={isQuitting:false};
 const win={isPrivate:false,setTimeout:fn=>timers.push(fn),addEventListener:(name,fn)=>listeners.set(name,fn),CreateContainerTabMenu(){}};
 function tab({id='owned',owner=2,url=`${base}?session=${id}&userContextId=${owner}`,pending=false,privateWindow=false,receipt=false}={}){
  const attrs=new Map([['label','Job'],['usercontextid',String(owner)]]);
  if(pending)attrs.set('pending','true');
  const item={ownerGlobal:{isPrivate:privateWindow},linkedBrowser:{currentURI:{spec:pending?'about:blank':url},browsingContext:pending?null:{originAttributes:{userContextId:owner,privateBrowsingId:privateWindow?1:0}}},savedState:{userContextId:owner,entries:[{url}],index:1},style:{removeProperty(){}},hasAttribute:k=>attrs.has(k),getAttribute:k=>attrs.get(k)||'',setAttribute:(k,v)=>attrs.set(k,String(v)),removeAttribute:k=>attrs.delete(k)};
  if(receipt)custom.set(item,{zenTerminalOwnership:JSON.stringify({id,userContextId:String(owner)})});
  return item;
 }
 const browser={tabs:[],setIcon(){},_setTabLabel(){},addTab(url,options){const item=tab({owner:options.userContextId,url});browser.tabs.push(item);return item;}};
 const context=vm.createContext({console,URL,URLSearchParams,window:win,gBrowser:browser,normalizeTerminalSessionId:value=>/^[a-z0-9-]+$/.test(value||'')?value:'',getTerminalContainerRecipe:()=>({recipe:{steps:[]}}),isTerminalContainerId:id=>String(id)==='2',setTerminalContainerRecipe(){},getTerminalSessionRecord:id=>records.get(id)||null,registerTerminalSession(id,{userContextId}){const previous=records.get(id);if(previous&&(previous.pendingDelete||previous.userContextId!==userContextId))return null;const record={id,userContextId};records.set(id,record);return record;},destroyTerminalSession(id){destroyed.push(id);records.get(id).pendingDelete=true;},retryPendingTerminalSessionDeletes(){},Services:{prefs:{getBoolPref:()=>true},uuid:{generateUUID:()=>({toString:()=>'{fresh}'})},scriptSecurityManager:{getSystemPrincipal:()=>({})},prompt:{alert(){}}},SessionStore:{getCustomTabValue:(t,k)=>custom.get(t)?.[k]||'',setCustomTabValue(t,k,v){custom.set(t,{...custom.get(t),[k]:v});},getTabState:t=>JSON.stringify(t.savedState)},ChromeUtils:{importESModule:()=>({PrivateBrowsingUtils:{isWindowPrivate:w=>w.isPrivate},ContextualIdentityService:{getPublicIdentities:()=>[{userContextId:2}],getUserContextLabel:()=> 'Terminal'},BrowserWindowTracker:{orderedWindows:[{gBrowser:browser}]},RunState:state})}});
 vm.runInContext(source,context);timers.length=0;
 return {records,destroyed,tab,browser,win,state,manager:win.gZenTerminalTabs,flush(){while(timers.length)timers.shift()();},close(t,detail){t.closing=true;listeners.get('TabClose')({target:t,detail});},markRestored(t){listeners.get('SSTabRestored')({target:t});},addRecord(id='owned',owner='2'){records.set(id,{id,userContextId:owner});}};
}
let checks=0;
for(const options of [{url:base+'.evil?session=owned&userContextId=2'},{owner:3,url:base+'?session=owned&userContextId=2'},{privateWindow:true},{url:base+'?session=../owned&userContextId=2'},{url:'https://example.com/?session=owned'}]){
 const f=fixture();f.addRecord();const t=f.tab(options);f.browser.tabs=[t];f.markRestored(t);f.close(t);f.flush();assert.deepEqual(f.destroyed,[],JSON.stringify(options));checks++;
}
for(const options of [{},{pending:true},{url:'https://example.com/',receipt:true}]){
 const f=fixture();f.addRecord();const t=f.tab(options);f.browser.tabs=[t];f.close(t);f.flush();assert.deepEqual(f.destroyed,['owned']);checks++;
}
{
 const f=fixture();f.addRecord();const a=f.tab(),b=f.tab({pending:true});f.browser.tabs=[a,b];f.close(a);f.flush();assert.deepEqual(f.destroyed,[]);f.close(b);f.flush();assert.deepEqual(f.destroyed,['owned']);checks++;
}
{
 const f=fixture();f.addRecord();const good=f.tab(),wrong=f.tab({owner:3,url:base+'?session=owned&userContextId=2'});f.browser.tabs=[good,wrong];f.close(good);f.flush();assert.deepEqual(f.destroyed,['owned'],'rejected viewer must not keep unrelated work alive');checks++;
}
for(const reason of ['adopted','quit','windowclose']){
 const f=fixture();f.addRecord();const t=f.tab();f.browser.tabs=[t];if(reason==='quit')f.state.isQuitting=true;if(reason==='windowclose')f.win._zenClosingWindow=true;f.close(t,reason==='adopted'?{adoptedBy:{}}:{});f.flush();assert.deepEqual(f.destroyed,[]);checks++;
}
{
 const f=fixture();const t=f.manager.openTerminalContainerTab(2);assert.ok(f.records.has('fresh'),'opener establishes owner before page startup');f.close(t);f.flush();assert.deepEqual(f.destroyed,['fresh']);checks++;
}
{
 const f=fixture();f.addRecord();const t=f.tab({pending:true});f.browser.tabs=[t];f.markRestored(t);assert.ok(t.__zenTerminalOwnership);t.linkedBrowser.currentURI.spec='https://example.com';t.removeAttribute('pending');t.linkedBrowser.browsingContext={originAttributes:{userContextId:2,privateBrowsingId:0}};f.close(t);f.flush();assert.deepEqual(f.destroyed,['owned'],'restored receipt survives navigation');checks++;
}
{
 const f=fixture();f.browser.addTab=()=>{throw Error('synthetic addTab failure');};assert.throws(()=>f.manager.openTerminalContainerTab(2));assert.deepEqual(f.destroyed,['fresh']);f.addRecord('old');assert.throws(()=>f.manager.openTerminalTab({userContextId:2,terminalSessionId:'old'}));assert.deepEqual(f.destroyed,['fresh'],'failed duplicate open never kills preexisting job');checks++;
}
console.log(`PASS ${checks} close-ownership cases (actual production class; no UI)`);
