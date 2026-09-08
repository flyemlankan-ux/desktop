#!/usr/bin/env python3
"""Reproduce mixed-folder behavior in the actual app with disposable data.
Uses native browser methods, not pointer drag/drop: diagnostic, NOT UI acceptance.
Currently expected to fail against the September8 installed development build.
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
proof=root/'docs/proof/2026-09-08-product-audit';proof.mkdir(parents=True,exist_ok=True)
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
try:
 start()
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 js('const service=ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService; const store=ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs");const identity=service.getPublicIdentities().find(x=>store.isTerminalContainerId(x.userContextId));window.auditTerminal=gZenTerminalTabs.openTerminalContainerTab(identity.userContextId);')
 wait(lambda:terminal_status() and 'ready' in terminal_status(),'live synthetic terminal')
 sid=js('return window.auditTerminal.getAttribute("zen-terminal-session-id");');test_sessions.append(sid)
 time.sleep(2)
 js('window.auditWeb=gBrowser.addTab("about:blank",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});window.auditFolder=gZenFolders.createFolder([window.auditWeb,window.auditTerminal],{name:"Mixed project audit"});')
 def state():return js('return {terminalPinned:window.auditTerminal.pinned,webPinned:window.auditWeb.pinned,terminalInFolder:window.auditTerminal.group===window.auditFolder,webInFolder:window.auditWeb.group===window.auditFolder,terminalSelected:gBrowser.selectedTab===window.auditTerminal};')
 before=state();print('BEFORE',before,flush=True)
 js('gBrowser.selectedTab=window.auditWeb;');time.sleep(.2)
 js('gBrowser.selectedTab=window.auditTerminal;');time.sleep(2)
 after=state();print('AFTER',after,flush=True);screen('mixed-folder-after-select')
 report={'app':str(args.app),'scope':'Native browser-method diagnostic on synthetic data, NOT drag-and-drop UI acceptance','before':before,'after':after,'shellStillAlive':tmux('has-session','-t','=zt_'+sid).returncode==0}
 (proof/'mixed-folder-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
 if not after['terminalInFolder'] or not after['terminalPinned']:
  raise AssertionError('Selecting a terminal undoes native folder membership/pinning')
finally:
 if m:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 for sid in test_sessions:tmux('kill-session','-t','=zt_'+sid)
 log.close()
