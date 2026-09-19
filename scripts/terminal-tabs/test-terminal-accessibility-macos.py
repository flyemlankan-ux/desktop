#!/usr/bin/env python3
"""Native late accessibility activation on an isolated browser only.
Does not start VoiceOver, modify OS accessibility settings or test actual speech.
"""
import argparse, json, os, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='native-accessibility')

args=parser.parse_args()
if not args.label.replace('-', '').replace('_', '').isalnum():parser.error('label must contain letters, digits, hyphens or underscores')
root=Path(__file__).resolve().parents[2]
run=root/'.terminal-test'/('mac-'+uuid.uuid4().hex[:8]);run.mkdir(parents=True)
proof=root/'docs/proof/2026-09-19';proof.mkdir(parents=True,exist_ok=True)
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
def page(code):return js('const w=accessibilityTab.linkedBrowser.contentWindow.wrappedJSObject;const d=w.document;const terminal=w.__accessibilityTerminal;'+code)
def observer_count():return js('return Array.from(Services.obs.enumerateObservers("a11y-init-or-shutdown")).length;')
failure=None
try:
 start()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 assert not js('return Services.appinfo.accessibilityEnabled;'),'Accessibility already active: late activation cannot be proved; do not disable a real service'
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 baseline=observer_count()
 js("""window.accessibilityCapture={observe(doc){
 if(!doc.documentURI.startsWith('chrome://browser/content/zen-terminal/terminal.xhtml'))return;
 const w=doc.defaultView.wrappedJSObject;let Original;
 Object.defineProperty(w,'Terminal',{configurable:true,get(){return Original;},set(value){Original=new Proxy(value,{construct(target,args){const instance=Reflect.construct(target,args);w.__accessibilityTerminal=instance;return instance;}});}});
 }};Services.obs.addObserver(accessibilityCapture,'document-element-inserted');
 const cis=ChromeUtils.importESModule('moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs').ContextualIdentityService;
 const identity=cis.create('Accessibility proof','briefcase','purple');
 ChromeUtils.importESModule('chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs').setTerminalContainerRecipe(identity.userContextId,{recipe:{steps:[]}});
 window.accessibilityTab=gZenTerminalTabs.openTerminalContainerTab(identity.userContextId);
 """)
 sid=js('return accessibilityTab.getAttribute("zen-terminal-session-id");');test_sessions.append(sid)
 wait(lambda:page('return terminal && d.getElementById("zen-terminal-surface").hasAttribute("terminal-ready");'),'real terminal ready')
 assert not page('return terminal.options.screenReaderMode;')
 assert not page('return !!d.querySelector(".xterm-accessibility-tree");')
 record('Terminal starts without accessibility enabled',{'browser_observers_before':baseline,'browser_observers_after':observer_count(),'observer_scope':'diagnostic only; unrelated browser components initialize asynchronously'})
 # Real Firefox service activation, not a simulated observer notification.
 js('window.nativeAccessibilityEvents=[];window.nativeAccessibilityObserver={observe(subject,topic,data){nativeAccessibilityEvents.push(data);}};Services.obs.addObserver(nativeAccessibilityObserver,"a11y-init-or-shutdown");window.nativeAccessibilityService=Cc["@mozilla.org/accessibilityService;1"].getService(Ci.nsIAccessibilityService);')
 wait(lambda:page('return terminal.options.screenReaderMode && !!d.querySelector(".xterm-accessibility-tree");'),'late native service creates xterm accessibility tree')
 assert js('return nativeAccessibilityEvents.includes("1");')
 record('Actual Firefox accessibility service started after terminal; existing terminal creates accessible output tree')
 marker='ACCESSIBLE_'+uuid.uuid4().hex[:12]
 assert tmux('send-keys','-t','zt_'+sid,'-l',"printf '%s\\n' '"+marker+"'").returncode==0
 assert tmux('send-keys','-t','zt_'+sid,'Enter').returncode==0
 wait(lambda:page('return [...(d.querySelector(".xterm-accessibility-tree")?.children||[])].some(row=>row.textContent.trim()==='+json.dumps(marker)+');'),'real shell output in xterm accessibility DOM')
 accessible=wait(lambda:js("""const d=accessibilityTab.linkedBrowser.contentDocument;
 const root=nativeAccessibilityService.getAccessibleFor(d.getElementById('zen-terminal-surface'));
 if(!root)return null;let count=0;const names=[];
 function visit(node){if(++count>1500)throw Error('Bounded accessible tree exceeded');if(node.name)names.push(node.name);for(let i=0;i<node.childCount;i++)visit(node.getChildAt(i));}
 visit(root);return names.some(n=>n.trim()===arguments[0])?{surfaceName:root.name,outputMarkerPresent:true,nodes:count}:null;""",[marker]),'actual Firefox accessible objects expose output')
 assert accessible['surfaceName']=='Terminal'
 assert page('return !!d.querySelector(".xterm-helper-textarea").getAttribute("aria-label") && d.getElementById("zen-terminal-status-text").getAttribute("aria-live")==="polite";')
 record('Real accessible objects include terminal label and actual shell output; input label and live status exist',accessible)
 before_close=observer_count();js('gBrowser.removeTab(accessibilityTab,{animate:false});')
 wait(lambda:tmux('has-session','-t','=zt_'+sid).returncode!=0,'exact terminal job cleaned up')
 record('Actual tab close removes exact terminal job',{'browser_observers_before_close':before_close,'browser_observers_after_close':observer_count(),'observer_cleanup_proof':'exact subscription/removal checked by focused production-function lifecycle test, not inferred from global browser totals'})
 results.append({'test':'macOS VoiceOver speech and OS IME','result':'not_run','detail':'Browser accessibility objects are not a VoiceOver/IME session; no OS settings changed'})
except Exception as exc:
 failure=str(exc);print('FAIL',repr(exc),flush=True);raise
finally:
 if m:
  for observer,topic in [('accessibilityCapture','document-element-inserted'),('nativeAccessibilityObserver','a11y-init-or-shutdown')]:
   try:js('if(window[arguments[0]])Services.obs.removeObserver(window[arguments[0]],arguments[1]);',[observer,topic])
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
 (proof/(args.label+'-results.json')).write_text(json.dumps({'app':str(args.app),'results':results,'failure':failure,'run':str(run),'scope':'new synthetic profile; real nsIAccessibilityService, not macOS VoiceOver'},indent=2)+'\n')
