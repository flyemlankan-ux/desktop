#!/usr/bin/env python3
"""Native mixed nested folder / workspace destructive-action journey.
Synthetic jobs only; menu cases and direct-method cases are labelled separately.
"""
import argparse, json, os, shlex, socket as net_socket, subprocess, time, uuid
from marionette_driver.keys import Keys
from pathlib import Path
from marionette_driver.marionette import Marionette

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='native-folder-lifecycle')

args=parser.parse_args()
if not args.label.replace('-', '').replace('_', '').isalnum():parser.error('label must contain letters, digits, hyphens or underscores')
root=Path(__file__).resolve().parents[2]
run=root/'.terminal-test'/('mac-'+uuid.uuid4().hex[:8]);run.mkdir(parents=True)
proof=root/'docs/proof/2026-09-19';proof.mkdir(parents=True,exist_ok=True)
if (proof/(args.label+'-results.json')).exists():parser.error('Use a new proof label; preserve existing evidence')
home=run/'home';home.mkdir();profile=run/'profile';profile.mkdir()
(home/'.zshenv').write_text('export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n')
with net_socket.socket() as listener:
 listener.bind(('127.0.0.1',0));marionette_port=listener.getsockname()[1]
prefs={'marionette.port':marionette_port,'browser.shell.checkDefaultBrowser':False,'browser.startup.page':3,'zen.welcome-screen.seen':True,'app.update.disabledForTesting':True,'app.update.auto':False,'app.update.enabled':False,'browser.startup.homepage':'about:blank','browser.aboutwelcome.enabled':False,'browser.sessionstore.resume_from_crash':True,'privacy.userContext.enabled':True,'privacy.userContext.ui.enabled':True,'ui.prefersReducedMotion':1,'zen.view.sidebar-expanded':True}
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
def exists(sid):return tmux('has-session','-t','=zt_'+sid).returncode==0
def asyncjs(code,values=None):
 value=m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{'+code+'})().then(value=>done({value}),error=>done({error:String(error)}));',script_args=values or [])
 assert 'error' not in value,value.get('error');return value.get('value')
def open_job(owner,key):
 sid=js('window[arguments[1]]=gZenTerminalTabs.openTerminalContainerTab(arguments[0]);return window[arguments[1]].getAttribute("zen-terminal-session-id");',[owner,key]);test_sessions.append(sid)
 wait(lambda:js('return window[arguments[0]].linkedBrowser.contentDocument?.getElementById("zen-terminal-surface")?.hasAttribute("terminal-ready");',[key]),'terminal '+key)
 wait(lambda:exists(sid),'actual job '+key);return sid
def right_click(element):
 rect=js('arguments[0].scrollIntoView({block:"center"});const r=arguments[0].getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};',[element])
 m.actions.sequence('pointer','folder-menu',{'pointerType':'mouse'}).pointer_move(int(rect['x']),int(rect['y'])).pointer_down(button=2).pointer_up(button=2).perform();m.actions.release()
def folder_menu(folder_key,item_id):
 element=js('return window[arguments[0]].labelElement;',[folder_key]);right_click(element)
 wait(lambda:js('return document.getElementById("zenFolderActions").state==="open";'),'real folder context menu')
 item=m.find_element('id',item_id);assert item.is_displayed() and item.is_enabled();item.click()
def finish_rename(name):
 field=wait(lambda:m.find_element('id','tab-label-input'),'native inline rename input')
 field.send_keys(Keys.META+'a'+Keys.NULL);field.send_keys(name);field.send_keys(Keys.ENTER)
 wait(lambda:js('return !document.getElementById("tab-label-input");'),'rename committed')
