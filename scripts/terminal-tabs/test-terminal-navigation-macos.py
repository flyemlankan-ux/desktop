#!/usr/bin/env python3
"""Native navigation-away and Return to terminal journeys in synthetic data.
Uses real address-bar typing, browser controls and notification-button clicks.
"""
import argparse, json, os, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.keys import Keys

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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import shlex
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  body=b'<!doctype html><meta charset="utf-8"><title>Ordinary local website</title><p>This is a website, not a terminal.</p>'
  self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);Thread(target=server.serve_forever,daemon=True).start()
website='http://127.0.0.1:'+str(server.server_address[1])+'/'
def notification():return js('const n=navTab.linkedBrowser._notificationBox?.getNotificationWithValue("zen-terminal-away");return n?{message:n.messageText?.textContent||n.message||"",ready:!n._clickjackingDelayActive}:null;')
def current_url():return js('return navTab.linkedBrowser.currentURI.spec;')
def same_job():
 result=tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}');assert result.returncode==0,result.stderr
 assert result.stdout.strip()==original_pid
 assert marker.read_text().splitlines()==['launch']
def navigate_address(url):
 js('gBrowser.selectedTab=navTab;')
 field=js('return gURLBar.inputField;');field.click();field.send_keys(Keys.META+'a'+Keys.NULL);field.send_keys(url);field.send_keys(Keys.ENTER)
 wait(lambda:current_url()==url,'actual address-bar website navigation')
 wait(lambda:notification() and notification()['ready'],'native return notification ready')
 same_job()
def click_notification_return():
 wait(lambda:notification() and notification()['ready'],'native notification click protection finished')
 js('return navTab.linkedBrowser._notificationBox.getNotificationWithValue("zen-terminal-away")._buttons[0];').click()
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'notification Return reconnect')
 wait(lambda:notification() is None,'notice gone on terminal')
 same_job()
failure=None
try:
 start()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();');assert socket.startswith('zen-terminal-p')
 marker=run/'launch-count.txt'
 sid=js('const service=ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService;const setup=service.create("Navigation proof","briefcase","purple");ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs").setTerminalContainerRecipe(setup.userContextId,{recipe:{steps:[arguments[0]]}});window.navTab=gZenTerminalTabs.openTerminalContainerTab(setup.userContextId);return navTab.getAttribute("zen-terminal-session-id");',['printf "launch\\n" >> '+shlex.quote(str(marker))])
 test_sessions.append(sid)
 wait(lambda:terminal_status() and 'ready' in terminal_status(),'terminal ready')
 wait(lambda:marker.exists(),'one launch')
 original_pid=tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}').stdout.strip();assert original_pid.isdigit()
 assert notification() is None
 record('fresh terminal has no away notice and owns one real job')
 navigate_address(website+'first')
 assert 'Closing its last copy' in notification()['message'],notification()
 assert js('return navTab.linkedBrowser.contentPrincipal.isContentPrincipal;')
 assert js('return gURLBar.value;').rstrip('/')==(website+'first').rstrip('/')
 record('real address-bar navigation keeps job and shows native return notice')
 screen('navigation-away')
 click_notification_return();record('rendered native Return button reconnects same job without startup')
 navigate_address(website+'back-proof')
 js('navTab.linkedBrowser.goBack();')
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'Back reconnect')
 wait(lambda:notification() is None,'Back removes notice');same_job()
 js('navTab.linkedBrowser.reload();')
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'terminal reload reconnect')
 assert notification() is None;same_job();record('Back and terminal reload preserve job without warning')
 navigate_address(website+'dismiss-proof')
 close=wait(lambda:js('const n=navTab.linkedBrowser._notificationBox.getNotificationWithValue("zen-terminal-away");return n?.closeButton?.shadowRoot?.querySelector("button")||n?.closeButton;'),'rendered notification close button')
 close.click();wait(lambda:notification() is None,'dismiss native notice')
 js('navTab.linkedBrowser.reload();')
 wait(lambda:current_url()==website+'dismiss-proof','website reload')
 time.sleep(.5);assert notification() is None;same_job()
 record('native dismissal persists over website reload without another warning')
 try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
 except Exception:pass
 process.wait(timeout=15)
 start()
 wait(lambda:js('window.navTab=[...gBrowser.tabs].find(t=>{try{return JSON.parse(SessionStore.getCustomTabValue(t,"zenTerminalOwnership")).id===arguments[0];}catch(_){return false;}});if(navTab)gBrowser.selectedTab=navTab;return !!navTab;',[sid]),'restored owned website tab')
 wait(lambda:current_url()==website+'dismiss-proof','restored web address')
 assert notification() is None;same_job()
 record('quit/restart while browsing preserves job, ownership and dismissed notice')
 js('TabContextMenu.contextTab=navTab;document.getElementById("tabContextMenu").openPopup(navTab,"after_start");')
 action=wait(lambda:m.find_element('id','context_zenReturnToTerminal'),'native context action')
 wait(lambda:action.is_displayed(),'Return action visible after dismissal')
 action.click()
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'context-menu Return reconnect')
 same_job();assert notification() is None
 record('native context-menu Return works after persisted notification dismissal')
 navigate_address(website+'final-close')
 js('gBrowser.removeTab(navTab,{animate:false});')
 wait(lambda:tmux('has-session','-t','=zt_'+sid).returncode!=0,'final website view close destroys owned job')
 record('only final actual tab close ends the retained terminal job')
 for case in ['bookmark current-tab navigation','actual URL drag/drop into terminal','mirrored-window away notice','non-tmux native away wording']:
  results.append({'test':case,'result':'not_run','detail':'Separate native journey required; no substitution by address-bar/module checks.'})
except Exception as error:
 failure=repr(error);raise
finally:
 (proof/(args.label+'-navigation-workflows.json')).write_text(json.dumps({'app':str(args.app),'scope':'Synthetic local website and terminal; actual address-bar and notification inputs, native browser methods as labelled','results':results,'failure':failure,'run':str(run)},indent=2)+'\n')
 if m:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 if socket:
  for sid in test_sessions:tmux('kill-session','-t','=zt_'+sid)
 server.shutdown();server.server_close();log.close()
