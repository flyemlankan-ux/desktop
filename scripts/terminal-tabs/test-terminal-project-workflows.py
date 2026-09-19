#!/usr/bin/env python3
"""Mixed project integration on an actual app, always disposable synthetic data.
Native methods unless explicitly labelled pointer input. Optional pointer drag
uses real W3C input; unsupported/broken input fails rather than faking a pass.
"""
import argparse, ctypes as C, importlib.util, json, os, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.keys import Keys

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='packaged')
parser.add_argument('--split-web-source-control', action='store_true', help='Diagnostic only: drag the ordinary web tab toward the previous terminal view')
parser.add_argument('--split-web-target-control', action='store_true', help='Diagnostic only: select web after native dragstart to compare content event paths')
parser.add_argument('--gecko-native-drag-to-split', action='store_true', help='Also prove actual tab-to-content-edge native split; requires Gecko pointer reorder mode')
parser.add_argument('--gecko-native-pointer-drag', action='store_true', help='Experimental process-local Gecko native down/move/up; moves system cursor but never posts global input')
parser.add_argument('--annotate-native-window', action='store_true', help='Opt-in CG window annotations; requires --native-pointer-drag')
parser.add_argument('--native-pointer-drag', action='store_true', help='Actual owned-PID macOS CGEvent drag; no W3C fallback')
parser.add_argument('--pointer-drag', action='store_true', help='Attempt real pointer reorder; failure is NOT replaced by a native-method pass')
args=parser.parse_args()
if args.split_web_source_control and not args.gecko_native_drag_to_split:parser.error('--split-web-source-control requires --gecko-native-drag-to-split')
if args.split_web_source_control and args.split_web_target_control:parser.error('Choose one split control')
if args.split_web_target_control and not args.gecko_native_drag_to_split:parser.error('--split-web-target-control requires --gecko-native-drag-to-split')
if args.gecko_native_drag_to_split and not args.gecko_native_pointer_drag:parser.error('--gecko-native-drag-to-split requires --gecko-native-pointer-drag')
if args.annotate_native_window and not args.native_pointer_drag:parser.error('--annotate-native-window requires --native-pointer-drag')
if sum([args.pointer_drag,args.native_pointer_drag,args.gecko_native_pointer_drag])>1:parser.error('Choose one pointer mechanism explicitly')
if not args.label.replace('-', '').replace('_', '').isalnum():parser.error('label must contain letters, digits, hyphens or underscores')
root=Path(__file__).resolve().parents[2]
run=root/'.terminal-test'/('mac-'+uuid.uuid4().hex[:8]);run.mkdir(parents=True)
proof=root/'docs/proof/2026-09-19';proof.mkdir(parents=True,exist_ok=True)
home=run/'home';home.mkdir();profile=run/'profile';profile.mkdir()
(home/'.zshenv').write_text('export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n')
with net_socket.socket() as listener:
 listener.bind(('127.0.0.1',0));marionette_port=listener.getsockname()[1]
