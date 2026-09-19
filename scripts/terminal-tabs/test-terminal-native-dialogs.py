#!/usr/bin/env python3
"""Real macOS folder-picker and private alert controls, scoped to one owned app PID."""
import argparse, importlib.util, json, os, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--app',required=True,type=Path);p.add_argument('--label',default='native-dialogs');p.add_argument('--launch-services',action='store_true');a=p.parse_args()
if not a.label.replace('-','').replace('_','').isalnum():p.error('Invalid proof label')
root=Path(__file__).resolve().parents[2];app=a.app.resolve();exe=app/'Contents/MacOS/zen-terminal'
if not exe.is_file():p.error('Expected separate Zen Terminal app')
spec=importlib.util.spec_from_file_location('owned_dialogs',Path(__file__).with_name('macos-test-dialogs.py'));axmodule=importlib.util.module_from_spec(spec);spec.loader.exec_module(axmodule)
run=root/'.terminal-test'/('native-dialogs-'+uuid.uuid4().hex[:8]);home=run/'home';profile=run/'profile';home.mkdir(parents=True);profile.mkdir()
folder_a=home/'Original project';folder_b=home/'Chosen project 雪';folder_a.mkdir();folder_b.mkdir()
proof=root/'docs/proof/2026-09-19';proof.mkdir(parents=True,exist_ok=True)
with net_socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
prefs={'marionette.port':port,'browser.shell.checkDefaultBrowser':False,'browser.startup.page':0,'browser.startup.homepage':'about:blank','zen.welcome-screen.seen':True,'browser.aboutwelcome.enabled':False,'app.update.disabledForTesting':True,'app.update.enabled':False,'privacy.userContext.enabled':True,'privacy.userContext.ui.enabled':True}
(profile/'user.js').write_text('\n'.join('user_pref(%s,%s);'%(json.dumps(k),json.dumps(v)) for k,v in prefs.items()))
env=dict(os.environ,MOZ_APP_DATA=str(home/'app-data'),MOZ_LOCAL_APP_DATA=str(home/'local-app-data'),HOME=str(home),ZDOTDIR=str(home),SHELL='/bin/zsh',MOZ_NO_REMOTE='1')
for key in list(env):
 if key.startswith(('XRE_PROFILE_','SELECTABLE_PROFILE_RESET_')) or key in {'XRE_RESTARTED_BY_PROFILE_MANAGER','MOZ_RESET_PROFILE_RESTART','MOZ_LEGACY_PROFILES'}:env.pop(key,None)
log=(run/'gecko.log').open('w');process=None;owned_pid=None;m=None;ax=None;results=[]
def js(code,values=None):return m.execute_script(code,script_args=values or [])
def wait(check,label,timeout=30):
 end=time.monotonic()+timeout;last=None
 while time.monotonic()<end:
  try:
   value=check()
   if value:return value
  except Exception as e:last=e
  time.sleep(.1)
 raise AssertionError('Timed out '+label+'; '+str(last))
