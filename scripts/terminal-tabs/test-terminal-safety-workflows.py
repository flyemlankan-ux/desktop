#!/usr/bin/env python3
"""Native terminal safety journeys using disposable synthetic data only.
Exercises real browser machinery; restart confirmation uses a rendered button click.
"""
import argparse, json, os, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.keys import Keys

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='packaged')
parser.add_argument('--skip-private-modal',action='store_true',help='Explicitly leave modal-button acceptance NOT RUN; still test direct private-page refusal and all session journeys')
args=parser.parse_args()
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
def state():
 return js('const d=safetyTab?.linkedBrowser.contentDocument;const b=d?.getElementById("zen-terminal-reconnect");return {status:d?.getElementById("zen-terminal-status-text")?.textContent,button:b?.textContent,visible:b && !b.hidden,ready:d?.getElementById("zen-terminal-surface")?.hasAttribute("terminal-ready"),url:safetyTab?.linkedBrowser.currentURI.spec};')
def launch_count():return len(marker.read_text().splitlines()) if marker.exists() else 0
def session_records():return js('return Services.prefs.getStringPref("zen.terminal.sessions","{}");')
def click_restart():
 # Top-level terminal tabs have their own WebDriver content handle.
 # Locate that handle before requesting its button; chrome-returned elements
 # belong to the wrong context and cannot be clicked by WebDriver.
 target_url=state()['url']
 chrome_handle=m.current_chrome_window_handle
 try:
  m.set_context('content')
  matched=False
  for handle in m.window_handles:
   m.switch_to_window(handle)
   if m.execute_script('return document.documentURI;')==target_url:
    matched=True
    break
  assert matched,'Terminal content handle not found'
  m.find_element('id','zen-terminal-reconnect').click()
 finally:
  m.set_context('chrome')
  m.switch_to_window(chrome_handle)
 wait(lambda:state()['ready'],'terminal ready after explicit rendered restart click')

def pane_pid(sid):
 result=tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}')
 assert result.returncode==0,result.stderr
 value=result.stdout.strip()
 assert value.isdigit(),repr(value)
 return value

