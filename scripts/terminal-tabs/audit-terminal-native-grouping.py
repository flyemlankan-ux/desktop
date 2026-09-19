#!/usr/bin/env python3
"""Reproduce mixed-folder behavior in the actual app with disposable data.
Uses native browser methods, not pointer drag/drop: diagnostic, NOT UI acceptance.
Checks folder selection, pin/unpin, Essentials, and grouped restart preservation.
Still NOT pointer drag/drop or complete workspace/split acceptance.
"""
import argparse, json, os, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.keys import Keys

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='packaged')
parser.add_argument('--cli-smoke', action='append', default=[], type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
run=root/'.terminal-test'/('mac-'+uuid.uuid4().hex[:8]);run.mkdir(parents=True)
proof=root/'docs/proof/2026-09-19';proof.mkdir(parents=True,exist_ok=True)
home=run/'home';home.mkdir();profile=run/'profile';profile.mkdir()
(home/'.zshenv').write_text('export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n')
with net_socket.socket() as listener:
 listener.bind(('127.0.0.1',0));marionette_port=listener.getsockname()[1]
prefs={'marionette.port':marionette_port,'browser.shell.checkDefaultBrowser':False,'browser.startup.page':3,'zen.welcome-screen.seen':True,'app.update.disabledForTesting':True,'app.update.auto':False,'app.update.enabled':False,'browser.startup.homepage':'about:blank','browser.aboutwelcome.enabled':False,'browser.sessionstore.resume_from_crash':True,'privacy.userContext.enabled':True,'privacy.userContext.ui.enabled':True,'zen.workspaces.separate-essentials':True}
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
 try:
  detail=js('return {selected:gBrowser.selectedTab?.id,terminal:window.auditTerminal?.id,uri:window.auditTerminal?.linkedBrowser?.currentURI?.spec,selectedUri:gBrowser.selectedBrowser?.currentURI?.spec,status:window.auditTerminal?.linkedBrowser?.contentDocument?.getElementById("zen-terminal-status-text")?.textContent,selectedStatus:gBrowser.selectedBrowser?.contentDocument?.getElementById("zen-terminal-status-text")?.textContent,pending:window.auditTerminal?.hasAttribute("pending"),sid:window.auditTerminal?.getAttribute("zen-terminal-session-id"),initial:window.auditTerminal?._zenPinnedInitialState,state:window.auditTerminal?JSON.parse(SessionStore.getTabState(window.auditTerminal)):null,terminalPrefs:Services.prefs.getChildList("zen.terminal.").filter(k=>k.includes("session")).map(k=>[k,Services.prefs.getStringPref(k,"")])};')
  detail['tmux']=tmux('list-sessions','-F','#{session_name}:#{session_windows}').stdout if socket else None
  print('TIMEOUT DETAIL',json.dumps(detail),flush=True)
  (proof/(args.label+'-organization-timeout.json')).write_text(json.dumps(detail,indent=2)+'\n')
 except Exception as diagnostic_error:print('Diagnostic failed',repr(diagnostic_error),flush=True)
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
def terminal_ready():return js('return Boolean(gBrowser.selectedBrowser.contentDocument?.getElementById("zen-terminal-surface")?.hasAttribute("terminal-ready"));')
def tmux(*args):return subprocess.run(['/opt/homebrew/bin/tmux','-L',socket,*args],capture_output=True,text=True,timeout=5)
def screen(name):
 m.set_context('chrome');(proof/(args.label+'-'+name+'.png')).write_bytes(m.screenshot(format='binary'))
def restart_and_recover_tabs(sid):
 global m
 try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
 except Exception:pass
 process.wait(timeout=20);m=None
 start()
 wait(lambda:js('return [...gBrowser.tabs].some(t=>t.getAttribute("zen-terminal-session-id")===arguments[0]);',[sid]),'restored terminal marker')
 js('window.auditTerminal=[...gBrowser.tabs].find(t=>t.getAttribute("zen-terminal-session-id")===arguments[0]);window.auditWeb=[...gBrowser.tabs].find(t=>SessionStore.getCustomTabValue(t,"terminalOrganizationProofWeb")==="true");window.auditFolder=window.auditTerminal.group;',[sid])
 assert js('return Boolean(auditTerminal && auditWeb);')
try:
 start()
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 js('const service=ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService; const store=ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs");const identity=service.getPublicIdentities().find(x=>store.isTerminalContainerId(x.userContextId));window.auditTerminal=gZenTerminalTabs.openTerminalContainerTab(identity.userContextId);')
 wait(terminal_ready,'live synthetic terminal')
 sid=js('return window.auditTerminal.getAttribute("zen-terminal-session-id");');test_sessions.append(sid)
 time.sleep(2)
 js('window.auditWeb=gBrowser.addTab("about:blank",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});SessionStore.setCustomTabValue(window.auditWeb,"terminalOrganizationProofWeb","true");window.auditFolder=gZenFolders.createFolder([window.auditWeb,window.auditTerminal],{name:"Mixed project audit"});')
 def state():return js('return {terminalPinned:window.auditTerminal.pinned,webPinned:window.auditWeb.pinned,terminalInFolder:window.auditTerminal.group===window.auditFolder,webInFolder:window.auditWeb.group===window.auditFolder,terminalSelected:gBrowser.selectedTab===window.auditTerminal};')
 before=state();print('BEFORE',before,flush=True)
 wait(lambda:tmux('has-session','-t','=zt_'+sid).returncode==0,'tmux-backed terminal exists (not unsaved fallback)')
 shell_result=tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}');assert shell_result.returncode==0,shell_result.stderr
 shell_pid=shell_result.stdout.strip();assert shell_pid
 js('gBrowser.selectedTab=window.auditWeb;');time.sleep(.2)
 js('gBrowser.selectedTab=window.auditTerminal;');time.sleep(2)
 after=state();print('AFTER',after,flush=True);screen('mixed-folder-after-select')
 report={'app':str(args.app),'scope':'Native browser-method diagnostic on synthetic data, NOT drag-and-drop UI acceptance','before':before,'after':after,'shellStillAlive':tmux('has-session','-t','=zt_'+sid).returncode==0}
 (proof/'mixed-folder-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
 if not after['terminalInFolder'] or not after['terminalPinned']:
  raise AssertionError('Selecting a terminal undoes native folder membership/pinning')
 record('mixed folder survives selection',after)
 # Direct native methods diagnose integration; pointer-driven proof is separate.
 js('gBrowser.unpinTab(window.auditTerminal);');time.sleep(2)
 assert not js('return window.auditTerminal.pinned;')
 record('intentional unpin stays unpinned')
 js('gBrowser.pinTab(window.auditTerminal);gBrowser.selectedTab=window.auditWeb;gBrowser.selectedTab=window.auditTerminal;');time.sleep(2)
 assert js('return window.auditTerminal.pinned;')
 record('intentional pin survives selection')
 essential_before=js('return {allowed:gZenPinnedTabManager.canEssentialBeAdded(auditTerminal),separate:gZenWorkspaces.containerSpecificEssentials,tabContainer:auditTerminal.getAttribute("usercontextid"),workspaceContainer:gZenWorkspaces.getActiveWorkspaceFromCache().containerTabId,max:gZenPinnedTabManager.maxEssentialTabs,count:gBrowser._numZenEssentials};')
 print('ESSENTIAL BEFORE',essential_before,flush=True)
 essential_added=js('const added=gZenPinnedTabManager.addToEssentials(auditTerminal);return {added,marked:auditTerminal.hasAttribute("zen-essential"),parent:auditTerminal.parentElement?.className};')
 print('ESSENTIAL ADD',essential_added,flush=True)
 assert essential_before['separate'] and not essential_before['allowed'],essential_before
 assert str(essential_before['tabContainer'])!=str(essential_before['workspaceContainer'] or 0)
 assert not essential_added['added'] and not essential_added['marked'],essential_added
 record('native separate-container Essentials refusal is preserved',{'before':essential_before,'added':essential_added})
 # The native Settings preference requires browser restart; never bypass its
 # eligibility test with replicating=true or by mutating manager fields.
 js('Services.prefs.setBoolPref("zen.workspaces.separate-essentials",false);')
 prefs['zen.workspaces.separate-essentials']=False
 (profile/'user.js').write_text('\n'.join('user_pref(%s, %s);'%(json.dumps(k),json.dumps(v)) for k,v in prefs.items()))
 restart_and_recover_tabs(sid)
 shared=js('return {preference:Services.prefs.getBoolPref("zen.workspaces.separate-essentials"),activeMode:gZenWorkspaces.containerSpecificEssentials,allowed:gZenPinnedTabManager.canEssentialBeAdded(auditTerminal)};')
 assert shared=={'preference':False,'activeMode':False,'allowed':True},shared
 record('synthetic native preference changed to shared Essentials and restarted',shared)
 assert js('return gZenPinnedTabManager.addToEssentials(auditTerminal);')
 js('gBrowser.selectedTab=window.auditWeb;gBrowser.selectedTab=window.auditTerminal;');time.sleep(2)
 assert js('return auditTerminal.hasAttribute("zen-essential");')
 record('shared Essential survives selection')
 restart_and_recover_tabs(sid)
 assert js('return auditTerminal.hasAttribute("zen-essential") && auditTerminal.pinned;')
 js('gBrowser.selectedTab=auditTerminal;')
 wait(terminal_ready,'restored Essential terminal ready')
 assert tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}').stdout.strip()==shell_pid
 record('shared Essential survives restart with same shell')
 js('gZenPinnedTabManager.removeEssentials(window.auditTerminal);window.auditFolder=gZenFolders.createFolder([window.auditWeb,window.auditTerminal],{name:"Mixed project restart"});window.auditFolder.collapsed=true;window.auditFolder.collapsed=false;gBrowser.selectedTab=window.auditWeb;')
 time.sleep(2)
 assert state()['terminalInFolder']
 record('regroup and collapse preserve membership')
 decoration=js('auditTerminal.setAttribute("zen-pinned-changed","true");auditTerminal.setAttribute("had-zen-pinned-changed","true");const marked=auditTerminal.hasAttribute("zen-terminal-tab");gZenPinnedTabManager.pinHasChangedUrl(auditTerminal);return {marked,uri:auditTerminal.linkedBrowser.currentURI.spec,changed:auditTerminal.hasAttribute("zen-pinned-changed"),hadChanged:auditTerminal.hasAttribute("had-zen-pinned-changed"),guard:gZenPinnedTabManager.pinHasChangedUrl.toString().includes("zen-terminal-tab")};')
 print('DECORATION',decoration,flush=True)
 assert not decoration['changed'] and not decoration['hadChanged'],decoration
 record('pin URL reset decoration stays suppressed')
 restart_and_recover_tabs(sid)
 assert js('return Boolean(window.auditFolder && window.auditWeb && window.auditTerminal.pinned);')
 js('gBrowser.selectedTab=window.auditTerminal;');time.sleep(2)
 wait(terminal_ready,'restored live terminal')
 assert state()['terminalInFolder']
 assert tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}').stdout.strip()==shell_pid
 record('grouped restart retains membership and same shell')
 screen('native-organization-restart')
 (proof/(args.label+'-native-organization.json')).write_text(json.dumps({'app':str(args.app),'scope':'Native method integration, not pointer drag/drop acceptance','results':results},indent=2)+'\n')
finally:
 if m:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 for sid in test_sessions:tmux('kill-session','-t','=zt_'+sid)
 log.close()