marker=home/'setup-run-count'
def runs():return len(marker.read_text().splitlines()) if marker.exists() else 0
failure=None
try:
 start();assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 owner=js('const cis=ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService;const id=cis.create("Folder lifecycle proof","briefcase","purple");ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs").setTerminalContainerRecipe(id.userContextId,{recipe:{steps:[{command:arguments[0]}]}});return id.userContextId;',["printf 'run\\n' >> "+shlex.quote(str(marker))])
 # Neighbor stays in the original workspace and uses the same saved setup.
 # Cleanup must follow exact job ownership, not merely the container identity.
 original_workspace=js('return gZenWorkspaces.activeWorkspace;')
 neighbor=open_job(owner,'folderNeighbor');wait(lambda:runs()==1,'neighbor startup once')
 workspace=asyncjs('return await gZenWorkspaces.createAndSaveWorkspace("Disposable project","briefcase");')
 first=open_job(owner,'folderFirst');second=open_job(owner,'folderSecond');wait(lambda:runs()==3,'three startup commands once')
 js('window.folderWebA=gBrowser.addTab("data:text/html,<title>Parent web</title>",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});window.folderWebB=gBrowser.addTab("data:text/html,<title>Nested web</title>",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});window.folderParent=gZenFolders.createFolder([folderWebA,folderFirst],{label:"Parent project",renameFolder:false});window.folderChild=gZenFolders.createFolder([folderWebB,folderSecond],{label:"Nested project",renameFolder:false});folderParent.tabs[0].after(folderChild);folderParent.collapsed=false;folderChild.collapsed=false;')
 assert js('return folderChild.group===folderParent && folderFirst.group===folderParent && folderSecond.group===folderChild && folderWebA.group===folderParent && folderWebB.group===folderChild;')
 assert all(exists(sid) for sid in [first,second,neighbor]) and runs()==3
 record('Native-method setup: two mixed folders nested using the same placement as upstream folder test; three jobs unchanged',{'pointer_drag_proved':False})
 folder_menu('folderParent','context_zenFolderRename');finish_rename('Renamed project')
 assert js('return folderParent.label==="Renamed project";')
 assert all(exists(sid) for sid in [first,second,neighbor]) and runs()==3
 record('Actual folder context-menu Rename and inline input preserve both nested jobs')
 # Actual workspace menu and inline rename; opening the menu uses its native
 # openPopup method, so this is not claimed as pointer workspace-menu discovery.
 js('document.getElementById("zenWorkspaceMoreActions").openPopup(gZenWorkspaces.activeWorkspaceIndicator,"after_start");')
 item=wait(lambda:m.find_element('id','context_zenEditWorkspace'),'workspace Rename item');wait(item.is_displayed,'workspace Rename visible');item.click();finish_rename('Renamed workspace')
 assert js('return gZenWorkspaces.getWorkspaceFromId(arguments[0]).name==="Renamed workspace";',[workspace['uuid']])
 assert all(exists(sid) for sid in [first,second,neighbor]) and runs()==3
 record('Actual workspace menu item and inline rename preserve jobs; popup opened by native method')
 parent_id=js('return folderParent.id;')
 asyncjs('await Promise.all([folderFirst,folderSecond,folderWebA,folderWebB].map(t=>gBrowser.TabStateFlusher.flush(t.linkedBrowser)));return true;')
 folder_menu('folderParent','context_zenFolderDelete')
 wait(lambda:js('return !folderParent.isConnected && !folderFirst.isConnected && !folderSecond.isConnected && !folderWebA.isConnected && !folderWebB.isConnected;'),'actual recursive folder removal')
 wait(lambda:not exists(first) and not exists(second),'only closed folder jobs stopped')
 assert exists(neighbor) and runs()==3
 record('Actual parent-folder Delete closes nested web/terminal tabs and stops only their exact jobs; same-setup neighbor survives')
 # Capture the actual closed transaction before normal user Undo consumes it.
 closed_state=js('return {parent:arguments[0],lastGroup:SessionStore.getLastClosedTabGroupId(window),lastCount:SessionStore.getLastClosedTabCount(window),groups:SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false}).map(g=>({id:g.id,name:g.name,tabs:g.tabs.map(t=>({groupId:t.state.groupId,pinned:t.state.pinned,zenIsEmpty:t.state.zenIsEmpty,closedInTabGroupId:t.closedInTabGroupId,terminalOwnership:t.state.extData?.zenTerminalOwnership,terminalSession:t.state.extData?.zenTerminalSessionId}))}))};',[parent_id])
 (proof/(args.label+'-before-undo.json')).write_text(json.dumps(closed_state,indent=2)+'\n')
 print('CLOSED FOLDER TRANSACTION',json.dumps(closed_state),flush=True)
 # Firefox156's user shortcut routes through SessionWindowUI. Do not assume
 # the last closed transaction equals the parent group id picked by the test.
 action=m.actions.sequence('key','folder-user-undo')
 action.key_down(Keys.META).key_down(Keys.SHIFT).key_down('t').key_up('t').key_up(Keys.SHIFT).key_up(Keys.META).perform();m.actions.release()
 wait(lambda:js('const find=id=>gBrowser.tabs.find(t=>{try{return JSON.parse(SessionStore.getCustomTabValue(t,"zenTerminalOwnership")).id===id;}catch(_){return false;}});window.folderRestoredFirst=find(arguments[0]);window.folderRestoredSecond=find(arguments[1]);return !!folderRestoredFirst && !!folderRestoredSecond;',[first,second]),'actual Cmd+Shift+T restores both terminal tabs')
 for key in ['folderRestoredFirst','folderRestoredSecond']:
  js('gBrowser.selectedTab=window[arguments[0]];',[key])
  wait(lambda:js('const d=window[arguments[0]].linkedBrowser.contentDocument;return d?.getElementById("zen-terminal-status-text")?.textContent.includes("ended") && d.getElementById("zen-terminal-reconnect")?.textContent==="Start again";',[key]),'Undo shows ended session with explicit Start again')
 assert not exists(first) and not exists(second) and exists(neighbor) and runs()==3
 record('Actual user Undo restores both terminal receipts; loading each shows ended/Start again without rerunning setup')
 assert js('return folderRestoredFirst.group?.isZenFolder && folderRestoredSecond.group?.isZenFolder && folderRestoredSecond.group.group===folderRestoredFirst.group;'),'Native Undo lost the nested Zen folder structure'
 record('Actual Cmd+Shift+T Undo restores nested organization but never silently restarts either closed terminal')
 js('gBrowser.selectedTab=folderRestoredFirst;')
 # Each top-level terminal has a separate WebDriver content handle.
 target_url=js('return folderRestoredFirst.linkedBrowser.currentURI.spec;')
 chrome_handle=m.current_chrome_window_handle
 try:
  m.set_context('content')
  matched=False
  for handle in m.window_handles:
   m.switch_to_window(handle)
   if m.execute_script('return document.documentURI;')==target_url:
    matched=True;break
  assert matched,'Restored terminal content handle not found'
  button=m.find_element('id','zen-terminal-reconnect')
  assert button.is_displayed() and button.is_enabled()
  button.click()
 finally:
  m.set_context('chrome');m.switch_to_window(chrome_handle)

 wait(lambda:js('return folderRestoredFirst.linkedBrowser.contentDocument.getElementById("zen-terminal-surface").hasAttribute("terminal-ready");'),'explicit restart ready')
 restarted=js('return folderRestoredFirst.getAttribute("zen-terminal-session-id");');test_sessions.append(restarted)
 wait(lambda:runs()==4 and exists(restarted),'one explicitly requested new job')
 assert not exists(second) and exists(neighbor)
 record('Actual Start again button runs exactly one setup; untouched restored tab remains ended')
 # Avoid mocking or auto-accepting the native destructive confirmation. This
 # case directly tests the real removeWorkspace implementation and consequences.
 asyncjs('await gZenWorkspaces.removeWorkspace(arguments[0]);return true;',[workspace['uuid']])
 wait(lambda:not exists(restarted),'workspace-owned restarted job stopped')
 assert exists(neighbor) and runs()==4
 assert js('return !gZenWorkspaces.getWorkspaces().some(w=>w.uuid===arguments[0]) && gZenWorkspaces.getWorkspaces().some(w=>w.uuid===arguments[1]) && folderNeighbor.isConnected;',[workspace['uuid'],original_workspace])
 record('Native-method workspace deletion stops its job and preserves neighboring workspace/job; confirmation UI not exercised')
