#!/usr/bin/env python3
"""Firefox156 native browser/security boundaries on disposable data only.
Uses actual public methods and real DOM; no extracted functions or remote shares.
"""
import argparse, json, os, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.keys import Keys
from marionette_driver.by import By

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='packaged')

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
 result=m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{'+script+'})().then(value=>done({value}),error=>done({error:String(error)}));',script_args=args or [])
 assert 'error' not in result,result
 return result['value']
def snapshot():
 return js('return {tabs:gBrowser.tabs.map(t=>t.id),spaces:gZenWorkspaces.getWorkspaces().map(s=>s.uuid),selected:gBrowser.selectedTab.id,sessions:Services.prefs.getStringPref("zen.terminal.sessions","{}")};')

def page(script):
 return js('const w=gBrowser.selectedBrowser.contentWindow.wrappedJSObject;const d=w.document;'+script)
def ready():
 return page('return d.getElementById("zen-terminal-surface")?.hasAttribute("terminal-ready");')
def focus_terminal():
 page('d.querySelector(".xterm-helper-textarea").focus();')
def keys(*values):
 # W3C keyboard actions target current native focus, not a synthetic JS event.
 action=m.actions.sequence('key','terminal-keyboard')
 for value in values:action.key_down(value)
 for value in reversed(values):action.key_up(value)
 action.perform();m.actions.release()
def type_text(value):
 action=m.actions.sequence('key','terminal-type')
 for char in value:action.key_down(char).key_up(char)
 action.perform();m.actions.release()
def query(value):
 keys(Keys.META,'a');type_text(value)
def command(value):
 focus_terminal();type_text(value);keys(Keys.ENTER)
def search_open():return page('return !d.getElementById("zen-terminal-find")?.hidden;')

