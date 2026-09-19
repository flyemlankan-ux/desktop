#!/usr/bin/env node
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync('src/zen/split-view/ZenViewSplitter.mjs','utf8');
const start=source.indexOf('  onBrowserDragOverToSplit(event) {');
const handler=source.slice(start,source.indexOf('\n  _animateDropEdge(',start)).replaceAll('this.#','this.');
const pointStart=source.indexOf('  _calculateDropSide(event, panelsRect) {');
const pointMethod=source.slice(pointStart,source.indexOf('\n  // eslint-disable-next-line complexity',pointStart));
const terminalURL='chrome://browser/content/zen-terminal/terminal.xhtml';
function run(change=()=>{}) {
 const chromeWindow={mozInnerScreenX:4,mozInnerScreenY:30};
 const doc={nodePrincipal:{isSystemPrincipal:true},documentURI:terminalURL+'?sessionId=synthetic'};
 const dragged={documentGlobal:chromeWindow,hasAttribute:()=>false,getAttribute:()=> 'workspace'};
 const oldTab={hasAttribute:()=>false,getAttribute:()=> 'workspace'};
 const browser={contentDocument:doc,currentURI:{spec:doc.documentURI}};
 const gBrowser={selectedTab:dragged,selectedBrowser:browser,isTab:tab=>tab===dragged,tabContainer:{tabDragAndDrop:{clearSpaceSwitchTimer(){},finishMoveTogetherSelectedTabs(){},clearDragOverVisuals(){},originalDragImageArgs:[null,0,0]}},tabbox:{getBoundingClientRect:()=>({left:240,right:1280,top:80,bottom:880,width:1040,height:800})}};
 const dt={mozTypesAt:()=>['application/x-moz-tabbrowser-tab'],mozGetDataAt:()=>dragged};
 const event={isTrusted:true,target:{ownerDocument:doc},clientX:996,clientY:400,screenX:1236,screenY:430,dataTransfer:dt};
 const model={event,doc,browser,dragged,oldTab,chromeWindow,gBrowser};change(model);
 const splitter=vm.runInNewContext('({'+pointMethod+','+handler+'})',{
  window:chromeWindow,gBrowser,TAB_DROP_TYPE:'application/x-moz-tabbrowser-tab',requestAnimationFrame:()=>{},Services:{zen:{playHapticFeedback(){}}},
 });
 let preview=null;Object.assign(splitter,{_lastOpenedTab:oldTab,_data:[],MAX_TABS:4,tabBrowserPanel:{setAttribute(){}},_animateDropEdge:(side,_view,sourceTab,targetTab)=>{preview={side,sourceTab,targetTab};}});
 splitter.onBrowserDragOverToSplit(event);
 return {preview,model,splitter};
}
let result=run();assert.equal(result.preview.side,'right');assert.equal(result.preview.sourceTab,result.model.dragged);assert.equal(result.preview.targetTab,result.model.oldTab);assert.equal(result.model.event.clientX,996);
for(const [name,change] of [
 ['untrusted event',m=>m.event.isTrusted=false],
 ['other document',m=>m.browser.contentDocument={}],
 ['non-system document',m=>m.doc.nodePrincipal.isSystemPrincipal=false],
 ['wrong terminal pathname',m=>m.doc.documentURI=terminalURL+'-fake'],
 ['wrong browser URL',m=>m.browser.currentURI.spec='https://example.invalid/'],
 ['invalid screen coordinates',m=>m.event.screenX=NaN],
 ['wrong native MIME',m=>m.event.dataTransfer.mozTypesAt=()=>['text/plain']],
 ['foreign-window source',m=>m.dragged.documentGlobal={}],
 ['multiselected source',m=>m.dragged.multiselected=true],
 ['already split source',m=>m.dragged.splitView=true],
 ]) assert.equal(run(change).preview,null,name);
result=run(m=>{m.doc.documentURI='https://example.invalid/';m.doc.nodePrincipal.isSystemPrincipal=false;m.event.clientX=1232;});assert.equal(result.preview.side,'right');
result=run(m=>{m.event.screenX=764;});assert.equal(result.preview,null,'normalized center does not split');
result=run(m=>{m.event.screenX=300;m.event.screenY=430;});assert.equal(result.preview.side,'left');
console.log('PASS actual splitter handler: exact trusted terminal coordinates normalized; 10 identity/source negatives; ordinary web unchanged; center rejected and both edges use chrome coordinates');
