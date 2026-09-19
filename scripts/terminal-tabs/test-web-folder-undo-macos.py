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
parser.add_argument('--child-last', action='store_true', help='Place nested child after parent web tab to exercise reverse closed-tab order')
parser.add_argument('--edge-case', choices=['all','empty','order','collision','workspace','restart','clear','disabled'], default='all')
parser.add_argument('--edges', action='store_true', help='Also exercise empty folders, ordering, ID collisions and removed workspace fallback')

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
def user_undo():
 action=m.actions.sequence('key','web-folder-edge-undo');action.key_down(Keys.META).key_down(Keys.SHIFT).key_down('t').key_up('t').key_up(Keys.SHIFT).key_up(Keys.META).perform();m.actions.release()
def edge_delete():
 folder_menu('edgeRoot','context_zenFolderDelete')
 wait(lambda:js('return !edgeRoot.isConnected;'),'actual edge folder Delete')
 snapshot=js('return {root:edgeRootId,lastGroup:SessionStore.getLastClosedTabGroupId(window),groups:SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false})};')
 (proof/(args.label+'-'+args.edge_case+'-edge-before-undo.json')).write_text(json.dumps(snapshot,indent=2)+'\n')
 print('EDGE CLOSED',json.dumps(snapshot),flush=True)
def edge_tab(marker):
 return wait(lambda:js('return gBrowser.tabs.find(t=>SessionStore.getCustomTabValue(t,"syntheticWebFolderProof")===arguments[0])||null;',[marker]),'edge restored receipt '+marker)
def edge_fixture(marker):
 js('window.edgeTab=gBrowser.addTab("data:text/html,<title>Edge proof</title>",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});SessionStore.setCustomTabValue(edgeTab,"syntheticWebFolderProof",arguments[0]);window.edgeRoot=gZenFolders.createFolder([edgeTab],{label:arguments[0],renameFolder:false});window.edgeRootId=edgeRoot.id;',[marker])
 wait(lambda:js('return edgeTab.linkedBrowser.currentURI.spec.startsWith("data:text/html,") && edgeTab.linkedBrowser.contentTitle==="Edge proof";'),'edge real page loaded before close')
 asyncjs('await gBrowser.TabStateFlusher.flush(edgeTab.linkedBrowser);return true;')
