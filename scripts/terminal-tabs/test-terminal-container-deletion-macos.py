#!/usr/bin/env python3
"""Native Firefox156 container-service deletion; synthetic profiles/jobs only."""
import argparse, json, os, shlex, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--app',type=Path,required=True)
p.add_argument('--label',default='container-service-deletion')
p.add_argument('--expected-engine',default='156.0')
a=p.parse_args()
if not a.label.replace('-','').replace('_','').isalnum():p.error('Use letters, numbers, hyphens and underscores in label')
root=Path(__file__).resolve().parents[2]
app=a.app.resolve();exe=app/'Contents/MacOS/zen-terminal'
if not exe.is_file():p.error('Expected separate Zen Terminal app')
if 'Milestone='+a.expected_engine not in (app/'Contents/Resources/platform.ini').read_text().splitlines():p.error('App engine does not match expected version; no launch')
run=root/'.terminal-test'/('service-delete-'+uuid.uuid4().hex[:8]);home=run/'home';profile=run/'profile'
home.mkdir(parents=True);profile.mkdir()
proof=root/'docs/proof/2026-09-19';proof.mkdir(parents=True,exist_ok=True)
(home/'.zshenv').write_text('export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n')
(home/'.zshrc').write_text("PROMPT='deletion-proof> '\n")
with net_socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
prefs={'marionette.port':port,'browser.shell.checkDefaultBrowser':False,'browser.startup.page':0,'zen.welcome-screen.seen':True,'browser.startup.homepage':'about:blank','browser.aboutwelcome.enabled':False,'app.update.disabledForTesting':True,'app.update.enabled':False,'privacy.userContext.enabled':True,'privacy.userContext.ui.enabled':True}
(profile/'user.js').write_text('\n'.join('user_pref(%s,%s);'%(json.dumps(k),json.dumps(v)) for k,v in prefs.items()))
env=dict(os.environ,MOZ_APP_DATA=str(home/'app-data'),MOZ_LOCAL_APP_DATA=str(home/'local-app-data'),HOME=str(home),ZDOTDIR=str(home),SHELL='/bin/zsh',PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',MOZ_NO_REMOTE='1')
for key in list(env):
 if key.startswith(('XRE_PROFILE_','SELECTABLE_PROFILE_RESET_')) or key in {'XRE_RESTARTED_BY_PROFILE_MANAGER','MOZ_RESET_PROFILE_RESTART','MOZ_LEGACY_PROFILES'}:env.pop(key,None)
manager_url='chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs'
store_url='chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs'
cis_url='moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs'
process=None;m=None;socket=None;results=[];log=(run/'gecko.log').open('w')
def js(code,values=None):return m.execute_script(code,script_args=values or [])
def wait(check,label,timeout=30):
 end=time.monotonic()+timeout;last=None
 while time.monotonic()<end:
  try:
   value=check()
   if value:return value
  except Exception as exc:last=exc
  time.sleep(.1)
 raise AssertionError('Timed out '+label+'; '+str(last))
def record(name,detail=True):results.append({'test':name,'result':'pass','detail':detail});print('PASS',name,detail,flush=True)
def tmux(*args):
 assert socket and socket.startswith('zen-terminal-p')
 return subprocess.run(['/opt/homebrew/bin/tmux','-L',socket,*args],capture_output=True,text=True,timeout=6)
def exists(sid):return tmux('has-session','-t','=zt_'+sid).returncode==0
def create_setup(name,command=''):
 return js('const cis=ChromeUtils.importESModule(arguments[0]).ContextualIdentityService;const identity=cis.create(arguments[2],"briefcase","purple");ChromeUtils.importESModule(arguments[1]).setTerminalContainerRecipe(identity.userContextId,{recipe:{steps:arguments[3]?[{command:arguments[3]}]:[]}});return identity.userContextId;',[cis_url,store_url,name,command])
def open_job(owner,key):
 sid=js('window[arguments[1]]=gZenTerminalTabs.openTerminalContainerTab(arguments[0]);return window[arguments[1]].getAttribute("zen-terminal-session-id");',[owner,key])
 wait(lambda:js('return window[arguments[0]].linkedBrowser.contentDocument?.getElementById("zen-terminal-surface")?.hasAttribute("terminal-ready");',[key]),'terminal '+key)
 return sid
def remove(owner):return js('return ChromeUtils.importESModule(arguments[0]).ContextualIdentityService.remove(arguments[1]);',[cis_url,owner])
def records():return js('return ChromeUtils.importESModule(arguments[0]).readTerminalSessionRecords();',[manager_url])
def recipe(owner):return js('return ChromeUtils.importESModule(arguments[0]).getTerminalContainerRecipe(arguments[1]);',[store_url,owner])
def screen(name):(proof/(a.label+'-'+name+'.png')).write_bytes(m.screenshot(format='binary'))
def alive(pid):
 try:os.kill(pid,0);return True
 except ProcessLookupError:return False
try:
 process=subprocess.Popen([str(exe),'-no-remote','-marionette','--remote-allow-system-access','-profile',str(profile)],env=env,stdout=log,stderr=log)
 m=Marionette(host='127.0.0.1',port=port,socket_timeout=30,startup_timeout=30);m.raise_for_port(timeout=30);m.start_session();m.set_context('chrome')
 assert js('return Services.appinfo.processID;')==process.pid
 assert Path(js('return Services.dirsvc.get("ProfD",Ci.nsIFile).path;')).resolve()==profile.resolve()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 wait(lambda:js('return Boolean(window.gZenTerminalTabs && gBrowserInit.delayedStartupFinished);'),'browser ready')
 socket=js('return ChromeUtils.importESModule(arguments[0]).getTerminalTmuxSocket();',[manager_url]);first_handle=m.current_chrome_window_handle
 record('Firefox156 app owns fresh synthetic profile and app-data',a.expected_engine)
 owner=create_setup('Delete this setup');neighbor_owner=create_setup('Keep neighbor')
 visible=open_job(owner,'deletionVisible');background=open_job(owner,'deletionBackground');neighbor=open_job(neighbor_owner,'deletionNeighbor')
 assert all(exists(sid) for sid in [visible,background,neighbor])
 # Firefox normally refuses discarding privileged non-remote pages. Respect
 # that rule; never fake an unloaded browser or close a tab just to get a pass.
 discarded=js('return gBrowser.discardBrowser(deletionBackground,true);')
 if discarded:wait(lambda:js('return deletionBackground.hasAttribute("pending");'),'background page discarded')
 else:assert js('return !deletionBackground.selected && !deletionBackground.linkedBrowser.isRemoteBrowser;')
 assert exists(background)
 record('Two matching jobs and neighbor run, with a genuine background terminal tab',{'page_unloaded':bool(discarded),'background_tab_selected':False})
 js('window.__deletionFirstWindow=true;window.__deletionObserver=ChromeUtils.importESModule(arguments[0]).getTerminalSessionCoordinator().containerCleanupObserver;',[manager_url])
 assert js('return Boolean(window.__deletionObserver);')
 handles=set(m.chrome_window_handles);js('OpenBrowserWindow();')
 second_handle=wait(lambda:next(iter(set(m.chrome_window_handles)-handles),None),'second browser window')
 m.switch_to_window(second_handle);m.set_context('chrome')
 wait(lambda:js('return Boolean(window.gZenTerminalTabs && gBrowserInit.delayedStartupFinished);'),'second window ready')
 assert js('const shared=ChromeUtils.importESModule(arguments[0]);shared.ensureTerminalContainerCleanupObserver();const windows=ChromeUtils.importESModule("resource:///modules/BrowserWindowTracker.sys.mjs").BrowserWindowTracker.orderedWindows;const first=windows.find(w=>w.__deletionFirstWindow);return !!first && shared.getTerminalSessionCoordinator().containerCleanupObserver===first.__deletionObserver;',[manager_url])
 # Counting the whole topic could include unrelated Firefox observers; compare
 # this exact shared production observer instead.
 record('Two actual windows use the same shared profile cleanup observer')
 assert remove(owner)
 assert recipe(owner) is None and recipe(neighbor_owner) is not None
 wait(lambda:not exists(visible) and not exists(background),'matching real tmux jobs stopped')
 wait(lambda:visible not in records() and background not in records(),'matching records removed')
 assert exists(neighbor) and neighbor in records()
 assert remove(owner) is False
 assert exists(neighbor)
 record('Native service removal stops visible/background exact jobs, removes recipe, keeps neighbor; duplicate removal harmless')
 m.switch_to_window(first_handle);m.set_context('chrome')
 js('gBrowser.selectedTab=deletionVisible;')
 wait(lambda:js('return deletionVisible.linkedBrowser.contentDocument?.getElementById("zen-terminal-status-text")?.textContent.includes("closed");'),'visible deleted terminal feedback')
 screen('service-deleted')
 # Pause only test-provided settings callback. Do not modify production methods.
 race_owner=create_setup('Creation race');race_id='delete-race-'+uuid.uuid4().hex[:12]
 race_marker=home/'race-must-not-run'
 js('const manager=ChromeUtils.importESModule(arguments[0]);manager.registerTerminalSession(arguments[1],{userContextId:arguments[2]});window.__raceState="starting";window.__raceDone=manager.prepareTerminalTmuxSession("/opt/homebrew/bin/tmux",arguments[1],async()=>{window.__raceState="waiting";await new Promise(resolve=>window.__releaseDeletionRace=resolve);return {shell:"/bin/sh",home:arguments[3],startupCommand:arguments[4]};}).then(()=>window.__raceState="unexpected-success",error=>window.__raceState=error.message);',[manager_url,race_id,race_owner,str(home),'touch '+shlex.quote(str(race_marker))])
 wait(lambda:js('return window.__raceState==="waiting";'),'new-job settings barrier')
 assert remove(race_owner);js('window.__releaseDeletionRace();')
 wait(lambda:js('return /closed|removed/.test(window.__raceState);'),'final creation guard refusal')
 wait(lambda:race_id not in records(),'race cleanup record removal')
 assert not exists(race_id) and not race_marker.exists()
 record('Actual service deletion during pending new-job settings prevents any startup command')
 # Simulate tmux unavailability only inside this synthetic user's login shell.
 (home/'.zprofile').write_text('export PATH=/usr/bin:/bin:/usr/sbin:/sbin\n')
 plain_marker=home/'plain-shell-pid'
 plain_owner=create_setup('Direct helper cleanup','printf "%s" "$$" > '+shlex.quote(str(plain_marker)))
 plain_sid=open_job(plain_owner,'deletionPlain')
 wait(lambda:plain_marker.exists(),'owned direct shell PID')
 plain_pid=int(plain_marker.read_text());assert plain_pid>1 and alive(plain_pid)
 assert js('return deletionPlain.linkedBrowser.contentDocument.getElementById("zen-terminal-status-text").textContent.includes("not saved");')
 assert not exists(plain_sid)
 assert remove(plain_owner)
 wait(lambda:not alive(plain_pid),'direct shell terminated by exact page notification')
 assert exists(neighbor)
 record('Without tmux, native service removal stops real direct shell and preserves unrelated tmux neighbor')
 (home/'.zprofile').write_text('export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n')
 m.execute_async_script('const done=arguments[arguments.length-1];ChromeUtils.importESModule(arguments[0]).retryPendingTerminalSessionDeletes().then(done);',script_args=[manager_url])
 wait(lambda:plain_sid not in records(),'direct cleanup pending record resolved after tools return')
 record('Pending direct cleanup record clears after tool availability returns')
except Exception as exc:
 results.append({'test':'native service deletion journey','result':'fail','detail':str(exc)});print('FAIL',repr(exc),flush=True)
 if m:
  try:screen('failure')
  except Exception:pass
 raise
finally:
 if m:
  try:m.set_context('chrome');js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);return true;')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:
   process.terminate()
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill();process.wait()
 if socket:tmux('kill-server') # Test-owned new profile socket only, not production cleanup.
 log.close()
 (proof/(a.label+'-results.json')).write_text(json.dumps({'app':str(app),'engine':a.expected_engine,'test_data':'new synthetic profile, native identities and test-owned jobs only','results':results,'log':str(run/'gecko.log')},indent=2)+'\n')
