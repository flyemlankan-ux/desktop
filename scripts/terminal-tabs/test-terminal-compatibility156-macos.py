#!/usr/bin/env python3
"""Firefox156 native browser/security boundaries on disposable data only.
Uses actual public methods and real DOM; no extracted functions or remote shares.
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
def async_js(script,args=None):
 result=m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{'+script+'})().then(value=>done({value}),error=>done({error:String(error)}));',script_args=args or [])
 assert 'error' not in result,result
 return result['value']
def snapshot():
 return js('return {tabs:gBrowser.tabs.map(t=>t.id),spaces:gZenWorkspaces.getWorkspaces().map(s=>s.uuid),selected:gBrowser.selectedTab.id,sessions:Services.prefs.getStringPref("zen.terminal.sessions","{}")};')

failure=None
try:
 start()
 assert js('return Services.appinfo.platformVersion;')=='156.0'
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 record('owned Firefox156 process and synthetic browser data confirmed')
 js('window.compatCIS=ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService;window.compatStore=ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs");window.compatWeb=compatCIS.create("Website proof","fingerprint","blue");window.compatTerminal=compatCIS.create("Terminal proof","briefcase","purple");compatStore.setTerminalContainerRecipe(compatTerminal.userContextId,{recipe:{steps:[]}});window.compatSafeTab=gBrowser.addTrustedTab("about:blank",{userContextId:compatWeb.userContextId});gBrowser.selectedTab=compatSafeTab;')
 web_id,terminal_id=js('return [compatWeb.userContextId,compatTerminal.userContextId];')
 state_before=snapshot()
 menu=js('gTabsPanel.init();const view=gTabsPanel.containerTabsView;view.dispatchEvent(new CustomEvent("ViewShowing",{bubbles:true}));const rows=[...view.querySelectorAll("[data-usercontextid]")].map(n=>({id:Number(n.getAttribute("data-usercontextid")),label:n.getAttribute("label")}));view.dispatchEvent(new CustomEvent("ViewHiding",{bubbles:true}));return rows;')
 assert any(row['id']==web_id for row in menu),menu
 assert not any(row['id']==terminal_id for row in menu),menu
 assert snapshot()==state_before
 record('actual All Tabs menu DOM excludes terminal setup and retains selected website',menu)
 options=js('const module=ChromeUtils.importESModule("chrome://browser/content/usercontext/container-select.mjs",{global:"current"});return module.containerOptions();')
 assert any(row['value']==str(web_id) for row in options)
 assert not any(row['value']==str(terminal_id) for row in options)
 assert snapshot()==state_before
 record('loaded Firefox156 association choices exclude terminal and preserve web choice')
 # The actual manager saves a stale workspace default; ordinary New Tab must
 # still be a website using ordinary identity0, not a terminal cookie identity.
 async_js('window.compatOriginalSpace={...gZenWorkspaces.getActiveWorkspaceFromCache()};await gZenWorkspaces.saveWorkspace({...compatOriginalSpace,containerTabId:compatTerminal.userContextId});return true;')
 assert js('return gZenWorkspaces.getActiveWorkspaceFromCache().containerTabId;')==terminal_id
 route=js('return gZenWorkspaces.getContextIdIfNeeded(undefined,false,Services.scriptSecurityManager.getSystemPrincipal());')
 assert route[0]==0,route
 js('BrowserOpenTab();')
 wait(lambda:js('return gBrowser.selectedTab!==compatSafeTab;'),'normal new tab')
 normal=js('return {id:Number(gBrowser.selectedTab.getAttribute("usercontextid")||0),terminal:gBrowser.selectedTab.hasAttribute("zen-terminal-tab"),uri:gBrowser.selectedBrowser.currentURI.spec,sessions:Services.prefs.getStringPref("zen.terminal.sessions","{}")};')
 assert normal['id']==0 and not normal['terminal'] and not normal['uri'].startswith('chrome://browser/content/zen-terminal/')
 assert normal['sessions']==state_before['sessions']
 js('gBrowser.removeTab(gBrowser.selectedTab,{animate:false});gBrowser.selectedTab=compatSafeTab;')
 async_js('await gZenWorkspaces.saveWorkspace(compatOriginalSpace);return true;')
 record('actual ordinary New Tab ignores stale terminal workspace default',normal)
 # Public client validation exercises packaged safety + schema without calling
 # upload/read share endpoints. Schema fetch is only resource:/// local app data.
 js('window.compatShareClient=ChromeUtils.importESModule("resource:///modules/zen/share/ZenShareClient.sys.mjs").ZenShareClient;')
 def share(url):
  return {'version':'1','shared':{'type':'folder','name':'Controlled proof','items':[{'type':'folder','name':'Nested','items':[{'type':'tab','url':url}]}]}}
 before_validation=snapshot()
 for url in ['chrome://browser/content/zen-terminal/terminal.xhtml?userContextId='+str(terminal_id),'javascript:throw 1','file:///synthetic/never-opened','data:text/html,blocked']:
  result=async_js('return await compatShareClient.validateDocument(arguments[0]);',[share(url)])
  assert result['valid'] is False,result
  assert snapshot()==before_validation
  record('native shared-document validation rejects nested '+url.split(':',1)[0]+' address without browser changes')
 result=async_js('return await compatShareClient.validateDocument(arguments[0]);',[share('https://example.invalid/controlled-proof')])
 assert result['valid'] is True,result
 assert snapshot()==before_validation
 record('native shared-document validation preserves safe HTTPS support without loading a site')
 # Open the real Firefox156 dialog using its public preferences controller.
 js('gBrowser.selectedTab=gBrowser.addTrustedTab("about:preferences#containers");')
 m.set_context('content')
 for handle in m.window_handles:
  m.switch_to_window(handle)
  if m.execute_script('return document.documentURI;').startswith('about:preferences'):break
 else:raise AssertionError('Preferences content handle unavailable')
 wait(lambda:m.execute_script('return Boolean(window.gSubDialog);'),'native preferences dialog controller')
 m.execute_script('window.gSubDialog.open("chrome://browser/content/preferences/dialogs/siteContainer.xhtml");')
 frame=wait(lambda:m.execute_script('return [...document.querySelectorAll("browser.dialogFrame")].find(x=>x.contentDocument?.documentURI==="chrome://browser/content/preferences/dialogs/siteContainer.xhtml");'),'native association dialog')
 m.execute_async_script('const done=arguments[arguments.length-1];arguments[0]._dialogReady.then(()=>done(true));',script_args=[frame])
 m.switch_to_frame(frame)
 dialog_options=m.execute_script('return [...document.querySelectorAll("container-select moz-option")].map(n=>n.getAttribute("value"));')
 assert str(web_id) in dialog_options and str(terminal_id) not in dialog_options,dialog_options
 record('rendered native site-association dialog contains web choices and excludes terminal')
 # No dangerous accept event is fabricated: click the real accept button.
 site_input=wait(lambda:m.execute_script('return document.querySelector("moz-input-text")?.shadowRoot?.querySelector("input");'),'native website input')
 site_input.send_keys('compatibility.example.invalid')
 m.execute_script('document.querySelector("container-select").value=String(arguments[0]);ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs").setTerminalContainerRecipe(arguments[0],{recipe:{steps:[]}});',script_args=[web_id])
 accept=m.execute_script('return document.querySelector("dialog").getButton("accept");')
 accept.click()
 error=wait(lambda:m.execute_script('return document.getElementById("siteContainerError")?.textContent;'),'native stale-choice visible error')
 assert 'web container' in error,error
 assert m.execute_script('return ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService.getSiteAssociation("compatibility.example.invalid");') in (0,None)
 assert m.execute_script('return document.querySelector("container-select").value;')==''
 record('actual accept click refuses a setup changed to terminal and keeps dialog open',error)
 m.set_context('chrome')
 # The real manager import entry points are private and triggered by share URLs.
 # We have deliberately NOT fetched a URL, mocked a private method, or claimed
 # full share-import UI acceptance from the public validation checks above.
 results.append({'test':'full native share import UI','result':'not_run','detail':'Public validation proved; no network share fetched and no private method extracted'})
 screen('compatibility156-native')
except Exception as error:
 failure=repr(error)
 raise
finally:
 (proof/(args.label+'-compatibility156.json')).write_text(json.dumps({'app':str(args.app),'scope':'Native public methods, real DOM and one rendered dialog accept click; no remote sharing','results':results,'failure':failure,'run':str(run)},indent=2)+'\n')
 if m:
  try:
   m.set_context('chrome')
   js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 log.close()