failure=None
try:
 start()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 assert socket and socket.startswith('zen-terminal-p')
 # Test-only capture before script parsing: the genuine constructor still runs
 # unchanged. This observes actual options/selection, not source extraction.
 js("""window.keyboardObserver={observe(doc){
   if(!doc.documentURI.startsWith('chrome://browser/content/zen-terminal/terminal.xhtml'))return;
   const w=doc.defaultView.wrappedJSObject;let Original;
   Object.defineProperty(w,'Terminal',{configurable:true,get(){return Original;},set(value){
     Original=new Proxy(value,{construct(target,args){const instance=Reflect.construct(target,args);w.__keyboardProofTerminal=instance;return instance;}});
   }});
 }};Services.obs.addObserver(keyboardObserver,'document-element-inserted');
 const cis=ChromeUtils.importESModule('moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs').ContextualIdentityService;
 const store=ChromeUtils.importESModule('chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs');
 window.keyboardIdentity=cis.create('Keyboard proof','briefcase','purple');
 store.setTerminalContainerRecipe(keyboardIdentity.userContextId,{recipe:{steps:[]}});
 window.keyboardTab=gZenTerminalTabs.openTerminalContainerTab(keyboardIdentity.userContextId);
 """)
 sid=js('return keyboardTab.getAttribute("zen-terminal-session-id");');test_sessions.append(sid)
 wait(ready,'terminal ready')
 wait(lambda:page('return !!w.__keyboardProofTerminal;'),'real constructor capture')
 pid=tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}').stdout.strip();assert pid
 record('owned process, synthetic profile, real terminal and shell confirmed')
 motion=page('return {matches:w.matchMedia("(prefers-reduced-motion: reduce)").matches,blink:w.__keyboardProofTerminal.options.cursorBlink,scroll:w.__keyboardProofTerminal.options.smoothScrollDuration};')
 assert motion=={'matches':True,'blink':False,'scroll':0},motion
 record('synthetic reduced-motion preference reaches actual matchMedia and xterm options',motion)
 command("printf 'SEARCH_LITERAL.* alpha\\nSEARCH_LITERAL.* beta\\n'")
 wait(lambda:page('return w.__keyboardProofTerminal.buffer.active.length > 2;'),'output')
 for modifier,label in [(Keys.META,'Cmd+F'),(Keys.CONTROL,'Ctrl+F')]:
  focus_terminal();keys(modifier,'f');wait(search_open,label+' opens terminal find')
  assert js('return !gBrowser.selectedTab._findBar || gBrowser.selectedTab._findBar.hidden;'),'browser find unexpectedly opened'
  query('SEARCH_LITERAL.*')
  wait(lambda:page('return w.__keyboardProofTerminal.getSelection()==="SEARCH_LITERAL.*";'),'literal result')
  keys(Keys.ENTER);keys(Keys.SHIFT,Keys.ENTER)
  assert page('return d.getElementById("zen-terminal-find-result").textContent;')=='Match found'
  query('NO_SUCH_SEARCH_9f02')
  wait(lambda:page('return d.getElementById("zen-terminal-find-result").textContent==="No matches";'),'no-match')
  query('touch "$HOME/SEARCH_MUST_NOT_RUN"');keys(Keys.ENTER)
  keys(Keys.ESCAPE)
  assert not search_open()
  assert page('return d.activeElement===d.querySelector(".xterm-helper-textarea");')
  assert not (home/'SEARCH_MUST_NOT_RUN').exists()
  record(label+' native keyboard: terminal-only find, literal text, navigation, no-match, no shell execution, Escape focus')
 command('printf "ok\\n" > "$HOME/keyboard-after-search"')
 wait(lambda:(home/'keyboard-after-search').exists(),'shell input after find')
 assert (home/'keyboard-after-search').read_text()=='ok\n'
 js('window.keyboardOldDocument=gBrowser.selectedBrowser.contentDocument;gBrowser.selectedBrowser.reload();');wait(lambda:js('return gBrowser.selectedBrowser.contentDocument!==keyboardOldDocument;'),'new reload document');wait(ready,'reload ready')
 wait(lambda:page('return d.activeElement===d.querySelector(".xterm-helper-textarea");'),'reload focus')
 assert tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}').stdout.strip()==pid
 record('reload restores terminal focus and same saved shell')
 assert tmux('detach-client','-s','zt_'+sid).returncode==0
 wait(lambda:page('return !d.getElementById("zen-terminal-reconnect").hidden;'),'reconnect offer')
 # Keyboard activates the actual reconnect button, not its callback.
 page('d.getElementById("zen-terminal-reconnect").focus();');keys(Keys.ENTER)
 wait(ready,'recovery ready')
 wait(lambda:page('return d.activeElement===d.querySelector(".xterm-helper-textarea");'),'recovery focus')
 assert tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}').stdout.strip()==pid
 record('detached viewer reconnect restores focus without changing saved shell')
 for theme,value in [('light',0),('dark',1)]:
  js('Services.prefs.setIntPref("ui.systemUsesDarkTheme",arguments[0]);',[value])
  m.set_window_rect(width=620,height=440)
  focus_terminal();keys(Keys.META,'f');wait(search_open,'small find')
  query('NO_SUCH_SEARCH_9f02')
  layout=page("""const ids=['zen-terminal-find','zen-terminal-find-input','zen-terminal-find-result','zen-terminal-status'];return ids.map(id=>{const e=d.getElementById(id),r=e.getBoundingClientRect();return {id,width:r.width,height:r.height,left:r.left,right:r.right,viewport:w.innerWidth,overflow:e.scrollWidth>e.clientWidth+1};});""")
  assert all(r['width']>0 and r['height']>0 and r['left']>=0 and r['right']<=r['viewport']+1 and not r['overflow'] for r in layout),layout
  assert page('return d.getElementById("zen-terminal-find-input").getAttribute("aria-label") && d.getElementById("zen-terminal-find-result").getAttribute("aria-live")==="polite";')
  screen('keyboard-search-'+theme+'-small');keys(Keys.ESCAPE)
  record(theme+' system preference small window controls/status fit; terminal intentionally stays dark',layout)
 js('Services.prefs.setIntPref("ui.prefersReducedMotion",0);')
 wait(lambda:page('return !w.matchMedia("(prefers-reduced-motion: reduce)").matches && w.__keyboardProofTerminal.options.smoothScrollDuration===80;'),'live reduced-motion off')
 js('Services.prefs.setIntPref("ui.prefersReducedMotion",1);')
 wait(lambda:page('return !w.__keyboardProofTerminal.options.cursorBlink && w.__keyboardProofTerminal.options.smoothScrollDuration===0;'),'live reduced-motion on')
 record('live motion preference transitions update actual terminal options; non-reduced cursor style may be controlled by shell/tmux')
 results.extend([{'test':'OS clipboard all-format preservation and paste','result':'not_run','detail':'No system clipboard access; cannot guarantee all original formats and concurrent owner race preservation.'},{'test':'OS IME composition / screen-reader speech','result':'not_run','detail':'Trusted keyboard automation is not an operating-system input-method or assistive-technology session. DOM labels/live regions checked only.'}])
except Exception as error:
 failure=repr(error)
 try:
  print('KEYBOARD FAILURE STATE',page('return {uri:w.location.href,status:d.getElementById("zen-terminal-status-text")?.textContent,focus:d.activeElement?.outerHTML,motion:{matches:w.matchMedia("(prefers-reduced-motion: reduce)").matches,blink:w.__keyboardProofTerminal?.options.cursorBlink,scroll:w.__keyboardProofTerminal?.options.smoothScrollDuration},findHidden:d.getElementById("zen-terminal-find")?.hidden};'),flush=True)
  screen('keyboard-failure')
 except Exception:pass
 raise
finally:
 (proof/(args.label+'-keyboard.json')).write_text(json.dumps({'app':str(args.app),'scope':'Synthetic profile; W3C native keyboard input; constructor capture is test-only observation, not patched product logic','results':results,'failure':failure,'run':str(run)},indent=2)+'\n')
 if m:
  try:js("Services.obs.removeObserver(keyboardObserver,'document-element-inserted');")
  except Exception:pass
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 if socket:
  for sid in test_sessions:tmux('kill-session','-t','=zt_'+sid)
 log.close()
