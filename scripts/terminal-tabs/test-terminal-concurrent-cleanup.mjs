#!/usr/bin/env node
// MPL-2.0. Actual tmux subprocesses on a unique synthetic profile/socket only.
import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
const tmux=['/opt/homebrew/bin/tmux','/usr/local/bin/tmux'].find(file=>spawnSync(file,['-V']).status===0);
assert.ok(tmux,'Installed tmux required, no silent skip');
const directory=mkdtempSync(path.join(tmpdir(),'zt-six-cleanup-'));
const prefs=new Map(), probes=[];
let manager;
globalThis.Ci={nsIFile:{}};
globalThis.Services={appinfo:{OS:'Darwin'},dirsvc:{get:()=>({path:directory})},prefs:{getStringPref:(k,f)=>prefs.get(k)??f,setStringPref:(k,v)=>prefs.set(k,v),savePrefFile(){}}};
globalThis.ChromeUtils={importESModule(name){
 if(name.endsWith('/ZenTerminalSessionManager.mjs'))return manager;
 if(name.endsWith('/Timer.sys.mjs'))return {setTimeout,clearTimeout};
 assert.ok(name.endsWith('/Subprocess.sys.mjs'));
 return {Subprocess:{async call(options){
  assert.equal(options.command,tmux);assert.equal(options.arguments[1],manager.getTerminalTmuxSocket());
  const child=spawn(tmux,options.arguments,{env:{...process.env,...options.environment}});
  let error='';child.stderr.on('data',chunk=>{error+=chunk;});
  const done=new Promise((resolve,reject)=>{child.on('error',reject);child.on('close',code=>{if(code!==0)probes.push({args:options.arguments.slice(4),code,error:error.trim()});resolve({exitCode:code});});});
  const pipe=stream=>{const it=stream[Symbol.asyncIterator]();return {async readString(){const item=await it.next();return item.done?'':item.value.toString('utf8');}};};
  return {stdout:pipe(child.stdout),stderr:pipe(child.stderr),wait:()=>done,kill:()=>child.kill('SIGKILL')};
 }}};
}};
manager=await import('../../src/zen/terminal/ZenTerminalSessionManager.mjs');
const direct=(...args)=>spawnSync(tmux,['-L',manager.getTerminalTmuxSocket(),'-f','/dev/null',...args],{encoding:'utf8'});
try{
 for(let round=0;round<10;round++){
  const ids=Array.from({length:6},(_,i)=>`round-${round}-job-${i}`);
  for(const id of ids){
   manager.registerTerminalSession(id);
   const created=direct('new-session','-d','-s',manager.getTerminalTmuxSessionName(id),'/bin/sleep','120');
   assert.equal(created.status,0,created.stderr);
  }
  const results=await Promise.all(ids.map(id=>manager.destroyTerminalSession(id,{tmuxCommand:tmux})));
  assert.deepEqual(results,[true,true,true,true,true,true],JSON.stringify({round,probes,records:manager.readTerminalSessionRecords()}));
  assert.deepEqual(Object.keys(manager.readTerminalSessionRecords()),[]);
  for(const id of ids)assert.equal(await manager.terminalTmuxSessionState(tmux,id),'absent');
 }
 console.log('PASS 10 rounds of six actual tmux jobs: all final-close records removed; unique synthetic profile');
 console.log('Nonzero tool result counts:',JSON.stringify(probes.reduce((counts, result)=>{const key=result.error.replace(/ on .*/, ' on <isolated socket>');counts[key]=(counts[key]||0)+1;return counts;},{})));
}finally{
 direct('kill-server');rmSync(directory,{recursive:true,force:true});
}