failure=None
try:
 start()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 assert socket.startswith('zen-terminal-p')
 record('owned app, profile and data roots confirmed')
 import shlex
 marker=run/'startup-count.txt'
 js('const cis=ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService;window.safetyIdentity=cis.create("Safety proof","briefcase","purple");window.safetyOther=cis.create("Other proof","fingerprint","blue");ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs").setTerminalContainerRecipe(safetyIdentity.userContextId,{recipe:{steps:[arguments[0]]}});', ['printf "launch\\n" >> '+shlex.quote(str(marker))])
 identity=js('return safetyIdentity.userContextId;')
 # An explicit mismatched internal address must not register or launch a job.
 before=session_records()
 rejected='rejected-'+uuid.uuid4().hex[:12]
 test_sessions.append(rejected)
 js('window.safetyRejected=gBrowser.addTab("chrome://browser/content/zen-terminal/terminal.xhtml?session="+arguments[0]+"&userContextId="+safetyIdentity.userContextId,{userContextId:safetyOther.userContextId,triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});gBrowser.selectedTab=safetyRejected;',[rejected])
 wait(lambda:js('return safetyRejected.linkedBrowser.contentDocument?.getElementById("zen-terminal-status-text")?.textContent.includes("does not match");'),'visible identity mismatch refusal')
 assert session_records()==before
 assert launch_count()==0
 assert tmux('has-session','-t','=zt_'+rejected).returncode!=0
 record('mismatched actual container refused before records or command launch')
 # Use a genuine private browser window and its actual modal alert.
 normal_handle=m.current_chrome_window_handle
 handles=set(m.chrome_window_handles)
 js('window.safetyPrivate=OpenBrowserWindow({private:true});')
 private_handle=wait(lambda:next(iter(set(m.chrome_window_handles)-handles),None),'new private chrome handle')
 m.switch_to_window(private_handle);m.set_context('chrome')
 wait(lambda:js('return gBrowserInit.delayedStartupFinished && !!window.gZenTerminalTabs;'),'private browser initialized')
 assert js('return ChromeUtils.importESModule("resource://gre/modules/PrivateBrowsingUtils.sys.mjs").PrivateBrowsingUtils.isWindowPrivate(window);')
 before=session_records();tab_count=js('return gBrowser.tabs.length;')
 if args.skip_private_modal:
  results.append({'test':'actual private opener modal acceptance','result':'not_run','detail':'Explicit --skip-private-modal; Gecko155 WebDriver dismissal currently times out. No private-modal acceptance claimed.'})
 else:
  js('window.safetyPrivateResult="waiting";setTimeout(()=>{window.safetyPrivateResult=gZenTerminalTabs.openTerminalContainerTab(arguments[0]);},0);',[identity])
  alert_text=wait(lambda:m.switch_to_alert().text,'private terminal refusal alert')
  print('OBSERVED private alert body',repr(alert_text),flush=True)
  assert 'shell history and files' in alert_text and 'normal window' in alert_text,repr(alert_text)
  m.switch_to_alert().accept()
  wait(lambda:js('return window.safetyPrivateResult===null;'),'private opener returns no tab')
  assert js('return gBrowser.tabs.length;')==tab_count
  assert session_records()==before and launch_count()==0
  record('actual private opener explains refusal and its modal accepts without tab or command',alert_text)
 # Defense inside the page must also reject a direct trusted open in private mode.
 private_sid='private-'+uuid.uuid4().hex[:12]
 test_sessions.append(private_sid)
 js('window.safetyDirect=gBrowser.addTab("chrome://browser/content/zen-terminal/terminal.xhtml?session="+arguments[0]+"&userContextId="+arguments[1],{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});gBrowser.selectedTab=safetyDirect;',[private_sid,identity])
 wait(lambda:js('return safetyDirect.linkedBrowser.contentDocument?.getElementById("zen-terminal-status-text")?.textContent.includes("private windows");'),'direct private page refusal')
 assert session_records()==before and launch_count()==0
 assert tmux('has-session','-t','=zt_'+private_sid).returncode!=0
 record('direct private terminal address also refuses before record or command')
 js('window.close();')
 m.switch_to_window(normal_handle);m.set_context('chrome')
 # Open a valid terminal. Markers count actual saved startup execution.
 sid=js('window.safetyTab=gZenTerminalTabs.openTerminalContainerTab(safetyIdentity.userContextId);return safetyTab.getAttribute("zen-terminal-session-id");')
 test_sessions.append(sid)
 wait(lambda:state()['ready'],'fresh terminal ready')
 wait(lambda:launch_count()==1,'first startup exactly once')
 original_pid=pane_pid(sid)
 assert 'started=1' in state()['url']
 record('fresh terminal starts once and retains ended-session history marker')
 assert tmux('kill-session','-t','=zt_'+sid).returncode==0
 js('safetyTab.linkedBrowser.reload();')
 wait(lambda:state()['visible'] and state()['button']=='Start again','lost terminal offers Start again')
 assert launch_count()==1
 assert tmux('has-session','-t','=zt_'+sid).returncode!=0
 screen('safety-ended-session')
 record('lost process offers visible restart choice without rerunning startup')
 js('safetyTab.linkedBrowser.reload();')
 wait(lambda:state()['button']=='Start again' and state()['visible'],'reload retains restart choice')
 assert launch_count()==1
 assert tmux('has-session','-t','=zt_'+sid).returncode!=0
 record('reload cannot silently authorize another startup')
 click_restart();wait(lambda:launch_count()==2,'explicit restart runs startup once')
 assert pane_pid(sid)!=original_pid
 record('rendered Start again click creates a new job exactly once')
 # Final close really destroys this session; Undo restores history, not its process.
 js('gBrowser.removeTab(safetyTab,{animate:false});')
 wait(lambda:tmux('has-session','-t','=zt_'+sid).returncode!=0,'final close destroys exact job')
 wait(lambda:not json.loads(session_records()).get(sid),'closed session record cleaned')
 js('window.safetyTab=SessionStore.undoCloseTab(window,0);gBrowser.selectedTab=safetyTab;')
 wait(lambda:state()['button']=='Start again' and state()['visible'],'Undo Close requires explicit restart')
 assert 'started=1' in state()['url']
 assert launch_count()==2
 assert tmux('has-session','-t','=zt_'+sid).returncode!=0
 record('Undo Close keeps marker and never silently recreates intentionally closed work')
 click_restart();wait(lambda:launch_count()==3,'Undo explicit restart runs startup once')
 record('Undo Close rendered restart button starts one fresh job')
 screen('safety-complete')
except Exception as error:
 failure=repr(error)
 raise
finally:
 report={'app':str(args.app),'scope':'Synthetic profile, real browser mechanisms and rendered restart-button clicks; no personal data','results':results,'failure':failure,'run':str(run)}
 (proof/(args.label+'-safety-workflows.json')).write_text(json.dumps(report,indent=2)+'\n')
 if m:
  try:m.switch_to_alert().dismiss()
  except Exception:pass
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 if socket:
  for sid in test_sessions:tmux('kill-session','-t','=zt_'+sid)
 log.close()