except Exception as exc:
 failure=str(exc);print('FAIL',repr(exc),flush=True)
 if m:
  try:
   state=js('return {lastGroup:SessionStore.getLastClosedTabGroupId(window),folders:[...document.querySelectorAll("zen-folder")].map(g=>({id:g.id,label:g.label,parent:g.group?.id})),groups:gBrowser.tabGroups.map(g=>({id:g.id,tag:g.localName,isZenFolder:!!g.isZenFolder,parent:g.group?.id})),tabs:gBrowser.tabs.map(t=>({id:t.id,group:t.group?.id,session:t.getAttribute("zen-terminal-session-id"),pending:t.hasAttribute("pending"),uri:t.linkedBrowser.currentURI.spec,status:t.linkedBrowser.contentDocument?.getElementById("zen-terminal-status-text")?.textContent,ownership:SessionStore.getCustomTabValue(t,"zenTerminalOwnership")}))};')
   (proof/(args.label+'-failure-state.json')).write_text(json.dumps(state,indent=2)+'\n')
   (proof/(args.label+'-failure.png')).write_bytes(m.screenshot(format='binary'))
  except Exception:pass
 raise
finally:
 if m:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:
   process.terminate()
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill();process.wait()
 if socket:
  for sid in set(test_sessions):tmux('kill-session','-t','=zt_'+sid)
 log.close()
 (proof/(args.label+'-results.json')).write_text(json.dumps({'app':str(args.app),'results':results,'failure':failure,'run':str(run),'scope':'synthetic native menu cases and explicitly labelled native-method cases; no pointer drag or confirmation acceptance claim'},indent=2)+'\n')
