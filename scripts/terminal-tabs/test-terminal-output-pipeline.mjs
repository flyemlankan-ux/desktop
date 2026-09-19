import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../../src/zen/terminal/ZenTerminalPage.mjs',import.meta.url),'utf8');
const code=source.slice(source.indexOf('async function readPipe('),source.indexOf('\nfunction validateTerminalPageContext()'));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function harness(chunks,{sync=false,writeThrow=false,readThrow=false}={}) {
 const callbacks=[],written=[],errors=[],listeners=new Map();let reads=0,queued=0,peak=0,peakCount=0;
 const terminal={write(chunk,callback){written.push(chunk);queued+=chunk.length*2;peak=Math.max(peak,queued);const done=()=>{queued-=chunk.length*2;callback();};if(sync)done();else callbacks.push(done);peakCount=Math.max(peakCount,callbacks.length);if(writeThrow)throw new Error('write broke');},writeln(s){errors.push(s);}};
 const context=vm.createContext({terminal,stopping:false,window:{addEventListener(type,fn){listeners.set(type,fn);},removeEventListener(type){listeners.delete(type);}}});
 vm.runInContext(code,context);
 const pipe={async readString(){reads++;if(readThrow&&reads===3)throw new Error('read broke');return chunks.shift()??'';}};
 context.pipe=pipe;
 const result=vm.runInContext('readPipe(pipe)',context);
 return {context,result,callbacks,written,errors,listeners,get reads(){return reads;},get peak(){return peak;},get peakCount(){return peakCount;},flush(){const batch=callbacks.splice(0);for(const fn of batch)fn();},cancel(){context.stopping=true;listeners.get('pagehide')?.();}};
}
// Hidden timer simulation: do not allow any callbacks until the pipeline fills.
const h=harness(Array.from({length:30},(_,i)=>String(i).padEnd(32768,'x')));
await tick();assert.equal(h.reads,3);assert(h.peak<=256*1024);assert.equal(h.callbacks.length,3);
for(let i=0;i<12;i++){h.flush();await tick();}
await h.result;assert.equal(h.written.length,30);assert.deepEqual(h.written.map(s=>parseInt(s,10)),Array.from({length:30},(_,i)=>i));assert.equal(h.listeners.size,0);
const tiny=harness(Array(140).fill('x'));await tick();assert.equal(tiny.reads,64);assert.equal(tiny.peakCount,64);for(let i=0;i<4;i++){tiny.flush();await tick();}await tiny.result;
// EOF must not finish while writes still await parser callbacks.
const eof=harness(['雪','\x1b[31m','🙂','\x1b[0m']);let ended=false;eof.result.then(()=>ended=true);await tick();assert(!ended);eof.flush();await eof.result;assert.equal(eof.written.join(''),'雪\x1b[31m🙂\x1b[0m');
const sync=harness(['a','b','c'],{sync:true});await sync.result;assert.equal(sync.errors.length,0);
const thrown=harness(['a'],{sync:true,writeThrow:true});await thrown.result;assert.match(thrown.errors[0],/write broke/);
const readError=harness(['a','b','c'],{readThrow:true});await tick();assert.equal(readError.errors.length,0);readError.flush();await readError.result;assert.match(readError.errors[0],/read broke/);
const unload=harness(Array(100).fill('x'));await tick();unload.cancel();await unload.result;assert.equal(unload.listeners.size,0);assert.equal(unload.errors.length,0);unload.flush();
// A blocked pipe read must not keep the reader alive on unload.
const blocked=harness([]);await blocked.result;
const listeners=new Map();const context=vm.createContext({terminal:{},stopping:false,pipe:{readString:()=>new Promise(()=>{})},window:{addEventListener:(t,f)=>listeners.set(t,f),removeEventListener:t=>listeners.delete(t)}});vm.runInContext(code,context);const waiting=vm.runInContext('readPipe(pipe)',context);await tick();listeners.get('pagehide')();await waiting;assert.equal(listeners.size,0);
const asynchronousThrow=harness(['a'],{writeThrow:true});await asynchronousThrow.result;assert.match(asynchronousThrow.errors[0],/write broke/);asynchronousThrow.flush();
const decoderPrefix=harness(['🙂'+'a'.repeat(32768)],{sync:true});await decoderPrefix.result;assert.equal(decoderPrefix.errors.length,0);assert.equal(decoderPrefix.written[0].length,32770);
const oversized=harness(['x'.repeat(32773)]);await oversized.result;assert.equal(oversized.written.length,0);assert.match(oversized.errors[0],/bounded pipe read size/);
// Independent stdout/stderr readers each enforce their ceiling, rather than
// claiming an interleaving order the subprocess transport never guaranteed.
const left=harness(Array(12).fill('l'.repeat(32768))),right=harness(Array(12).fill('r'.repeat(32768)));
await tick();assert(left.peak+right.peak<=512*1024);for(let i=0;i<5;i++){left.flush();right.flush();await tick();}await Promise.all([left.result,right.result]);
assert.doesNotMatch(code,/Promise\.race/);
const longOutput=harness(Array(10000).fill('x'),{sync:true});await longOutput.result;assert.equal(longOutput.reads,10001);assert.equal(longOutput.listeners.size,0);assert.equal(longOutput.errors.length,0);
console.log('PASS bounded output pipeline: payload/count ceilings, order, Unicode/ANSI, EOF drain, sync callbacks, callback+throw, read failure, unload and blocked-read cancellation. Native throughput not inferred.');