failure=None
try:
 start();assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 js('window.webUndoA=gBrowser.addTab("data:text/html,<title>Web parent proof</title>",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});window.webUndoB=gBrowser.addTab("data:text/html,<title>Web child proof</title>",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});SessionStore.setCustomTabValue(webUndoA,"syntheticWebFolderProof","parent");SessionStore.setCustomTabValue(webUndoB,"syntheticWebFolderProof","child");window.webUndoParent=gZenFolders.createFolder([webUndoA],{label:"Web-only parent",renameFolder:false});window.webUndoChild=gZenFolders.createFolder([webUndoB],{label:"Web-only child",renameFolder:false});webUndoParent.tabs[0].after(webUndoChild);webUndoParent.collapsed=false;webUndoChild.collapsed=false;')
 if args.child_last:js('webUndoParent.groupContainer.appendChild(webUndoChild);')
 assert js('return webUndoA.group===webUndoParent && webUndoB.group===webUndoChild && webUndoChild.group===webUndoParent;')
 wait(lambda:js('return [[webUndoA,"Web parent proof"],[webUndoB,"Web child proof"]].every(([t,title])=>t.linkedBrowser.currentURI.spec.startsWith("data:text/html,") && t.linkedBrowser.contentTitle===title);'),'both baseline real pages loaded before history flush')
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
 if args.edges:
  # Fixture construction is a method-level setup; Delete and Undo below are
  # actual visible menu/keyboard actions, not SessionStore restore calls.
  if args.edge_case in ('all','empty'):
   js('window.edgeRoot=gZenFolders.createFolder([],{label:"Empty parent",renameFolder:false});window.edgeChild=gZenFolders.createFolder([],{label:"Empty child",renameFolder:false});edgeRoot.tabs[0].after(edgeChild);window.edgeRootId=edgeRoot.id;window.edgeChildId=edgeChild.id;edgeRoot.collapsed=false;')
   edge_delete();user_undo()
   wait(lambda:js('const p=document.getElementById(edgeRootId),c=document.getElementById(edgeChildId);return p?.isZenFolder && c?.isZenFolder && c.group===p && p.tabs.every(t=>t.hasAttribute("zen-empty-tab"));'),'empty parent/child native Undo')
   record('Actual Delete and Cmd+Shift+T restore an empty parent with its empty child; only inert placeholders exist')
  if args.edge_case in ('all','order'):
   edge_fixture('ordered-first')
   js('window.edgeSurvivor=gZenFolders.createFolder([],{label:"Surviving neighbor",renameFolder:false});gZenWorkspaces.pinnedTabsContainer.firstElementChild.before(edgeRoot);edgeRoot.after(edgeSurvivor);')
   edge_delete();user_undo();edge_tab('ordered-first')
   assert js('const t=gBrowser.tabs.find(t=>SessionStore.getCustomTabValue(t,"syntheticWebFolderProof")==="ordered-first");return t.group?.isZenFolder && t.group.nextElementSibling===edgeSurvivor && t.group.parentElement.firstElementChild===t.group;'),'First-position root order changed'
   record('Actual Delete/Undo restores first root position before untouched surviving neighbor')
  if args.edge_case in ('all','collision'):
   edge_fixture('collision-original');edge_delete()
   js('window.edgeCollisionTab=gBrowser.addTab("data:text/html,<title>Collision neighbor</title>",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});window.edgeCollision=gZenFolders.createFolder([edgeCollisionTab],{label:"Must stay unchanged",renameFolder:false});edgeCollision.id=edgeRootId;window.edgeCollisionParent=edgeCollision.parentElement;')
   user_undo();edge_tab('collision-original')
   assert js('const t=gBrowser.tabs.find(t=>SessionStore.getCustomTabValue(t,"syntheticWebFolderProof")==="collision-original");return t.group?.isZenFolder && t.group!==edgeCollision && t.group.id!==edgeRootId && edgeCollision.isConnected && edgeCollisionTab.group===edgeCollision && edgeCollision.label==="Must stay unchanged" && edgeCollision.parentElement===edgeCollisionParent;'),'Undo consumed or changed existing colliding folder'
   record('Synthetic same-ID stress fixture: actual Undo remaps restored root and leaves preexisting folder/tab/label/parent unchanged')
  if args.edge_case in ('all','workspace'):
   original=js('return gZenWorkspaces.activeWorkspace;')
   removed=asyncjs('return await gZenWorkspaces.createAndSaveWorkspace("Removed folder workspace","briefcase");')
   edge_fixture('removed-workspace');edge_delete()
   asyncjs('await gZenWorkspaces.removeWorkspace(arguments[0]);return true;',[removed['uuid']])
   after_remove=js('const groups=SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false});return {lastGroup:SessionStore.getLastClosedTabGroupId(window),activeWorkspace:gZenWorkspaces.activeWorkspace,workspaceIds:gZenWorkspaces.getWorkspaces().map(w=>w.uuid),removedWorkspaceElementConnected:gZenWorkspaces.workspaceElement(arguments[0])?.isConnected ?? null,groups,prepared:groups.filter(g=>g.zenFolderState).map(g=>({id:g.id,prepared:gZenFolders.prepareClosedFolderState(g.zenFolderState,structuredClone(g.tabs.map(t=>t.state)))}))};',[removed['uuid']])
   (proof/(args.label+'-after-workspace-remove-before-undo.json')).write_text(json.dumps(after_remove,indent=2)+'\n');print('AFTER WORKSPACE REMOVE BEFORE UNDO',json.dumps(after_remove),flush=True)
   # Workspace removal is explicitly a native-method consequence case, not an
   # automated destructive confirmation. Real user Undo must still select the
   # folder transaction; if it does not, retain the failure for investigation.
   user_undo();edge_tab('removed-workspace')
   assert js('const t=gBrowser.tabs.find(t=>SessionStore.getCustomTabValue(t,"syntheticWebFolderProof")==="removed-workspace");return t.group?.isZenFolder && t.getAttribute("zen-workspace-id")===gZenWorkspaces.activeWorkspace && t.group.parentElement===gZenWorkspaces.pinnedTabsContainer && !gZenWorkspaces.getWorkspaces().some(w=>w.uuid===arguments[0]);',[removed['uuid']]),'Missing workspace did not restore visibly into active workspace'
   record('Native-method workspace removal followed by actual Undo restores folder into surviving active workspace')
  if args.edge_case in ('all','restart'):
   js('window.edgeRoot=gZenFolders.createFolder([],{label:"Empty restart parent",renameFolder:false});window.edgeChild=gZenFolders.createFolder([],{label:"Empty restart child",renameFolder:false});edgeRoot.tabs[0].after(edgeChild);window.edgeRootId=edgeRoot.id;window.edgeChildId=edgeChild.id;')
   restart_ids=js('return [edgeRootId,edgeChildId];')
   edge_delete()
   wait(lambda:js('return SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false}).some(g=>g.id===arguments[0] && g.zenFolderState?.emptyOnly);',[restart_ids[0]]),'empty transaction present before restart')
   asyncjs('await ChromeUtils.importESModule("moz-src:///browser/components/sessionstore/SessionSaver.sys.mjs").SessionSaver.run();return true;')
   try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
   except Exception:pass
   process.wait(timeout=20);m=None
   start()
   wait(lambda:js('return SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false}).some(g=>g.id===arguments[0] && g.zenFolderState?.emptyOnly);',[restart_ids[0]]),'serialized empty transaction recovered')
   user_undo()
   wait(lambda:js('const p=document.getElementById(arguments[0]),c=document.getElementById(arguments[1]);return p?.isZenFolder && c?.isZenFolder && c.group===p && p.tabs.every(t=>t.hasAttribute("zen-empty-tab"));',restart_ids),'actual shortcut restores empty subtree after own-app restart')
   record('Actual clean quit/relaunch of same synthetic profile preserves empty nested folder history and user Undo')
  if args.edge_case in ('all','clear'):
   js('window.edgeRoot=gZenFolders.createFolder([],{label:"Empty clear-history",renameFolder:false});window.edgeRootId=edgeRoot.id;')
   clear_id=js('return edgeRootId;');edge_delete()
   assert js('return SessionStore.lastClosedActions.length>0;')
   js('Services.obs.notifyObservers(null,"browser:purge-session-history");')
   wait(lambda:js('return SessionStore.lastClosedActions.length===0 && SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false}).length===0;'),'real session-history purge removes empty records and actions')
   user_undo();time.sleep(.3)
   assert js('return !document.getElementById(arguments[0]);',[clear_id])
   record('Real session-history clear notification removes empty folder action; subsequent user Undo does not restore it (not Settings UI proof)')
  if args.edge_case in ('all','disabled'):
   js('window.edgeRoot=gZenFolders.createFolder([],{label:"Empty limit-change",renameFolder:false});window.edgeRootId=edgeRoot.id;')
   edge_delete()
   js('Services.prefs.setIntPref("browser.sessionstore.max_tabs_undo",0);')
   wait(lambda:js('return !SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false}).some(g=>g.zenEmptyClosedId!==undefined);'),'disabling history removes existing empty records')
   js('window.edgeRoot=gZenFolders.createFolder([],{label:"Empty history-disabled",renameFolder:false});window.edgeRootId=edgeRoot.id;')
   disabled_id=js('return edgeRootId;');edge_delete();user_undo();time.sleep(.3)
   assert js('return !document.getElementById(arguments[0]) && !SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false}).some(g=>g.id===arguments[0]);',[disabled_id])
   record('Actual zero history preference prunes existing empty records and prevents new empty folder Undo (preference method, not Settings UI)')
except Exception as exc:
 failure=str(exc);print('FAIL',repr(exc),flush=True)
 if m:
  try:
   detail=js('return {activeWorkspace:gZenWorkspaces.activeWorkspace,lastGroup:SessionStore.getLastClosedTabGroupId(window),groups:SessionStore.getClosedTabGroups({sourceWindow:window,closedTabsFromAllWindows:true,closedTabsFromClosedWindows:false}),folders:[...document.querySelectorAll("zen-folder")].map(f=>({id:f.id,name:f.label,parent:f.group?.id,tabs:f.tabs.map(t=>({id:t.id,empty:t.hasAttribute("zen-empty-tab"),workspace:t.getAttribute("zen-workspace-id")}))}))};')
   (proof/(args.label+'-failure-state.json')).write_text(json.dumps(detail,indent=2)+'\n')
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
 log.close()
 (proof/(args.label+'-results.json')).write_text(json.dumps({'app':str(args.app),'results':results,'failure':failure,'run':str(run),'scope':'ordinary web tabs only, actual folder Delete and Cmd+Shift+T; no terminal jobs'},indent=2)+'\n')
