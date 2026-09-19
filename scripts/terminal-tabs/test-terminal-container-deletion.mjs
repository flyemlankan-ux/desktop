#!/usr/bin/env node
// Production shared cleanup observer, synthetic identities; optional real isolated tmux.
import assert from 'node:assert/strict';
import {mkdtempSync, rmSync, readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
const prefs=new Map(), recipes=new Map(), identities=new Set(), observers=new Map();
let profile='/synthetic/deletion-proof', saves=0, calls=[], sessions=new Set(), available=true, real=false, holdNew=null;
const command='/opt/homebrew/bin/tmux';
const notify=(subject,topic,data)=>{for(const observer of [...(observers.get(topic)||[])])observer.observe(subject,topic,data);};
globalThis.Ci={nsIFile:{}};
globalThis.Services={appinfo:{OS:'Darwin'},dirsvc:{get:()=>({path:profile})},prefs:{getStringPref:(key,fallback)=>prefs.get(key)??fallback,setStringPref:(key,value)=>prefs.set(key,value),savePrefFile:()=>saves++},obs:{addObserver(observer,topic){const set=observers.get(topic)||new Set();set.add(observer);observers.set(topic,set);},removeObserver(observer,topic){observers.get(topic)?.delete(observer);},notifyObservers:notify}};
const result=(stdout='',stderr='',code=0)=>{const pipe=text=>({async readString(){const chunk=text;text='';return chunk;}});return {stdout:pipe(stdout),stderr:pipe(stderr),wait:async()=>({exitCode:code}),kill(){}};};
globalThis.ChromeUtils={importESModule(name){
 if(name.endsWith("/ZenTerminalSessionManager.mjs"))return manager;
 if(name.includes('ContainerStore'))return {getTerminalContainerRecipe:id=>recipes.get(String(id))||null,removeTerminalContainerRecipe:id=>recipes.delete(String(id))};
 if(name.includes('ContextualIdentityService'))return {ContextualIdentityService:{getPublicIdentities:()=>[...identities].map(id=>({userContextId:Number(id)}))}};
 if(name.includes('Timer.sys'))return {setTimeout,clearTimeout};
 return {Subprocess:{async call(options){
  calls.push(options);
  if(options.command==='/bin/zsh')return result(available?command:'','',available?0:1);
  assert(!options.arguments.includes('kill-server'),'Production may never kill a server');
  if(real){const r=spawnSync(options.command,options.arguments,{encoding:'utf8',env:{...process.env,...options.environment}});return result(r.stdout||'',r.stderr||'',r.status??1);}
  const args=options.arguments.slice(4), op=args[0];
  if(op==='list-sessions')return result([...sessions].join('\n'));
  if(op==='new-session'){if(holdNew)await holdNew; sessions.add(args[args.indexOf('-s')+1]);return result();}
  if(op==='kill-session'){sessions.delete(args[args.indexOf('-t')+1].replace(/^=/,''));return result();}
  if(op==='set-option')return result();
  throw Error('Unexpected command '+op);
 }}};
}};
const manager=await import('../../src/zen/terminal/ZenTerminalSessionManager.mjs');
const settings={shell:'/bin/sh',home:'/tmp',startupCommand:'true'};
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(check){for(let i=0;i<100;i++){if(check())return;await sleep(10);}throw Error('Cleanup did not finish');}
function setup(){prefs.clear();recipes.clear();identities.clear();calls=[];sessions=new Set();saves=0;available=true;holdNew=null;for(const id of ['1','2']){identities.add(id);recipes.set(id,{kind:'terminal',recipe:{steps:[]}});}}
function register(id,owner){assert(manager.registerTerminalSession(id,{userContextId:owner}));sessions.add('zt_'+id);}
function remove(owner){identities.delete(owner);notify({wrappedJSObject:{userContextId:Number(owner)}},'contextual-identity-deleted');}
const tests=[];const test=(name,run)=>tests.push([name,run]);
test('One shared observer across repeat/window startup and session registration',async()=>{
 const secondWindow=await import('../../src/zen/terminal/ZenTerminalSessionManager.mjs?second-window');
 secondWindow.ensureTerminalContainerCleanupObserver();manager.ensureTerminalContainerCleanupObserver();await manager.retryPendingTerminalSessionDeletes();register('visible','1');
 assert.equal(observers.get('contextual-identity-deleted').size,1);
});
test('Service deletion synchronously marks visible/background only, keeps neighbor, duplicate safe',async()=>{
 register('visible','1');register('background','1');register('neighbor','2');
 const stopRequests=[];const observer={observe(_s,_t,id){stopRequests.push(id);}};Services.obs.addObserver(observer,manager.ZEN_TERMINAL_SESSION_DELETE_TOPIC);
 remove('1');
 assert.equal(recipes.has('1'),false);assert(recipes.has('2'));
 assert(manager.getTerminalSessionRecord('visible').pendingDelete);assert(manager.getTerminalSessionRecord('background').pendingDelete);assert(!manager.getTerminalSessionRecord('neighbor').pendingDelete);assert(saves>=2);
 remove('1'); // Extension notifications or existing Settings cleanup can overlap.
 await until(()=>!manager.getTerminalSessionRecord('visible')&&!manager.getTerminalSessionRecord('background'));
 assert.deepEqual([...sessions],['zt_neighbor']);assert(stopRequests.includes('visible')&&stopRequests.includes('background'));assert(!stopRequests.includes('neighbor'));
 assert.equal(calls.filter(c=>c.arguments.includes('kill-session')).length,2);
 Services.obs.removeObserver(observer,manager.ZEN_TERMINAL_SESSION_DELETE_TOPIC);
});
test('Unavailable tmux keeps durable deletion intent and next-launch retry completes',async()=>{
 register('unavailable','1');available=false;remove('1');await sleep(20);
 assert(manager.getTerminalSessionRecord('unavailable').pendingDelete);assert(sessions.has('zt_unavailable'));assert(saves>0);
 available=true;await manager.retryPendingTerminalSessionDeletes();assert.equal(manager.getTerminalSessionRecord('unavailable'),null);assert(!sessions.has('zt_unavailable'));
});
test('Owner deleted during settings lookup cannot create any new process',async()=>{
 manager.registerTerminalSession('not-started',{userContextId:'1'});
 await assert.rejects(manager.prepareTerminalTmuxSession(command,'not-started',()=>{remove('1');return settings;}),/closed|removed/);
 await until(()=>!manager.getTerminalSessionRecord('not-started'));
 assert.equal(calls.filter(c=>c.arguments.includes('new-session')).length,0);
});
test('Final service and saved-setup lookup refuses stale owner without relying on observer',async()=>{
 manager.registerTerminalSession('stale-owner',{userContextId:'1'});identities.delete('1');
 await assert.rejects(manager.prepareTerminalTmuxSession(command,'stale-owner',settings),/setup was removed/);
 identities.add('1');recipes.delete('1');
 await assert.rejects(manager.prepareTerminalTmuxSession(command,'stale-owner',settings),/setup was removed/);
 assert.equal(calls.filter(c=>c.arguments.includes('new-session')).length,0);
});
test('Deletion while tmux creation is in flight wins and leaves neighbor running',async()=>{
 register('neighbor','2');manager.registerTerminalSession('inflight',{userContextId:'1'});
 let release;holdNew=new Promise(resolve=>release=resolve);
 const secondWindow=await import('../../src/zen/terminal/ZenTerminalSessionManager.mjs?second-window');
 const preparing=secondWindow.prepareTerminalTmuxSession(command,'inflight',settings);
 await until(()=>calls.some(c=>c.arguments.includes('new-session')));remove('1');assert(manager.getTerminalSessionRecord('inflight').pendingDelete);release();
 await preparing;await until(()=>!manager.getTerminalSessionRecord('inflight'));
 assert.deepEqual([...sessions],['zt_neighbor']);
});
test('Page deletion observer stops its attached helper only and hides reconnect',()=>{
 const source=readFileSync(new URL('../../src/zen/terminal/ZenTerminalPage.mjs',import.meta.url),'utf8');
 const observer=source.slice(source.indexOf('const sessionDeleteObserver ='),source.indexOf('surface.addEventListener("mousedown"'));
 let stopped=0;const button={hidden:false};
 const context=vm.createContext({ZEN_TERMINAL_SESSION_DELETE_TOPIC:manager.ZEN_TERMINAL_SESSION_DELETE_TOPIC,activeTerminalSessionId:'mine',stopShell(){stopped++;},terminal:{writeln(){}},setStatus(){},document:{getElementById:()=>button},Services:{obs:{addObserver(){}}}});
 vm.runInContext(observer+';globalThis.observer=sessionDeleteObserver;',context);
 context.observer.observe(null,manager.ZEN_TERMINAL_SESSION_DELETE_TOPIC,'neighbor');assert.equal(stopped,0);
 context.observer.observe(null,manager.ZEN_TERMINAL_SESSION_DELETE_TOPIC,'mine');assert.equal(stopped,1);assert(button.hidden);
 assert(source.includes('if (stopping) {\n      createdProcess.kill(0);'),'Late helper must be killed after page deletion');
});
test('Real isolated tmux: service deletion kills exact jobs, retains neighbor',async()=>{
 assert.equal(spawnSync(command,['-V']).status,0,'Real tmux required for this proof');
 const directory=mkdtempSync(path.join(tmpdir(),'zen-delete-proof-'));profile=directory;real=true;
 try{
  for(const [id,owner] of [['real-visible','1'],['real-background','1'],['real-neighbor','2']]){
   manager.registerTerminalSession(id,{userContextId:owner});await manager.prepareTerminalTmuxSession(command,id,{...settings,home:directory});
  }
  remove('1');await until(()=>!manager.getTerminalSessionRecord('real-visible')&&!manager.getTerminalSessionRecord('real-background'));
  assert.equal(await manager.terminalTmuxSessionState(command,'real-neighbor'),'present');
  assert.equal(await manager.terminalTmuxSessionState(command,'real-visible'),'absent');
 }finally{
  // Test owns this new directory/socket; this is not production cleanup behavior.
  spawnSync(command,['-L',manager.getTerminalTmuxSocket(),'kill-server']);real=false;profile='/synthetic/deletion-proof';rmSync(directory,{recursive:true,force:true});
 }
});
for(const [name,run]of tests){setup();await run();console.log('PASS '+name);}
console.log(`${tests.length} container deletion checks passed, including real isolated tmux.`);