prefs={'marionette.port':marionette_port,'browser.shell.checkDefaultBrowser':False,'browser.startup.page':3,'zen.welcome-screen.seen':True,'app.update.disabledForTesting':True,'app.update.auto':False,'app.update.enabled':False,'browser.startup.homepage':'about:blank','browser.aboutwelcome.enabled':False,'browser.sessionstore.resume_from_crash':True,'privacy.userContext.enabled':True,'privacy.userContext.ui.enabled':True}
(profile/'user.js').write_text('\n'.join('user_pref(%s, %s);'%(json.dumps(k),json.dumps(v)) for k,v in prefs.items()))
env=dict(os.environ,MOZ_APP_DATA=str(home/'app-data'),MOZ_LOCAL_APP_DATA=str(home/'local-app-data'),HOME=str(home),ZDOTDIR=str(home),SHELL='/bin/zsh',PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',MOZ_NO_REMOTE='1')
# Restart-only environment values take priority over -profile in Firefox.
# Never inherit a real browser's selected profile into this synthetic test.
for key in list(env):
 if key.startswith(('XRE_PROFILE_', 'SELECTABLE_PROFILE_RESET_')) or key in {'XRE_RESTARTED_BY_PROFILE_MANAGER','MOZ_RESET_PROFILE_RESTART','MOZ_LEGACY_PROFILES'}:
  env.pop(key,None)
exe=args.app.resolve()/'Contents/MacOS/zen-terminal'
log=open(run/'gecko.log','w');process=None;m=None;results=[];test_sessions=[];socket=None
def record(name,detail=True):
 results.append({'test':name,'result':'pass','detail':detail});print('PASS',name,detail,flush=True)
def wait(check,label,timeout=25):
 end=time.monotonic()+timeout;error=None
 while time.monotonic()<end:
  try:
   result=check()
   if result:return result
  except Exception as e:error=e
  time.sleep(.1)
 raise AssertionError('Timed out: '+label+'; '+str(error))
def start():
 global process,m
 process=subprocess.Popen([str(exe),'-no-remote','-marionette','--remote-allow-system-access','-profile',str(profile)],env=env,stdout=log,stderr=log)
 m=Marionette(host='127.0.0.1',port=marionette_port,socket_timeout=30,startup_timeout=30)
 m.raise_for_port(timeout=30);m.start_session();m.set_context('chrome')
 assert js('return Services.appinfo.processID;')==process.pid
 assert Path(js('return Services.dirsvc.get("ProfD",Ci.nsIFile).path;')).resolve()==profile.resolve()
 wait(lambda:js('return Boolean(window.gZenTerminalTabs && gBrowserInit.delayedStartupFinished);'),'browser ready')
def js(script,args=None):return m.execute_script(script,script_args=args or [])
def terminal_status():return js('return gBrowser.selectedBrowser.contentDocument?.getElementById("zen-terminal-status-text")?.textContent;')
def tmux(*args):return subprocess.run(['/opt/homebrew/bin/tmux','-L',socket,*args],capture_output=True,text=True,timeout=5)
def screen(name):
 m.set_context('chrome');(proof/(args.label+'-'+name+'.png')).write_bytes(m.screenshot(format='binary'))
def async_js(script,args=None):
 return m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{'+script+'})().then(value=>done({value}),error=>done({error:String(error)}));',script_args=args or [])
def pane(sid,format='#{pane_pid}'):
 result=tmux('display-message','-p','-t','zt_'+sid,format)
 assert result.returncode==0,result.stderr
 return result.stdout.strip()
def same_jobs():
 assert [pane(sid) for sid in test_sessions]==job_pids
 assert marker.read_text().splitlines()==['launch','launch']