def record(name,detail=True):results.append({'test':name,'result':'pass','detail':detail});print('PASS',name,detail,flush=True)
def deep(selector):return js('const find=root=>{const x=root.querySelector(arguments[0]);if(x)return x;for(const el of root.querySelectorAll("*")){if(el.shadowRoot){const found=find(el.shadowRoot);if(found)return found;}}return null;};return find(document);',[selector])
def identity():return js('return ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService.getPublicIdentities().find(x=>x.name==="Picker proof")?.userContextId;')
def screen(name):(proof/(a.label+'-'+name+'.png')).write_bytes(m.screenshot(format='binary'))
try:
 args=['-no-remote','-marionette','--remote-allow-system-access','-profile',str(profile)]
 if a.launch_services:
  command=['/usr/bin/open','-n','-a',str(app),'--stdout',str(run/'gecko.log'),'--stderr',str(run/'gecko.log')]
  for key in ['HOME','ZDOTDIR','MOZ_APP_DATA','MOZ_LOCAL_APP_DATA','MOZ_NO_REMOTE','SHELL']:command+=['--env',key+'='+env[key]]
  subprocess.run(command+['--args']+args,env=env,check=True)
 else:
  process=subprocess.Popen([str(exe)]+args,env=env,stdout=log,stderr=log)
 m=Marionette(host='127.0.0.1',port=port,socket_timeout=30,startup_timeout=30);m.raise_for_port(timeout=30);m.start_session();m.set_context('chrome')
 candidate_pid=js('return Services.appinfo.processID;')
 if process:assert candidate_pid==process.pid
 assert str(profile) in subprocess.check_output(['/bin/ps','-p',str(candidate_pid),'-o','command='],text=True)
 assert Path(js('return Services.dirsvc.get("ProfD",Ci.nsIFile).path;')).resolve()==profile.resolve()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 owned_pid=candidate_pid
 ax=axmodule.OwnedAppDialogs(owned_pid) # Read-only trust check; never requests permissions.
 wait(lambda:js('return Boolean(window.gZenTerminalTabs && gBrowserInit.delayedStartupFinished);'),'browser ready')
 ax.activate()
 record('Owned browser/profile confirmed; existing Accessibility trust used without permission changes')
 js('gBrowser.selectedTab=gBrowser.addTab("about:preferences#containers",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});')
 m.set_context('content')
 for handle in m.window_handles:
  m.switch_to_window(handle)
  if m.get_url().startswith('about:preferences'):break
 wait(lambda:deep('[data-l10n-id="containers-add-button2"]'),'Settings Add')
 wait(lambda:js('return document.readyState==="complete" && !!window.gSubDialog;'),'Settings initialized')
 time.sleep(.5)
 button=deep('[data-l10n-id="containers-add-button2"]');js('return arguments[0].shadowRoot?.querySelector("button")||arguments[0];',[button]).click()
 frame=wait(lambda:js('return [...document.querySelectorAll("browser.dialogFrame")].find(x=>x.contentDocument?.documentURI==="chrome://browser/content/preferences/dialogs/containers.xhtml");'),'native editor')
 m.execute_async_script('const done=arguments[arguments.length-1];arguments[0]._dialogReady.then(()=>done(true));',script_args=[frame]);m.switch_to_frame(frame)
 m.execute_async_script('const done=arguments[arguments.length-1];requestAnimationFrame(()=>requestAnimationFrame(()=>done(true)));')
 m.find_element('id','zen-container-kind-terminal').click()
 wait(lambda:js('return document.querySelector("moz-input-text[name=name]")?.shadowRoot?.querySelector("input");'),'name input').send_keys('Picker proof')
 m.find_element('id','zen-terminal-starting-directory').send_keys(str(folder_a))
 # Real macOS Cancel button, not a mocked nsIFilePicker callback.
 m.find_element('id','zen-terminal-choose-directory').click()
 time.sleep(.5)
 print('PICKER_FOCUSED_APPLICATION',subprocess.check_output(['/usr/bin/osascript','-l','JavaScript','-e','ObjC.import("AppKit"); var a=$.NSWorkspace.sharedWorkspace.frontmostApplication; JSON.stringify({pid:a.processIdentifier,bundle:ObjC.unwrap(a.bundleIdentifier)})'],text=True).strip(),flush=True)
 ax.activate()
 print('AFTER_ACTIVATION_FOCUSED_APPLICATION',subprocess.check_output(['/usr/bin/osascript','-l','JavaScript','-e','ObjC.import("AppKit"); var a=$.NSWorkspace.sharedWorkspace.frontmostApplication; JSON.stringify({pid:a.processIdentifier,bundle:ObjC.unwrap(a.bundleIdentifier)})'],text=True).strip(),flush=True)
 ax.press_dialog_button(['Cancel'],'Choose starting folder')
 wait(lambda:js('return !document.getElementById("zen-terminal-choose-directory").disabled;'),'picker cancelled')
 assert js('return document.getElementById("zen-terminal-starting-directory").value;')==str(folder_a)
 assert identity() is None
 record('Native picker Cancel preserves typed folder and creates no saved setup')
 m.find_element('id','zen-terminal-choose-directory').click()
 ax.enter_picker_folder(str(folder_b))
 ax.press_dialog_button(['Choose','Open','Select','Select Folder'],'Choose starting folder')
 wait(lambda:js('return document.getElementById("zen-terminal-starting-directory").value;')==str(folder_b),'real selected folder returns to input')
 assert identity() is None
 screen('chosen-folder')
 record('Native picker chooses a different Unicode folder without prematurely saving')
 js('document.querySelector("dialog").getButton("accept").click();');m.switch_to_frame();m.set_context('chrome')
 cid=wait(identity,'saved native setup')
 assert js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs").getTerminalContainerRecipe(arguments[0]).recipe.startingDirectory;',[cid])==str(folder_b)
 record('Actual Settings Save persists the folder returned by native picker')
 original=m.current_chrome_window_handle;handles=set(m.chrome_window_handles);js('OpenBrowserWindow({private:true});')
 private=wait(lambda:next(iter(set(m.chrome_window_handles)-handles),None),'private browser window');m.switch_to_window(private);m.set_context('chrome')
 wait(lambda:js('return Boolean(window.gZenTerminalTabs && gBrowserInit.delayedStartupFinished);'),'private window ready')
 assert js('return ChromeUtils.importESModule("resource://gre/modules/PrivateBrowsingUtils.sys.mjs").PrivateBrowsingUtils.isWindowPrivate(window);')
 before=js('return {records:Services.prefs.getStringPref("zen.terminal.sessions","{}"),tabs:gBrowser.tabs.length};')
 js('window.__privateResult="waiting";setTimeout(()=>{window.__privateResult=gZenTerminalTabs.openTerminalContainerTab(arguments[0]);},0);',[cid])
 body=wait(lambda:m.switch_to_alert().text,'private refusal message')
 assert 'shell history and files' in body and 'normal window' in body,body
 # Deliberately avoid WebDriver:AcceptAlert's close-notification wait. AXPress
 # still operates the actual visible enabled OK button; no response is forged.
 ax.press_dialog_button(['OK'],'shell history and files')
 wait(lambda:js('return window.__privateResult===null;'),'private refusal returns after real OK button')
 after=js('return {records:Services.prefs.getStringPref("zen.terminal.sessions","{}"),tabs:gBrowser.tabs.length};')
 assert before==after
 record('Actual private alert body and enabled OK button work; no tab or terminal job created',body)
 js('window.close();');m.switch_to_window(original);m.set_context('chrome')
