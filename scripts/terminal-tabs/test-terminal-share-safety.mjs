#!/usr/bin/env node
// MPL-2.0. Production share safety and production methods with test-only services.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import * as safety from '../../src/zen/share/ZenShareSafety.sys.mjs';
const bad=['chrome://browser/content/zen-terminal/terminal.xhtml?userContextId=1','resource:///modules/x','file:///tmp/x','data:text/html,x','javascript:alert(1)','about:config','//example.com/x','/relative','https:example.com','https:///',' https://example.com','https://example.com\n','https:\\example.com','https://','not a url','ftp://example.com'];
const good=['https://example.com/path?q=x#part','http://localhost:8080/','HTTPS://EXAMPLE.COM/','https://[::1]/','https://example.com/%20'];
let checks=0;
for(const url of bad){assert.equal(safety.isSafeShareWebURL(url),false,url);assert.throws(()=>safety.assertSafeShareDocument({shared:{type:'folder',items:[{type:'tab',url:'https://good.example'},{type:'folder',items:[{type:'tab',url}]}]}}),error=>error.code==='invalid-document');checks++;}
for(const url of good){assert.equal(safety.isSafeShareWebURL(url),true,url);checks++;}
const valid={shared:{type:'space',name:'Project',items:[{type:'folder',name:'Mixed',items:[{type:'tab',url:good[0]}]},{type:'splitView',tabs:[{type:'tab',url:good[1]},{type:'tab',url:good[2]}]}]}};
assert.equal(safety.assertSafeShareDocument(valid),3);checks++;
const cycle={type:'folder',items:[]};cycle.items.push(cycle);assert.throws(()=>safety.assertSafeShareDocument({shared:cycle}));checks++;
const strip=source=>source.replace(/^import .*;\n/gm,'').replace(/^export /gm,'').replace(/#(?=[a-zA-Z])/g,'_');
let creations=0,uploads=0,confirms=0,toasts=[];
let preview;
const realConsole=console;
class ShareError extends Error {constructor(code,message){super(message);this.code=code;}}
const context=vm.createContext({...safety,URL,console:{error(){}},nsZenDOMOperatedFeature:class{},nsZenThemePicker:{},window:{},Services:{prefs:{getStringPref:()=>'',getBoolPref:()=>false}},gZenWorkspaces:{privateWindowOrDisabled:false,activeWorkspace:'space'},gZenViewSplitter:{MAX_TABS:4},gZenUIManager:{showToast:(...args)=>toasts.push(args)},gBrowser:{isTab:tab=>tab.isTab===true,isTabGroup:()=>false,addTrustedTab(url){creations++;return{setAttribute(){},linkedBrowser:{permanentKey:{}}};},getTabForBrowser:()=>({style:{removeProperty(){}}})},ChromeUtils:{defineESModuleGetters(target){Object.assign(target,{ZenShareError:ShareError,ZenShareClient:{createShare:async()=>{uploads++;return{link:'https://share.example'};},fetchSharePreview:async()=>({doc:preview})}});}}});
vm.runInContext(strip(readFileSync('src/zen/share/ZenShareManager.mjs','utf8')),context);
const manager=context.window.gZenShareManager;
manager._confirmShare=async()=>{confirms++;return true;};
manager._importFolder=()=>{creations++;};manager._importSpace=async()=>{creations++;};
for(const url of bad){
 const doc={shared:{type:'folder',name:'Injected',items:[{type:'tab',url:good[0]},{type:'tab',url}]}};
 const before=creations;
 await assert.rejects(manager._importDocument(doc),error=>error.code==='invalid-document');
 assert.equal(creations,before,'full document rejects before first mutation');
 assert.throws(()=>manager._importTab({url},'space'),error=>error.code==='invalid-document');
 assert.equal(creations,before,'tab boundary refuses trusted open');
 preview={shared:{type:'splitView',tabs:[{type:'tab',url:good[0]},{type:'tab',url}]}};
 await manager._openSharedSplitView({},{});
 assert.equal(creations,before,'eager split rejects before first tab');checks++;
}
const tab=(url,terminal=false)=>({isTab:true,label:'Example',image:null,getAttribute:()=>'',linkedBrowser:{currentURI:{spec:url}},hasAttribute:name=>terminal&&name==='zen-terminal-tab'});
assert.equal(manager._serializeTab(tab(good[0],true)),null,'terminal marker wins over stale HTTP address');checks++;
const web=manager._serializeTab(tab(good[0]));assert.equal(web.url,good[0]);assert.equal(web.label,'Example');checks++;
for(const shared of [{type:'space',name:'Only terminals',items:[]},{type:'folder',name:'Empty nested',items:[{type:'folder',name:'Empty',items:[]}]}]){
 await manager._createAndCopyLink(shared);assert.equal(uploads,0);assert.equal(confirms,0,'empty result does not ask to upload');checks++;
}
const folder={isZenFolder:true,label:'Mixed',allItems:[tab(good[0]),tab(good[1],true)]};
const serialized=manager._serializeFolder(folder);assert.equal(serialized.items.length,1);assert.equal(serialized.items[0].url,good[0]);checks++;
manager._importTab({url:good[0]},'space');assert.equal(creations,1,'genuine HTTP(S) still opens');checks++;
// Client rejects unsafe remote data even if schema validator accepts every URI.
let requests=0;
const clientContext=vm.createContext({...safety,URL,TextEncoder,AbortController,console:{error(){}},AppConstants:{MOZ_MOZILLA_API_KEY:'synthetic'},XPCOMUtils:{defineLazyPreferenceGetter(target,key){target[key]=key==='gBaseUrl'?'https://share.invalid':'';}},ChromeUtils:{defineESModuleGetters(target){Object.assign(target,{JsonSchema:{Validator:class{validate(){return{valid:true,errors:[]};}}},setTimeout,clearTimeout});}},fetch:async url=>{requests++;assert.equal(url,'resource:///modules/zen/share/share.schema.json','unsafe or empty create must never POST');return{json:async()=>({})};}});
vm.runInContext(strip(readFileSync('src/zen/share/ZenShareClient.sys.mjs','utf8'))+';globalThis.client=ZenShareClient;',clientContext);
for(const url of bad){assert.equal((await clientContext.client.validateDocument({shared:{type:'folder',items:[{type:'tab',url}]}})).valid,false);checks++;}
assert.equal(requests,0,'invalid addresses rejected before even schema resource fetch');
await assert.rejects(clientContext.client.createShare({shared:{type:'folder',name:'Empty',items:[]}}),error=>error.code==='empty');assert.equal(requests,1,'only schema resource read, no upload');checks++;
assert.equal((await clientContext.client.validateDocument(valid)).valid,true);checks++;
realConsole.log(`PASS ${checks} share-safety cases; actual production helpers/client/manager methods; no UI or network`);