def native_drag(source, target):
 # AX window geometry and DOM geometry use screen points on macOS, not Retina
 # device pixels. Require agreement instead of guessing an offset or scale.
 spec=importlib.util.spec_from_file_location('owned_dialogs',Path(__file__).with_name('macos-test-dialogs.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 ax=module.OwnedAppDialogs(process.pid)
 try:
  ax.activate();ax.raise_window()
  assert js('return Services.appinfo.processID;')==process.pid
  focused=ax.attr(ax.root,'AXFocusedWindow');assert focused,'No owned focused window'
  ax.owner(focused)
  class Pair(C.Structure):_fields_=[('a',C.c_double),('b',C.c_double)]
  decode=ax.ax.AXValueGetValue;decode.argtypes=[C.c_void_p,C.c_int,C.c_void_p];decode.restype=C.c_bool
  position=Pair();size=Pair()
  assert decode(ax.attr(focused,'AXPosition'),1,C.byref(position)), 'No AX screen position'
  assert decode(ax.attr(focused,'AXSize'),2,C.byref(size)), 'No AX window size'
  geometry=js('return {x:window.screenX,y:window.screenY,width:window.outerWidth,height:window.outerHeight,innerX:window.mozInnerScreenX,innerY:window.mozInnerScreenY,ratio:window.devicePixelRatio};')
  assert all(abs(a-b)<=2 for a,b in zip([position.a,position.b,size.a,size.b],[geometry['x'],geometry['y'],geometry['width'],geometry['height']])), {'AX':[position.a,position.b,size.a,size.b],'DOM':geometry}
  start=(geometry['innerX']+source['x'],geometry['innerY']+source['y'])
  end=(geometry['innerX']+target['x'],geometry['innerY']+target['y']-8)
  bounds=(position.a,position.b,size.a,size.b)
  print('NATIVE POINTER GEOMETRY',{'start':start,'end':end,'bounds':bounds,'DOM':geometry},flush=True)
  # Native helper checks ownership before every mouse event and always releases.
  window_id=ax.drag(start,end,bounds,duration=1.2,annotate_window=args.annotate_native_window)
  geometry["verifiedCGWindowID"]=window_id
  return {'start':start,'end':end,'bounds':bounds,'DOM':geometry}
 finally:ax.close()

def gecko_native_drag(source,target,split=False):
 # Native AppKit drag tracking requires an active owned application, not just
 # DOM window.focus(). Never activate or send input to any other process.
 spec=importlib.util.spec_from_file_location('owned_dialogs',Path(__file__).with_name('macos-test-dialogs.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 ax=module.OwnedAppDialogs(process.pid)
 try:
  class Pair(C.Structure):_fields_=[('a',C.c_double),('b',C.c_double)]
  decode=ax.ax.AXValueGetValue;decode.argtypes=[C.c_void_p,C.c_int,C.c_void_p];decode.restype=C.c_bool
  def verified_front_window():
   if ax.attr(ax.root,'AXFrontmost') is not True:return False
   focused=ax.attr(ax.root,'AXFocusedWindow')
   if not focused:return False
   ax.owner(focused)
   position=Pair();size=Pair()
   if not decode(ax.attr(focused,'AXPosition'),1,C.byref(position)) or not decode(ax.attr(focused,'AXSize'),2,C.byref(size)):return False
   actual=js('return [Services.appinfo.processID,screenX,screenY,outerWidth,outerHeight];')
   return actual[0]==process.pid and all(abs(a-b)<=2 for a,b in zip([position.a,position.b,size.a,size.b],actual[1:]))
  if not verified_front_window():
   try:ax.activate();ax.raise_window()
   except module.AccessibilityError as error:
    if "-25206" not in str(error):raise
    # Unsupported Raise is acceptable ONLY if the exact desired state already
    # holds. Never infer permission success or activate another application.
    if not verified_front_window():raise
  assert verified_front_window(),'Owned app is not frontmost with the exact focused window'
 finally:ax.close()
 # Activation can change compact-sidebar geometry. Recompute after it, not
 # from the stale pre-activation rectangles supplied by the caller.
 if split:
  source,target=js('const t=arguments[0]?projectWeb:projectTerms[0];t.scrollIntoView({block:"nearest"});const r=t.getBoundingClientRect(),box=gBrowser.tabbox.getBoundingClientRect();const a={x:r.x+r.width/2,y:r.y+r.height/2,width:r.width,height:r.height};a.hit=document.elementFromPoint(a.x,a.y)?.closest("tab")===t;const b={x:box.right-Math.min(40,box.width/8),y:box.y+box.height/2,width:box.width,height:box.height};b.hit=gBrowser.tabbox.contains(document.elementFromPoint(b.x,b.y));return [a,b];',[args.split_web_source_control])
 else:
  source,target=js('return [projectTerms[1],projectWeb].map(t=>{const r=t.getBoundingClientRect();const x=r.x+r.width/2,y=r.y+r.height/2;return {x,y,width:r.width,height:r.height,hit:document.elementFromPoint(x,y)?.closest("tab")===t};});')
 assert all(r['width']>0 and r['height']>16 and r['hit'] for r in [source,target]),[source,target]
 result=async_js("""
 const pid=arguments[0],source=arguments[1],target=arguments[2],split=arguments[3],webControl=arguments[4];
 if(Services.appinfo.processID!==pid)throw new Error('Wrong owned browser process');
 const ownedDocument=window.document,element=split?gBrowser.tabContainer:projectTerms[1];
 if(element.ownerDocument!==ownedDocument || !element.isConnected)throw new Error('Not an owned chrome tab');
 const u=window.windowUtils,ratio=window.devicePixelRatio;
 if(!Number.isFinite(ratio)||ratio<=0)throw new Error('Invalid device-pixel scale');
 const origin={x:window.mozInnerScreenX,y:window.mozInnerScreenY};
 const outer={x:window.screenX,y:window.screenY,width:window.outerWidth,height:window.outerHeight};
 const start={x:origin.x+source.x,y:origin.y+source.y},end={x:origin.x+target.x,y:origin.y+target.y-(split?0:8)};
 for(const p of [start,end])if(p.x<outer.x||p.y<outer.y||p.x>outer.x+outer.width||p.y>outer.y+outer.height)throw new Error('Point outside owned window');
 const sent=[];window.projectNativeDispatch=sent;
 async function send(message,point){
   if(Services.appinfo.processID!==pid || element.ownerDocument!==ownedDocument || !element.isConnected)throw new Error('Owned widget changed');
   if(message!==u.NATIVE_MOUSE_MESSAGE_BUTTON_UP && (window.screenX!==outer.x || window.screenY!==outer.y || window.outerWidth!==outer.width || window.outerHeight!==outer.height || window.devicePixelRatio!==ratio))throw new Error('Owned geometry changed');
   const dispatch={message,x:point.x,y:point.y,requestedAt:performance.now()};sent.push(dispatch);
   await new Promise((resolve,reject)=>{
     const timeout=window.setTimeout(()=>reject(new Error('Native mouse dispatch callback timed out')),3000);
     try{u.sendNativeMouseEvent(Math.round(point.x*ratio),Math.round(point.y*ratio),message,0,0,element,{onCompleteDispatch(){window.clearTimeout(timeout);resolve();}});}
     catch(error){window.clearTimeout(timeout);reject(error);}
   });
   dispatch.completedAt=performance.now();
 }
 window.focus();
 const lifecycle=[];
 const splitState=()=>{
   const splitter=gZenViewSplitter,fake=splitter.fakeBrowser;
   const rect=fake?.getBoundingClientRect();
   return {canDrop:!!splitter._canDrop,hasAnimated:!!splitter._hasAnimated,selected:gBrowser.selectedTab?.id,last:splitter._lastOpenedTab?.id,dragging:splitter._draggingTab?.id,fake:fake?.id,side:fake?.getAttribute('side'),fakeConnected:fake?.isConnected,fakeRect:rect?{x:rect.x,y:rect.y,width:rect.width,height:rect.height}:null};
 };
 const lifecycleTypes=['dragenter','dragleave','dragover','drop','dragend','TabSelect'];
 const traceLifecycle=event=>{
   if(!split||lifecycle.length>=128)return;
   const entry={type:event.type,time:performance.now(),trusted:event.isTrusted,previousTab:event.detail?.previousTab?.id,target:event.target.id||event.target.localName,document:event.target.ownerDocument?.documentURI,related:event.relatedTarget?.id||event.relatedTarget?.localName,path:event.composedPath().map(n=>n.id||n.localName||n.constructor.name),client:{x:event.clientX,y:event.clientY},screen:{x:event.screenX,y:event.screenY},chrome:{x:event.screenX-window.mozInnerScreenX,y:event.screenY-window.mozInnerScreenY},effect:event.dataTransfer?.dropEffect,cancelled:event.dataTransfer?.mozUserCancelled,before:splitState()};
   lifecycle.push(entry);
   // Observe the real production listeners; never call or replace them.
   setTimeout(()=>{entry.after=splitState();entry.afterTime=performance.now();entry.afterEffect=event.dataTransfer?.dropEffect;},0);
 };
 if(split)for(const type of lifecycleTypes)window.addEventListener(type,traceLifecycle,true);
 const traceMilestone=name=>{if(split&&lifecycle.length<128)lifecycle.push({milestone:name,time:performance.now(),state:splitState()});};
 let acceptedOver=null;const observedOvers=[];let tabboxHits=0;const atTabbox=()=>tabboxHits++;gBrowser.tabbox.addEventListener("dragover",atTabbox,true);
 const onOver=event=>{
   const tab=event.target.closest?.('tab');const nativePath=event.composedPath();const crossedTabbox=nativePath.includes(gBrowser.tabbox);const eventPath=nativePath.map(n=>n.id||n.localName||n.constructor.name);
   const types=event.dataTransfer?[...event.dataTransfer.types]:[];
   // Capture survives native propagation stops; inspect acceptance after the
   // production target handlers, without altering the event or its data.
   (split?callback=>setTimeout(callback,0):queueMicrotask)(()=>{
     const fake=document.getElementById('zen-split-view-fake-browser');
     if(split&&observedOvers.length<64)observedOvers.push({fake:fake?.id,side:fake?.getAttribute('side'),target:event.target.localName,document:event.target.ownerDocument?.documentURI,path:eventPath,embedder:event.target.ownerGlobal?.browsingContext?.embedderElement?.id,tabboxHits,inside:gBrowser.tabbox.contains(event.target),effect:event.dataTransfer?.dropEffect,clientX:event.clientX,clientY:event.clientY,chromeOrigin:{x:mozInnerScreenX,y:mozInnerScreenY},x:event.screenX,y:event.screenY,canDrop:gZenViewSplitter._canDrop,last:gZenViewSplitter._lastOpenedTab?.id});
     const correctTarget=split ? !!fake&&fake.getAttribute('side')==='right'&&crossedTabbox&&tabboxHits>0 : tab===projectWeb;
     const correctEffect=split ? event.dataTransfer.dropEffect==='none' : event.dataTransfer.dropEffect==='move';
     if(event.isTrusted && correctTarget && types.includes('application/x-moz-tabbrowser-tab') && correctEffect && Math.abs(event.screenX-end.x)<=2 && Math.abs(event.screenY-end.y)<=2){
       acceptedOver={trusted:true,target:split?fake.id:tab.id,types,dropEffect:event.dataTransfer.dropEffect,screenX:event.screenX,screenY:event.screenY};
     }
   });
 };
 window.addEventListener('dragover',onOver,true);
 try{
   await send(u.NATIVE_MOUSE_MESSAGE_MOVE,start);
   await send(u.NATIVE_MOUSE_MESSAGE_BUTTON_DOWN,start);
   if(split){
     // Start the drag inside the original chrome tab before crossing into its
     // content browser widget. A single leap can miss tab drag initiation.
     const threshold={x:start.x+Math.min(20,source.width/4),y:start.y};
     const started=performance.now()+3000;
     while(!projectDragEvents.some(event=>event.type==='dragstart'&&event.trusted) && performance.now()<started){
       await send(u.NATIVE_MOUSE_MESSAGE_MOVE,threshold);
       await new Promise(resolve=>setTimeout(resolve,50));
     }
     if(!projectDragEvents.some(event=>event.type==='dragstart'&&event.trusted))throw new Error('No trusted tab dragstart before entering content');
     const trackingDeadline=performance.now()+3000;
     while(!projectDragEvents.some(event=>event.type==='dragover'&&event.trusted)&&performance.now()<trackingDeadline)await new Promise(resolve=>setTimeout(resolve,25));
     if(!projectDragEvents.some(event=>event.type==='dragover'&&event.trusted))throw new Error('Native AppKit drag tracking did not start');
     if(webControl)gBrowser.selectedTab=projectWeb;
     await send(u.NATIVE_MOUSE_MESSAGE_MOVE,end);
   }
   const deadline=performance.now()+3000;
   while(!acceptedOver && performance.now()<deadline){
     if(split&&projectDragEvents.some(event=>event.type==='dragend'))throw new Error('Native drag ended before explicit mouse release');
     if(!split)await send(u.NATIVE_MOUSE_MESSAGE_MOVE,end);
     await new Promise(resolve=>window.setTimeout(resolve,split?25:50));
   }
   // Actual drag readiness, not a fixed number of moves or an assumed delay.
   if(!acceptedOver)throw new Error('No trusted accepted tab dragover at destination before bounded release '+JSON.stringify(observedOvers));
   traceMilestone("before-preview-animation-wait");
   if(split)await new Promise((resolve,reject)=>{
     const timeout=setTimeout(()=>reject(new Error('Native split preview animation timed out')),3000);
     Promise.resolve(gZenViewSplitter._finishAllAnimatingPromise).then(()=>{clearTimeout(timeout);resolve();},error=>{clearTimeout(timeout);reject(error);});
   });
   traceMilestone("after-preview-animation-wait");
   if(split&&projectDragEvents.some(event=>event.type==='dragend'))throw new Error('Native drag ended before explicit mouse release after preview');
 }finally{
   try{traceMilestone("before-button-up");await send(u.NATIVE_MOUSE_MESSAGE_BUTTON_UP,end);await new Promise(resolve=>setTimeout(resolve,0));traceMilestone("after-button-up");}
   finally{window.removeEventListener('dragover',onOver,true);gBrowser.tabbox.removeEventListener('dragover',atTabbox,true);if(split)for(const type of lifecycleTypes)window.removeEventListener(type,traceLifecycle,true);window.projectSplitDiagnostic={observedOvers,tabboxHits,webControl,lifecycle};}
 }
 return {start:[start.x,start.y],end:[end.x,end.y],outer,ratio,sent,acceptedOver,observedOvers,tabboxHits,webControl,lifecycle,scope:'own NSApp NSEvent down/move/up; shared cursor moved'};
 """,[process.pid,source,target,split,args.split_web_target_control])
 assert 'error' not in result,result
 return result['value']

failure=None
try:
 start()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 assert socket and socket.startswith('zen-terminal-p')
 record('owned process and synthetic profile/data root confirmed')
 import shlex
 marker=run/'recipe-launches.txt'
 js('const service=ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService;const store=ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs");window.projectIdentity=service.create("Mixed project proof","briefcase","purple");store.setTerminalContainerRecipe(projectIdentity.userContextId,{recipe:{steps:[arguments[0]]}});window.projectTerms=[];', ['printf "launch\\n" >> '+shlex.quote(str(marker))])
 for i in range(2):
  sid=js('const tab=gZenTerminalTabs.openTerminalContainerTab(projectIdentity.userContextId);projectTerms.push(tab);return tab.getAttribute("zen-terminal-session-id");')
  test_sessions.append(sid)
  wait(lambda:tmux('has-session','-t','=zt_'+sid).returncode==0,'owned terminal job')
  wait(lambda:terminal_status() and 'ready' in terminal_status(),'terminal ready')
 wait(lambda:marker.exists() and len(marker.read_text().splitlines())==2,'exactly two recipe launches')
 job_pids=[pane(sid) for sid in test_sessions]
 assert len(set(job_pids))==2 and len(set(test_sessions))==2
 record('same saved setup launches two independent shells exactly once')
 js('window.projectWeb=gBrowser.addTrustedTab("about:blank");window.projectFolder=gZenFolders.createFolder([projectWeb,...projectTerms],{label:"Mixed project proof"});gBrowser.selectedTab=projectWeb;gBrowser.selectedTab=projectTerms[0];')
 time.sleep(1.7)
 assert js('return [projectWeb,...projectTerms].every(t=>t.group===projectFolder && t.pinned);')
 same_jobs();record('mixed folder retains web and both terminals after selection')
 js('projectFolder.collapsed=true;projectFolder.collapsed=false;')
 assert js('return [projectWeb,...projectTerms].every(t=>t.group===projectFolder);')
 same_jobs();record('native collapse/expand retains members and jobs')
 if args.pointer_drag or args.native_pointer_drag or args.gecko_native_pointer_drag:
  js('window.projectDragEvents=[];for(const type of ["mousedown","dragstart","dragover","drop","dragend"]){window.addEventListener(type,e=>{if(e.type!=="dragover" || projectDragEvents.filter(x=>x.type==="dragover").length<10)projectDragEvents.push({type:e.type,trusted:e.isTrusted,button:e.button,buttons:e.buttons,target:e.target.closest?.("tab")?.id||e.target.localName,x:e.clientX,y:e.clientY,screenX:e.screenX,screenY:e.screenY,dropEffect:e.dataTransfer?.dropEffect,cancelled:e.dataTransfer?.mozUserCancelled,types:e.dataTransfer?[...e.dataTransfer.types]:[]});},true);}window.focus();')
  time.sleep(.6)
  # Both pointer mechanisms hit actual browser chrome. Never inject drag events or
  # silently substitute DOM moves when real pointer dragging fails.
  rects=js('const tabs=[projectTerms[1],projectWeb];tabs.forEach(t=>t.scrollIntoView({block:"nearest"}));return tabs.map(t=>{const r=t.getBoundingClientRect();const x=r.x+r.width/2,y=r.y+r.height/2;return {x,y,top:r.y+2,width:r.width,height:r.height,hit:document.elementFromPoint(x,y)?.closest("tab")===t};});')
  assert all(r["width"]>0 and r["height"]>16 and r["hit"] for r in rects),rects
  source,target=rects
  print('POINTER RECTS',rects,flush=True)
  native_geometry=None
  if args.gecko_native_pointer_drag:
   native_geometry=gecko_native_drag(source,target)
  elif args.native_pointer_drag:
   native_geometry=native_drag(source,target)
  else:
   m.actions.sequence('pointer','project-drag',{'pointerType':'mouse'}).pointer_move(int(source['x']),int(source['y'])).pointer_down().pause(250).pointer_move(int(target['x']),int(target['y']-8),duration=800).pause(1000).pointer_up().perform()
   m.actions.release()
  wait(lambda:js('return projectTerms[1].group===projectFolder && projectFolder.tabs.indexOf(projectTerms[1])<projectFolder.tabs.indexOf(projectWeb);'),'actual pointer reorder')
  wait(lambda:js('return projectDragEvents.some(e=>e.type==="dragend" && e.trusted);'),'native drag session finishes')
  events=js('return projectDragEvents;')
  assert all(any(event['type']==kind and event['trusted'] for event in events) for kind in ['dragstart','drop','dragend']), events
  # Capture sees dragstart before the native tab handler fills dataTransfer.
  # The actual trusted drop must carry the native tab payload.
  assert any(event['type']=='drop' and event['trusted'] and 'application/x-moz-tabbrowser-tab' in event['types'] for event in events),events
  if native_geometry:
   down=next(event for event in events if event['type']=='mousedown')
   assert abs(down['screenX']-native_geometry['start'][0])<=2 and abs(down['screenY']-native_geometry['start'][1])<=2, {'event':down,'geometry':native_geometry}
  same_jobs();record('actual pointer drag reordered terminal before web inside folder',{'mechanism':'Gecko own NSApp NSEvent' if args.gecko_native_pointer_drag else 'owned-PID CGEvent' if native_geometry else 'W3C','events':events,'geometry':native_geometry})
 else:
  results.append({'test':'actual pointer drag/drop','result':'not_run','detail':'Use --pointer-drag, --native-pointer-drag or --gecko-native-pointer-drag; native methods do not establish pointer acceptance'})
 # Use Zen's actual move helper, not direct DOM insertion.
 js('const from=gBrowser.tabs.indexOf(projectTerms[1]),to=gBrowser.tabs.indexOf(projectWeb);gBrowser.moveTabTo(projectTerms[1],{tabIndex:to-(from<to?1:0)});')
 assert js('return projectTerms[1].group===projectFolder && projectFolder.tabs.indexOf(projectTerms[1])<projectFolder.tabs.indexOf(projectWeb);')
 same_jobs();record('native tab reorder retains folder and live jobs')
 created=async_js('window.projectSpace=await gZenWorkspaces.createAndSaveWorkspace("Mixed proof workspace");return projectSpace?.uuid;')
 assert created.get('value'),created
 moved=async_js('gZenFolders.changeFolderToSpace(projectFolder,projectSpace.uuid);await gZenWorkspaces.changeWorkspaceWithID(projectSpace.uuid);return projectSpace.uuid;')
 assert moved.get('value'),moved
 wait(lambda:js('return [projectWeb,...projectTerms].every(t=>t.group===projectFolder && t.getAttribute("zen-workspace-id")===projectSpace.uuid);'),'whole mixed folder moves to workspace')
 js('gBrowser.selectedTab=projectTerms[0];')
 same_jobs();record('whole mixed folder moves to new workspace without restarting jobs')
 if args.gecko_native_drag_to_split:
  js('if(!Services.prefs.getBoolPref("zen.splitView.enable-tab-drop"))throw new Error("Native tab drop split preference disabled");projectFolder.collapsed=false;gBrowser.selectedTab=projectWeb;window.projectDragEvents=[];',[ ])
  if args.split_web_source_control:js('gBrowser.selectedTab=projectTerms[0];')
  split_geometry=gecko_native_drag(None,None,split=True)
  wait(lambda:js('return projectWeb.splitView && projectTerms[0].splitView && projectWeb.group===projectTerms[0].group;'),'actual native edge drag creates mixed split')
  wait(lambda:js('return projectDragEvents.some(e=>e.type==="dragend"&&e.trusted);'),'native split drag ends')
  split_events=js('return projectDragEvents;')
  assert all(any(e['type']==kind and e['trusted'] for e in split_events) for kind in ['dragstart','dragover','dragend']),split_events
  assert any(e['type']=='dragover' and e['trusted'] and 'application/x-moz-tabbrowser-tab' in e['types'] for e in split_events),split_events
  assert any(e['type']=='dragend' and e['trusted'] and e['dropEffect']=='none' and not e.get('cancelled') for e in split_events),split_events
  same_jobs();record('controlled web-target native edge drag creates mixed split' if args.split_web_target_control else 'actual native content-edge drag creates mixed web/terminal split',{'events':split_events,'geometry':split_geometry,'scope':'Zen native uncancelled dragend commit, not a DOM drop handler'})
 else:
  js('gZenViewSplitter.splitTabs([projectWeb,projectTerms[0]],"grid",1);')
 wait(lambda:js('return projectWeb.splitView && projectTerms[0].splitView && projectWeb.group===projectTerms[0].group;'),'mixed split view')
 old_size=pane(test_sessions[0],'#{pane_width}x#{pane_height}')
 m.set_window_rect(width=1100,height=700)
 m.set_window_rect(width=900,height=600)
 wait(lambda:pane(test_sessions[0],'#{pane_width}x#{pane_height}')!=old_size,'split terminal resize')
 same_jobs();record('mixed split and window resize retain shell and resize terminal')
 js('gZenViewSplitter.removeTabFromGroup(projectTerms[0],undefined,{forUnsplit:true});gBrowser.selectedTab=projectTerms[0];')
 wait(lambda:js('return !projectTerms[0].splitView && !projectWeb.splitView;'),'unsplit')
 same_jobs();record('unsplit retains live jobs and recipe counts')
 js('window.projectOther=OpenBrowserWindow();')
 wait(lambda:js('return projectOther?.gBrowserInit?.delayedStartupFinished && !!projectOther.gZenWorkspaces;'),'second owned browser window')
 sync_ready=async_js('await projectOther.gZenWorkspaces.promiseInitialized;return {original:gZenWorkspaces.currentWindowIsSyncing,other:projectOther.gZenWorkspaces.currentWindowIsSyncing};')
 assert sync_ready.get('value',{}).get('original') and sync_ready.get('value',{}).get('other'),sync_ready
 wait(lambda:js('return projectTerms.every(t=>Boolean(gZenWindowSync.getItemFromWindow(projectOther,t.id)));'),'mirrored terminal tabs')
 js('const mirrored=gZenWindowSync.getItemFromWindow(projectOther,projectTerms[0].id);projectOther.gBrowser.selectedTab=mirrored;')
 same_jobs();record('second native window mirrors both terminal tabs without rerunning recipes')
 js('projectOther.close();')
 wait(lambda:js('return projectOther.closed;'),'second window closes')
 same_jobs();record('closing one mirrored window preserves original live jobs')
 # Native synchronized tab deletion should remove the final tab viewers.
 js('gBrowser.removeTab(projectTerms[1],{animate:false});')
 wait(lambda:tmux('has-session','-t','=zt_'+test_sessions[1]).returncode!=0,'last viewer session cleanup')
 assert pane(test_sessions[0])==job_pids[0]
 record('closing last view destroys only its matching shell')
 screen('project-workflows')
except Exception as error:
 failure=repr(error)
 try:
  print('NATIVE FAILURE STATE',js('return {terms:projectTerms?.map(t=>({id:t.id,index:t.index,oldIndex:t._tPos,group:t.group?.id,pending:t.hasAttribute("pending")})),web:projectWeb?.id,order:projectFolder?.tabs?.map(t=>t.id),nativeDispatch:window.projectNativeDispatch,splitDiagnostic:window.projectSplitDiagnostic,drag:window.projectDragEvents||[]};'),flush=True)
  if args.gecko_native_drag_to_split:
   (proof/(args.label+'-split-lifecycle.json')).write_text(json.dumps(js('return window.projectSplitDiagnostic||null;'),indent=2)+'\n')
  screen('project-workflows-failure')
 except Exception:pass
 raise
finally:
 report={'app':str(args.app),'scope':'Synthetic data; native browser-method integration except explicitly labelled pointer action','results':results,'failure':failure,'run':str(run)}
 (proof/(args.label+'-project-workflows.json')).write_text(json.dumps(report,indent=2)+'\n')
 if m:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 if socket:
  for sid in test_sessions:
   tmux('kill-session','-t','=zt_'+sid)
 log.close()
