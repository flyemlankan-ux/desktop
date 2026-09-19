#!/usr/bin/env python3
"""Actual Firefox156 text-input-processor integration on an isolated native app.
Not macOS input-source/candidate UI or VoiceOver proof. No clipboard access.
"""
import argparse, json, os, shlex, socket as net_socket, subprocess, sys, time, uuid
from marionette_driver.keys import Keys
from pathlib import Path
from marionette_driver.marionette import Marionette

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='native-text-input')

args=parser.parse_args()
if not args.label.replace('-', '').replace('_', '').isalnum():parser.error('label must contain letters, digits, hyphens or underscores')
root=Path(__file__).resolve().parents[2]
run=root/'.terminal-test'/('mac-'+uuid.uuid4().hex[:8]);run.mkdir(parents=True)
proof=root/'docs/proof/2026-09-19';proof.mkdir(parents=True,exist_ok=True)
if (proof/(args.label+'-results.json')).exists():parser.error('Use a new label; preserve prior evidence')
home=run/'home';home.mkdir();profile=run/'profile';profile.mkdir()
(home/'.zshenv').write_text('export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n')
with net_socket.socket() as listener:
 listener.bind(('127.0.0.1',0));marionette_port=listener.getsockname()[1]
prefs={'marionette.port':marionette_port,'browser.shell.checkDefaultBrowser':False,'browser.startup.page':3,'zen.welcome-screen.seen':True,'app.update.disabledForTesting':True,'app.update.auto':False,'app.update.enabled':False,'browser.startup.homepage':'about:blank','browser.aboutwelcome.enabled':False,'browser.sessionstore.resume_from_crash':True,'privacy.userContext.enabled':True,'privacy.userContext.ui.enabled':True,'ui.prefersReducedMotion':1}
(profile/'user.js').write_text('\n'.join('user_pref(%s, %s);'%(json.dumps(k),json.dumps(v)) for k,v in prefs.items()))
env=dict(os.environ,MOZ_APP_DATA=str(home/'app-data'),MOZ_LOCAL_APP_DATA=str(home/'local-app-data'),HOME=str(home),ZDOTDIR=str(home),SHELL='/bin/zsh',PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',MOZ_NO_REMOTE='1')
# Restart-only environment values take priority over -profile in Firefox.
# Never inherit a real browser's selected profile into this synthetic test.
for key in list(env):
 if key.startswith(('XRE_PROFILE_', 'SELECTABLE_PROFILE_RESET_')) or key in {'XRE_RESTARTED_BY_PROFILE_MANAGER','MOZ_RESET_PROFILE_RESTART','MOZ_LEGACY_PROFILES'}:
  env.pop(key,None)
exe=args.app.resolve()/'Contents/MacOS/zen-terminal'
if not exe.is_file():parser.error('Expected separate test app')
if 'Milestone=156.0' not in (args.app.resolve()/'Contents/Resources/platform.ini').read_text().splitlines():parser.error('Expected Firefox156; no launch')
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
def tmux(*values):
 assert socket and socket.startswith('zen-terminal-p')
 return subprocess.run(['/opt/homebrew/bin/tmux','-L',socket,*values],capture_output=True,text=True,timeout=5)
def page(code,values=None):return js('const w=inputTab.linkedBrowser.contentWindow.wrappedJSObject;const d=w.document;const terminal=w.__inputTerminal;'+code,values)
def keys(*values):
 action=m.actions.sequence('key','text-input-proof')
 for value in values:action.key_down(value)
 for value in reversed(values):action.key_up(value)
 action.perform();m.actions.release()
def compose(text):
 assert page('inputTIP.setPendingCompositionString(arguments[0]);inputTIP.appendClauseToPendingComposition(arguments[0].length,inputTIP.ATTR_RAW_CLAUSE);inputTIP.setCaretInPendingComposition(arguments[0].length);return inputTIP.flushPendingComposition();',[text])
def captured():return received.read_bytes() if received.exists() else b''
def unchanged(expected):
 # Bounded quiet window catches deferred xterm composition callbacks/duplicates.
 end=time.monotonic()+.8
 while time.monotonic()<end:assert captured()==expected,'Unexpected bytes reached the real PTY';time.sleep(.05)
def search_diagnostics():
 return page("""const input=d.getElementById('zen-terminal-find-input');
 const buffer=terminal?.buffer.active;const lines=[];
 if(buffer)for(let i=Math.max(0,buffer.length-40);i<buffer.length;i++)lines.push(buffer.getLine(i)?.translateToString(true)||'');
 return {query:input?.value,result:d.getElementById('zen-terminal-find-result')?.textContent,
  selection:terminal?.getSelectionPosition()||null,rows:terminal?.rows,columns:terminal?.cols,
  activeElement:d.activeElement?.id,composing:window.inputTIP?.hasComposition,
  recentBuffer:lines,inputEvents:w.__searchInputEvents||[],layoutEvents:w.__searchLayoutEvents||[]};""")
received=home/'received-input.bin';receiver_ready=home/'receiver-ready';failure=None;diagnostics=None
try:
 start();assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 command=' '.join(shlex.quote(str(x)) for x in [Path(sys.executable).resolve(),root/'scripts/terminal-tabs/terminal-text-input-receiver.py',received,receiver_ready])
 js("""window.inputCapture={observe(doc){if(!doc.documentURI.startsWith('chrome://browser/content/zen-terminal/terminal.xhtml'))return;const w=doc.defaultView.wrappedJSObject;let Original;Object.defineProperty(w,'Terminal',{configurable:true,get(){return Original;},set(value){Original=new Proxy(value,{construct(target,args){const t=Reflect.construct(target,args);w.__inputTerminal=t;return t;}});}});}};Services.obs.addObserver(inputCapture,'document-element-inserted');
 const cis=ChromeUtils.importESModule('moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs').ContextualIdentityService;const identity=cis.create('Input proof','briefcase','purple');ChromeUtils.importESModule('chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs').setTerminalContainerRecipe(identity.userContextId,{recipe:{steps:[{command:arguments[0]}]}});window.inputTab=gZenTerminalTabs.openTerminalContainerTab(identity.userContextId);""",[command])
 sid=js('return inputTab.getAttribute("zen-terminal-session-id");');test_sessions.append(sid)
 wait(lambda:receiver_ready.exists() and page('return !!terminal && d.getElementById("zen-terminal-surface").hasAttribute("terminal-ready");'),'real PTY receiver ready')
 page('d.querySelector(".xterm-helper-textarea").focus();w.__compositionEvents=[];for(const type of ["compositionstart","compositionupdate","compositionend"]){d.addEventListener(type,e=>w.__compositionEvents.push({type:e.type,trusted:e.isTrusted,data:e.data}),true);}')
 assert page('window.inputTIP=Cc["@mozilla.org/text-input-processor;1"].createInstance(Ci.nsITextInputProcessor);return inputTIP.beginInputTransactionForTests(w);')
 composed='雪😀e\u0301'
 compose('temporary');unchanged(b'')
 compose(composed);unchanged(b'')
 page('inputTIP.commitComposition();')
 wait(lambda:captured()==composed.encode(),'composed Unicode reaches PTY exactly once');unchanged(composed.encode())
 events=page('return w.__compositionEvents;')
 assert events and all(e['trusted'] for e in events) and events[-1]['type']=='compositionend'
 record('Actual Gecko composition update/commit sends CJK, emoji and combining Unicode exactly once into real PTY',{'trusted_event_count':len(events),'byte_count':len(captured())})
 compose('CANCELLED雪');page('inputTIP.cancelComposition();');unchanged(composed.encode())
 record('Actual Gecko composition cancellation writes no bytes to shell receiver')
 # Normal W3C key actions exercise the product Option-as-Meta setting without
 # switching the operating-system keyboard/input source or touching clipboard.
 keys(Keys.ALT,'b');expected=composed.encode()+b'\x1bb'
 wait(lambda:captured()==expected,'Option-b reaches terminal as ESC b');unchanged(expected)
 record('Real browser Option-b key action sends one Meta escape sequence to PTY')
 # Opening search resizes xterm, then tmux redraws asynchronously. Record
 # actual parse/resize activity and wait for that transition BEFORE typing;
 # isolate that potential selection-reset race before assessing composition.
 page("""w.__searchLayoutEvents=[];w.__lastSearchLayoutEvent=Date.now();
 for(const [event,name] of [[terminal.onResize,'resize'],[terminal.onWriteParsed,'parsed']]){
  event.call(terminal,()=>{w.__lastSearchLayoutEvent=Date.now();w.__searchLayoutEvents.push({type:name,time:Date.now(),rows:terminal.rows,columns:terminal.cols});if(w.__searchLayoutEvents.length>30)w.__searchLayoutEvents.shift();});
 }
 w.__searchInputEvents=[];d.getElementById('zen-terminal-find-input').addEventListener('input',e=>{
  w.__searchInputEvents.push({trusted:e.isTrusted,composing:e.isComposing,inputType:e.inputType,value:e.target.value,time:Date.now()});
 });""")
 keys(Keys.META,'f');wait(lambda:page('return !d.getElementById("zen-terminal-find").hidden;'),'terminal search opens')
 wait(lambda:page(r"""const b=terminal.buffer.active;let text='';for(let i=0;i<b.length;i++)text+=(b.getLine(i)?.translateToString(true)||'')+'\n';
 return text.includes('SEARCH雪 one') && text.includes('SEARCH雪 two') && Date.now()-w.__lastSearchLayoutEvent>=500;"""),'search layout settled with actual receiver matches still in xterm')
 print('SEARCH_BEFORE_COMPOSITION',json.dumps(search_diagnostics(),ensure_ascii=False),flush=True)
 assert page('return d.activeElement===d.getElementById("zen-terminal-find-input");')
 assert page('return inputTIP.beginInputTransactionForTests(w);')
 page('inputTIP.commitCompositionWith("SEARCH");');compose('雪')
 wait(lambda:page('return d.getElementById("zen-terminal-find-input").value==="SEARCH雪";'),'search composition text')
 # Observe trusted key state at capture, not a fabricated DOM keyboard event.
 page('w.__composingEnter=[];d.addEventListener("keydown",e=>{if(e.key==="Enter")w.__composingEnter.push({trusted:e.isTrusted,composing:e.isComposing});},true);')
 time.sleep(.2)
 print('SEARCH_DURING_COMPOSITION',json.dumps(search_diagnostics(),ensure_ascii=False),flush=True)
 before_selection=wait(lambda:page('return terminal.getSelectionPosition() || null;'),'real search match selected before composing Enter')
 page('const key=new w.KeyboardEvent("",{key:"Enter",code:"Enter"});inputTIP.keydown(key);inputTIP.keyup(key);')
 time.sleep(.2)
 assert page('return inputTIP.hasComposition;')
 assert page('return terminal.getSelectionPosition() || null;')==before_selection
 assert page('return w.__composingEnter.some(e=>e.trusted && e.composing);')
 unchanged(expected)
 record('Gecko composing Enter remains composing; does not advance search selection or send shell bytes')
 page('inputTIP.commitComposition();');wait(lambda:page('return d.getElementById("zen-terminal-find-input").value==="SEARCH雪";'),'search composition committed')
 keys(Keys.SHIFT,Keys.ARROW_LEFT)
 assert page('const input=d.getElementById("zen-terminal-find-input");return input.selectionEnd>input.selectionStart;')
 unchanged(expected)
 record('Search Unicode commit and real Shift-Left selection stay inside search, not shell')
 results.append({'test':'actual macOS input source, candidate UI, dead keys and VoiceOver','result':'not_run','detail':'This test covers Firefox text-input integration only; no OS input-source/settings changes'})
except Exception as exc:
 failure=str(exc);print('FAIL',repr(exc),flush=True)
 if m:
  try:
   diagnostics=search_diagnostics();print('SEARCH_FAILURE_DIAGNOSTICS',json.dumps(diagnostics,ensure_ascii=False),flush=True)
  except Exception as diagnostic_error:diagnostics={'unavailable':str(diagnostic_error)}
 raise
finally:
 if m:
  try:js('if(window.inputTIP?.hasComposition)inputTIP.cancelComposition();if(window.inputCapture)Services.obs.removeObserver(inputCapture,"document-element-inserted");')
  except Exception:pass
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:
   process.terminate()
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill();process.wait()
 if socket:
  for sid in test_sessions:tmux('kill-session','-t','=zt_'+sid)
 log.close()
 (proof/(args.label+'-results.json')).write_text(json.dumps({'app':str(args.app),'results':results,'failure':failure,'search_diagnostics':diagnostics,'run':str(run),'scope':'real Firefox nsITextInputProcessor plus real PTY bytes; NOT actual macOS input-method/candidate UI'},indent=2)+'\n')
