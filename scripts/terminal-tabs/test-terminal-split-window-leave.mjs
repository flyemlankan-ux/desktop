#!/usr/bin/env node
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync('src/zen/drag-and-drop/ZenDragAndDrop.js','utf8');
const a=source.indexOf('    handle_windowDragLeave(event) {');
const method=source.slice(a,source.indexOf('\n    handle_drop(event)',a)).replaceAll('this.#','this.');
const url='chrome://browser/content/zen-terminal/terminal.xhtml';
function run(change=()=>{}) {
 const window={mozInnerScreenX:4,mozInnerScreenY:25};
 const doc={nodePrincipal:{isSystemPrincipal:true},documentURI:url+'?session=synthetic'};
 const browser={contentDocument:doc,currentURI:{spec:doc.documentURI}};
 const tab={documentGlobal:window,linkedBrowser:browser};
 const event={isTrusted:true,target:{id:'',ownerDocument:doc},relatedTarget:null,clientX:996,clientY:348,screenX:1236,screenY:381,dataTransfer:{mozTypesAt:()=>['application/x-moz-tabbrowser-tab'],mozGetDataAt:()=>tab}};
 const splitter={_canDrop:true,_draggingTab:tab,fakeBrowser:{isConnected:true}};
 const gBrowser={selectedBrowser:{},tabbox:{getBoundingClientRect:()=>({left:236,right:1272,top:8,bottom:705})}};
 const model={window,doc,browser,tab,event,splitter,gBrowser};change(model);
 const cancellations=[];const stopped=Error('native cancellation path');
 splitter.onBrowserDragEndToSplit=(actual,cancelled)=>{cancellations.push({actual,cancelled});throw stopped;};
 const handler=vm.runInNewContext('({'+method+'})',{window,gBrowser,gZenViewSplitter:splitter,isTab:value=>value===tab,TAB_DROP_TYPE:'application/x-moz-tabbrowser-tab'});
 Object.assign(handler,{isMovingTab:()=>true,_tabbrowserTabs:{_dndCanvas:{}},isOutOfWindow:false});
 try{handler.handle_windowDragLeave(event);}catch(error){if(error!==stopped)throw error;}
 return {cancellations,handler,model};
}
const accepted=run();assert.equal(accepted.cancellations.length,0);assert.equal(accepted.handler.isOutOfWindow,false);assert.equal(accepted.model.splitter._canDrop,true);assert.equal(accepted.model.splitter._draggingTab,accepted.model.tab);
for(const [label,change] of [
 ['left genuine exit',m=>m.event.screenX=0],
 ['right genuine exit',m=>m.event.screenX=1400],
 ['top genuine exit',m=>m.event.screenY=0],
 ['bottom genuine exit',m=>m.event.screenY=900],
 ['tabbox boundary',m=>m.event.screenX=240],
 ['no active preview',m=>m.splitter._canDrop=false],
 ['disconnected preview',m=>m.splitter.fakeBrowser.isConnected=false],
 ['wrong drag owner',m=>m.splitter._draggingTab={}],
 ['foreign browser window',m=>m.tab.documentGlobal={}],
 ['source still selected',m=>m.gBrowser.selectedBrowser=m.browser],
 ['untrusted event',m=>m.event.isTrusted=false],
 ['wrong document identity',m=>m.browser.contentDocument={}],
 ['non-system document',m=>m.doc.nodePrincipal.isSystemPrincipal=false],
 ['wrong document path',m=>m.doc.documentURI=url+'-lookalike'],
 ['wrong browser path',m=>m.browser.currentURI.spec='about:blank'],
 ['wrong native MIME',m=>m.event.dataTransfer.mozTypesAt=()=>['text/plain']],
 ['nonfinite coordinates',m=>m.event.screenX=NaN],
 ['ordinary web unchanged',m=>{m.doc.documentURI='https://example.invalid/';m.doc.nodePrincipal.isSystemPrincipal=false;}],
 ]) {
 const result=run(change);assert.equal(result.cancellations.length,1,label);assert.equal(result.cancellations[0].cancelled,true,label);assert.equal(result.handler.isOutOfWindow,true,label);
 }
assert.equal(run(m=>m.event.relatedTarget={}).cancellations.length,0,'existing internal-relatedTarget behavior');
assert.equal(run(m=>m.event.target.id='zen-split-view-fake-browser').cancellations.length,0,'existing preview target behavior');
console.log('PASS actual window-leave handler: exact hidden terminal preview transition stays active; 18 source/geometry negatives retain native forced cancellation; existing related-target/preview behavior unchanged');