except Exception as e:
 results.append({'test':'native dialogs','result':'fail','detail':str(e)});print('FAIL',repr(e),flush=True)
 if ax:
  try:
   tree=ax.tree();summary=[{k:n[k] for k in ['role','title','description','value','enabled']} for n in ax.flatten(tree) if n['role'] in {'AXApplication','AXMenuBar','AXWindow','AXSheet','AXDialog','AXButton','AXTextField','AXComboBox'}]
   (proof/(a.label+'-owned-dialog-tree.json')).write_text(json.dumps(summary,indent=2)+'\n')
  except Exception:pass
 if m:
  try:screen('failure')
  except Exception:pass
 raise
finally:
 if ax:ax.close()
 if m and owned_pid:
  try:m.switch_to_frame();m.set_context('chrome');js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);return true;')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:
   process.terminate()
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill();process.wait()
 if owned_pid and not process:
  for _ in range(100):
   try:os.kill(owned_pid,0)
   except ProcessLookupError:break
   time.sleep(.1)
  else:os.kill(owned_pid,15)
 log.close()
 (proof/(a.label+'-results.json')).write_text(json.dumps({'app':str(app),'test_data':'new synthetic profile/folders; AX restricted to launched browser PID','results':results,'log':str(run/'gecko.log')},indent=2)+'\n')
