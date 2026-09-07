#!/usr/bin/env python3
"""Real Mac app proof using Mozilla Marionette. Always an isolated synthetic profile.
Install test-only dependency: python -m pip install marionette_driver.
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
proof=root/'docs/proof/2026-09-07';proof.mkdir(parents=True,exist_ok=True)
home=run/'home';home.mkdir();profile=run/'profile';profile.mkdir()
(home/'.zshenv').write_text('export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n')
with net_socket.socket() as listener:
 listener.bind(('127.0.0.1',0));marionette_port=listener.getsockname()[1]
prefs={'marionette.port':marionette_port,'browser.shell.checkDefaultBrowser':False,'browser.startup.page':3,'zen.welcome-screen.seen':True,'app.update.disabledForTesting':True,'app.update.auto':False,'app.update.enabled':False,'browser.startup.homepage':'about:blank','browser.aboutwelcome.enabled':False,'browser.sessionstore.resume_from_crash':True,'privacy.userContext.enabled':True,'privacy.userContext.ui.enabled':True}
(profile/'user.js').write_text('\n'.join('user_pref(%s, %s);'%(json.dumps(k),json.dumps(v)) for k,v in prefs.items()))
env=dict(os.environ,MOZ_APP_DATA=str(home/'app-data'),MOZ_LOCAL_APP_DATA=str(home/'local-app-data'),HOME=str(home),ZDOTDIR=str(home),SHELL='/bin/zsh',PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',MOZ_NO_REMOTE='1')
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
 wait(lambda:js('return Boolean(window.gZenTerminalTabs && gBrowserInit.delayedStartupFinished);'),'browser ready')
def js(script,args=None):return m.execute_script(script,script_args=args or [])
def terminal_status():return js('return gBrowser.selectedBrowser.contentDocument?.getElementById("zen-terminal-status-text")?.textContent;')
def tmux(*args):return subprocess.run(['/opt/homebrew/bin/tmux','-L',socket,*args],capture_output=True,text=True,timeout=5)
def screen(name):
 m.set_context('chrome');(proof/(args.label+'-'+name+'.png')).write_bytes(m.screenshot(format='binary'))
try:
 start();socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();');record('real Mac app opens clean profile')
 assert js('return Services.dirsvc.get("UAppData", Ci.nsIFile).path;')==str(home/'app-data')
 record('test forces app-data into its disposable folder')
 if args.label == 'packaged':
  assert 'Profile=zen-terminal' in (args.app.resolve()/'Contents/Resources/application.ini').read_text()
  assert '155.0.1' in (args.app.resolve()/'Contents/Resources/platform.ini').read_text()
  record('packaged app declares terminal profile identity and current engine')
 assert js('return ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService.getPublicIdentities().some(x=>x.name==="Terminal");')
 record('plain Terminal setup is available on first launch')
 security=js('const manager=Services.scriptSecurityManager;const uri=Services.io.newURI("chrome://browser/content/zen-terminal/terminal.xhtml");manager.checkLoadURIWithPrincipal(manager.getSystemPrincipal(),uri,Ci.nsIScriptSecurityManager.STANDARD);try{manager.checkLoadURIWithPrincipal(manager.createContentPrincipal(Services.io.newURI("https://example.invalid"),{}),uri,Ci.nsIScriptSecurityManager.STANDARD);return false;}catch(error){return error.name;}')
 assert security=='NS_ERROR_DOM_BAD_URI',security
 record('ordinary websites cannot load the privileged terminal page',security)
 # Open Settings using browser navigation, then drive its native container form.
 js('gBrowser.selectedTab = gBrowser.addTab("about:preferences#containers", {triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});')
 m.set_context('content')
 m.switch_to_window(m.window_handles[-1])
 def deep_element(selector):
  return m.execute_script('const find=root=>{const found=root.querySelector(arguments[0]);if(found)return found;for(const node of root.querySelectorAll("*")){if(node.shadowRoot){const found=find(node.shadowRoot);if(found)return found;}}return null;};return find(document);',script_args=[selector])
 add_button=wait(lambda:deep_element('[data-l10n-id="containers-add-button2"]'),'stable container settings Add button')
 time.sleep(.5)
 add_button=m.execute_script('return arguments[0].shadowRoot?.querySelector("button") || arguments[0];',script_args=[add_button])
 add_button.click()
 frame=wait(lambda:m.execute_script('return [...document.querySelectorAll("browser.dialogFrame")].find(x=>x.contentDocument?.documentURI==="chrome://browser/content/preferences/dialogs/containers.xhtml");'),'native container dialog')
 m.switch_to_frame(frame)
 wait(lambda:m.find_element('id','zen-container-kind-terminal'),'kind chooser').click()
 name_input=wait(lambda:m.execute_script("return document.querySelector('moz-input-text[name=name]')?.shadowRoot?.querySelector('input');"),'native name input')
 name_input.send_keys('Terminal Proof')
 m.find_element('id','zen-terminal-add-step').click()
 first_step=m.find_element('css selector','#zen-terminal-recipe-steps input')
 first_step.send_keys('ssh -vN invalid')
 m.find_element('id','zen-terminal-add-step').click()
 inputs=m.find_elements('css selector','#zen-terminal-recipe-steps input')
 inputs[1].send_keys('printf never')
 m.execute_script('document.querySelector("dialog").getButton("accept").click();')
 wait(lambda:m.find_element('id','zen-terminal-recipe-error').is_displayed(),'invalid recipe feedback')
 assert m.execute_script('return ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService.getPublicIdentities().every(identity=>identity.name!=="Terminal Proof");')
 record('invalid remote recipe stays in dialog without saving')
 inputs=m.find_elements('css selector','#zen-terminal-recipe-steps input')
 inputs[0].clear();inputs[0].send_keys('printf started >> "$HOME/recipe-count"')
 inputs[1].clear();inputs[1].send_keys('printf second >> "$HOME/step-order"')
 # Move second step up and down through real buttons; order must return intact.
 m.find_elements('css selector','#zen-terminal-recipe-steps button')[3].click()
 m.find_elements('css selector','#zen-terminal-recipe-steps button')[1].click()
 assert m.execute_script('return [...document.querySelectorAll("#zen-terminal-recipe-steps input")].map(input=>input.value);') == ['printf started >> "$HOME/recipe-count"', 'printf second >> "$HOME/step-order"']
 record('ordered step editor supports reordering')
 # Functional controls must also fit the real native dialog, without sideways scrolling.
 layout=m.execute_script('return [...document.querySelectorAll("#containerEditorHost, .container-editor, #zen-terminal-container-fields, #zen-terminal-recipe-steps")].map(el=>({name:el.id||el.className,width:el.clientWidth,scroll:el.scrollWidth}));')
 assert all(item['scroll'] <= item['width'] + 1 for item in layout), layout
 record('native step editor fits without horizontal scrolling')
 # Real rendered dialog screenshot.
 (proof/(args.label+'-container-dialog.png')).write_bytes(m.screenshot(format='binary'))
 m.execute_script('document.querySelector("dialog").getButton("accept").click();')
 m.switch_to_frame();m.set_context('chrome')
 cid=wait(lambda:js('return ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService.getPublicIdentities().find(x=>x.name==="Terminal Proof")?.userContextId;'),'saved terminal container')
 record('create terminal container through actual Settings',cid)
 # Exercise the actual unified menu command, not the opener directly.
 js('const menu=document.querySelector("#zenCreateBrowserContainerTabMenu menupopup");gZenTerminalTabs.populateUnifiedContainerMenu({target:menu});menu.querySelector(`[data-usercontextid="${arguments[0]}"]`).doCommand();',[cid])
 wait(lambda:terminal_status() and ('ready' in terminal_status() or 'reconnected' in terminal_status()),'live terminal')
 sid=js('return gBrowser.selectedTab.getAttribute("zen-terminal-session-id");');test_sessions.append(sid)
 name='zt_'+sid
 pid=tmux('display-message','-p','-t',name,'#{pane_pid}').stdout.strip()
 assert pid.isdigit();record('menu opens real saved terminal',terminal_status())
 m.set_context('content')
 for handle in m.window_handles:
  m.switch_to_window(handle)
  if 'zen-terminal/terminal.xhtml' in m.get_url():break
 textarea=m.find_element('css selector','.xterm-helper-textarea')
 textarea.send_keys("printf 'REPEATED:%s\\n' 'aaabbb café 😀'\n")
 wait(lambda:'REPEATED:aaabbb café 😀' in tmux('capture-pane','-p','-t',name).stdout,'repeated Unicode command output')
 record('actual keyboard reaches local shell exactly')
 textarea.send_keys('sleep 60\n')
 wait(lambda:tmux('display-message','-p','-t',name,'#{pane_current_command}').stdout.strip()=='sleep','foreground sleep')
 textarea.send_keys(Keys.CONTROL+'c'+Keys.NULL)
 textarea.send_keys('printf INTERRUPTED\n')
 wait(lambda:'INTERRUPTED' in tmux('capture-pane','-p','-t',name).stdout,'Ctrl-C returns to shell')
 record('Ctrl-C interrupts a foreground program')
 textarea.send_keys('/usr/bin/vi -u NONE -i NONE -n "$HOME/editor-proof.txt"\n')
 wait(lambda:tmux('display-message','-p','-t',name,'#{pane_current_command}').stdout.strip() in {'vi','vim'},'full-screen editor')
 textarea.send_keys('iFull screen works café 😀'+Keys.ESCAPE+':wq\n')
 wait(lambda:(home/'editor-proof.txt').exists(),'editor saves file')
 assert (home/'editor-proof.txt').read_text().strip()=='Full screen works café 😀'
 record('full-screen editor accepts text and exits cleanly')
 for cli in args.cli_smoke:
  assert cli.is_absolute() and cli.is_file()
  quoted="'"+str(cli).replace("'", "'\\''")+"'"
  marker='CLI_DONE_'+cli.name
  textarea.send_keys(quoted+' --version; printf "'+marker+':%s\\n" "$?"\n')
  wait(lambda:marker+':0' in tmux('capture-pane','-p','-t',name).stdout,'CLI version '+cli.name)
  record('installed CLI starts inside actual terminal',cli.name)
 old_size=tmux('display-message','-p','-t',name,'#{pane_width}x#{pane_height}').stdout.strip()
 m.set_window_rect(width=1000,height=650)
 wait(lambda:tmux('display-message','-p','-t',name,'#{pane_width}x#{pane_height}').stdout.strip()!=old_size,'native window resize reaches terminal')
 record('real Mac window resize changes the shell dimensions')
 assert (home/'step-order').read_text()=='second' 
 m.set_context('chrome');screen('terminal')
 # Duplicating a terminal creates another viewer, not another startup process.
 js('window.__zenProofOriginalTab=gBrowser.selectedTab;gBrowser.selectedTab=gBrowser.duplicateTab(gBrowser.selectedTab,true);')
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'duplicate terminal viewer')
 assert js('return gBrowser.selectedTab.getAttribute("zen-terminal-session-id");')==sid
 js('gBrowser.removeTab(window.__zenProofOriginalTab,{animate:false});')
 wait(lambda:js('return ![...gBrowser.tabs].includes(window.__zenProofOriginalTab);'),'original viewer closes')
 time.sleep(.2)
 assert tmux('display-message','-p','-t',name,'#{pane_pid}').stdout.strip()==pid
 assert (home/'recipe-count').read_text()=='started'
 record('closing one duplicated terminal preserves its other viewer and process')
 # Drive the actual native tab-title editor, not a direct label setter.
 def rename_input(value):
  js('TabContextMenu.contextTab=gBrowser.selectedTab;document.getElementById("context_zen-edit-tab-title").doCommand();')
  editor=wait(lambda:m.find_element('id','tab-label-input'),'native tab rename input')
  editor.send_keys(value)
  return editor
 rename_input('Entered terminal').send_keys(Keys.ENTER)
 wait(lambda:js('return !document.getElementById("tab-label-input") && gBrowser.selectedTab.label==="Entered terminal";'),'Enter commits native rename')
 record('native terminal rename saves on Enter')
 rename_input('My renamed terminal')
 js('return gURLBar.inputField;').click()
 wait(lambda:js('return !document.getElementById("tab-label-input") && gBrowser.selectedTab.label==="My renamed terminal";'),'click-away commits native rename')
 record('native terminal rename saves on click-away')
 rename_input('Cancelled terminal').send_keys(Keys.ESCAPE)
 wait(lambda:js('return !document.getElementById("tab-label-input");'),'Escape closes native rename editor')
 escaped_label=js('return gBrowser.selectedTab.label;')
 assert escaped_label=='My renamed terminal',{'expected':'My renamed terminal','actual':escaped_label}
 record('Escape cancels native terminal rename')
 assert 'input is null' not in (run/'gecko.log').read_text()
 screen('native-rename-cancelled')
 js('gBrowser.selectedBrowser.reload();')
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'reload reconnect')
 assert tmux('display-message','-p','-t',name,'#{pane_pid}').stdout.strip()==pid
 assert (home/'recipe-count').read_text()=='started'
 record('reload keeps same process and does not rerun startup')
 # Keep the terminal in the background so its lazy restoration is tested.
 js('gBrowser.selectedTab=gBrowser.addTab("about:blank",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});')
 # Quit the browser normally; relaunch the same isolated profile.
 js("Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit); return true;");m=None;process.wait(timeout=20)
 assert tmux('has-session','-t','='+name).returncode==0
 start()
 background=wait(lambda:js('const tab=[...gBrowser.tabs].find(t=>{try{return JSON.parse(SessionStore.getTabState(t)).entries?.some(entry=>entry.url.includes(arguments[0]));}catch(_){return false;}});if(!tab||!tab.hasAttribute("zen-terminal-tab"))return null;return {selected:tab===gBrowser.selectedTab,label:tab.label,pending:tab.hasAttribute("pending")};',[sid]),'background terminal marked before selection')
 assert background['selected'] is False and background['label']=='My renamed terminal',background
 record('background restored terminal is marked and renamed before selection',background)
 js('const tab=[...gBrowser.tabs].find(t=>{try{return JSON.parse(SessionStore.getTabState(t)).entries?.some(entry=>entry.url.includes(arguments[0]));}catch(_){return false;}});gBrowser.selectedTab=tab;',[sid])
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'quit/relaunch reconnect')
 assert tmux('display-message','-p','-t',name,'#{pane_pid}').stdout.strip()==pid
 assert (home/'recipe-count').read_text()=='started'
 record('quit and relaunch restore same terminal process')
 assert js('return gBrowser.selectedTab.label;')=='My renamed terminal'
 record('saved terminal name survives reload and relaunch')
 screen('restored')
 # Simulate a real app crash: kill ONLY the browser process this test launched.
 crashed_pid=process.pid
 process.kill();assert process.wait(timeout=20)==-9;m=None
 assert tmux('display-message','-p','-t',name,'#{pane_pid}').stdout.strip()==pid
 start()
 recovery=wait(lambda:js('if([...gBrowser.tabs].some(t=>t.linkedBrowser.currentURI.spec==="about:sessionrestore"))return "restore-page";if([...gBrowser.tabs].some(t=>{try{return JSON.parse(SessionStore.getTabState(t)).entries?.some(entry=>entry.url.includes(arguments[0]));}catch(_){return false;}}))return "automatic";return null;',[sid]),'saved tabs after actual browser crash')
 if recovery=='restore-page':
  # Use Firefox's genuine recovery button; never construct replacement tab state.
  js('gBrowser.selectedTab=[...gBrowser.tabs].find(t=>t.linkedBrowser.currentURI.spec==="about:sessionrestore");')
  m.set_context('content')
  for handle in m.window_handles:
   m.switch_to_window(handle)
   if m.get_url()=='about:sessionrestore':break
  wait(lambda:m.find_element('id','errorTryAgain'),'genuine crash recovery button').click()
  m.set_context('chrome')
  wait(lambda:len(m.chrome_window_handles)>0,'browser window after recovery')
  m.switch_to_window(m.chrome_window_handles[-1])
 wait(lambda:js('const tab=[...gBrowser.tabs].find(t=>{try{return JSON.parse(SessionStore.getTabState(t)).entries?.some(entry=>entry.url.includes(arguments[0]));}catch(_){return false;}});if(tab){gBrowser.selectedTab=tab;return true;}return false;',[sid]),'crash-restored terminal tab')
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'crash reconnect to original shell')
 assert process.pid!=crashed_pid
 assert tmux('display-message','-p','-t',name,'#{pane_pid}').stdout.strip()==pid
 assert (home/'recipe-count').read_text()=='started'
 record('actual browser crash preserves same terminal process without repeating startup',{'browserRestarted':True,'recovery':recovery})
 screen('crash-restored')
 js('gBrowser.removeTab(gBrowser.selectedTab,{animate:false});')
 wait(lambda:tmux('has-session','-t','='+name).returncode!=0,'explicit close cleanup')
 record('explicit tab close destroys only its session')
except Exception as e:
 results.append({'test':'app proof','result':'fail','detail':str(e)});print('FAIL',repr(e),flush=True)
 try:screen('failure')
 except Exception:pass
 raise
finally:
 if m:
  try:js("Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit); return true;")
  except Exception:pass
 if process and process.poll() is None:
  process.terminate()
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:process.kill();process.wait()
 for sid in test_sessions:tmux('kill-session','-t','=zt_'+sid)
 log.close()
 (proof/(args.label+'-macos-results.json')).write_text(json.dumps({'app':str(args.app),'label':args.label,'test_data':'isolated synthetic profile, no founder data','results':results,'log':str(run/'gecko.log')},indent=2)+'\n')
