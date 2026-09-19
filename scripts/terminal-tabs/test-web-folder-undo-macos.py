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
parser.add_argument('--label', default='web-only-folder-undo')

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
failure=None
try:
 start();assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 js('window.webUndoA=gBrowser.addTab("data:text/html,<title>Web parent proof</title>",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});window.webUndoB=gBrowser.addTab("data:text/html,<title>Web child proof</title>",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});SessionStore.setCustomTabValue(webUndoA,"syntheticWebFolderProof","parent");SessionStore.setCustomTabValue(webUndoB,"syntheticWebFolderProof","child");window.webUndoParent=gZenFolders.createFolder([webUndoA],{label:"Web-only parent",renameFolder:false});window.webUndoChild=gZenFolders.createFolder([webUndoB],{label:"Web-only child",renameFolder:false});webUndoParent.tabs[0].after(webUndoChild);webUndoParent.collapsed=false;webUndoChild.collapsed=false;')
 assert js('return webUndoA.group===webUndoParent && webUndoB.group===webUndoChild && webUndoChild.group===webUndoParent;')
 asyncjs('await Promise.all([webUndoA,webUndoB].map(t=>gBrowser.TabStateFlusher.flush(t.linkedBrowser)));return true;')
 record('Web-only nested folder setup uses native method fixture; zero terminal jobs created')
 folder_menu('webUndoParent','context_zenFolderDelete')
 wait(lambda:js('return !webUndoA.isConnected && !webUndoB.isConnected && !webUndoParent.isConnected;'),'actual web-only folder Delete')
 record('Actual parent-folder Delete closes nested ordinary web tabs')
 closed=js('return {lastGroup:SessionStore.getLastClosedTabGroupId(window),groups:SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false}).map(g=>({id:g.id,name:g.name,tabs:g.tabs.map(t=>({groupId:t.state.groupId,pinned:t.state.pinned,marker:t.state.extData?.syntheticWebFolderProof}))}))};')
 (proof/(args.label+'-before-undo.json')).write_text(json.dumps(closed,indent=2)+'\n');print('CLOSED WEB GROUPS',json.dumps(closed),flush=True)
 action=m.actions.sequence('key','web-folder-user-undo');action.key_down(Keys.META).key_down(Keys.SHIFT).key_down('t').key_up('t').key_up(Keys.SHIFT).key_up(Keys.META).perform();m.actions.release()
 wait(lambda:js('window.webRestoredA=gBrowser.tabs.find(t=>SessionStore.getCustomTabValue(t,"syntheticWebFolderProof")==="parent");window.webRestoredB=gBrowser.tabs.find(t=>SessionStore.getCustomTabValue(t,"syntheticWebFolderProof")==="child");return !!webRestoredA && !!webRestoredB;'),'actual shortcut restores both ordinary web tab receipts')
 state=js('return {parentGroup:webRestoredA.group?.id,parentIsZenFolder:!!webRestoredA.group?.isZenFolder,childGroup:webRestoredB.group?.id,childIsZenFolder:!!webRestoredB.group?.isZenFolder,nested:!!webRestoredB.group && webRestoredB.group.group===webRestoredA.group,groups:gBrowser.tabGroups.map(g=>({id:g.id,tag:g.localName,isZenFolder:!!g.isZenFolder,parent:g.group?.id}))};')
 (proof/(args.label+'-after-undo.json')).write_text(json.dumps(state,indent=2)+'\n');print('RESTORED WEB STRUCTURE',json.dumps(state),flush=True)
 record('Actual Cmd+Shift+T restores both ordinary web tab receipts')
 assert state['parentIsZenFolder'] and state['childIsZenFolder'] and state['nested'],'Web-only user Undo lost nested Zen folder structure'
 record('Web-only user Undo restores actual nested Zen folder structure')
except Exception as exc:
 failure=str(exc);print('FAIL',repr(exc),flush=True);raise
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
 log.close()
 (proof/(args.label+'-results.json')).write_text(json.dumps({'app':str(args.app),'results':results,'failure':failure,'run':str(run),'scope':'ordinary web tabs only, actual folder Delete and Cmd+Shift+T; no terminal jobs'},indent=2)+'\n')
