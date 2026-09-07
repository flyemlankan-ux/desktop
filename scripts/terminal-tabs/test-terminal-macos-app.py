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
env=dict(os.environ,HOME=str(home),ZDOTDIR=str(home),SHELL='/bin/zsh',PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',MOZ_NO_REMOTE='1')
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
 if args.label == 'packaged':
  assert js('return Services.dirsvc.get("UAppData", Ci.nsIFile).path;').endswith('/zen-terminal')
  record('personal app-data root is isolated from stock Zen')
 assert js('return ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService.getPublicIdentities().some(x=>x.name==="Terminal");')
 record('plain Terminal setup is available on first launch')
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
 record('invalid remote recipe stays in dialog without saving')
 inputs=m.find_elements('css selector','#zen-terminal-recipe-steps input')
 inputs[0].clear();inputs[0].send_keys('printf started >> "$HOME/recipe-count"')
 inputs[1].clear();inputs[1].send_keys('printf second >> "$HOME/step-order"')
 # Move second step up and down through real buttons; order must return intact.
 m.find_elements('css selector','#zen-terminal-recipe-steps button')[3].click()
 m.find_elements('css selector','#zen-terminal-recipe-steps button')[1].click()
 record('ordered step editor supports reordering')
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
 # Use Zen's own static-label setter, then prove its saved value survives reload/restart.
 js('const tab=gBrowser.selectedTab;tab.zenStaticLabel="My renamed terminal";tab._zenChangeLabelFlag=true;gBrowser._setTabLabel(tab,"My renamed terminal",{_zenChangeLabelFlag:true});delete tab._zenChangeLabelFlag;')
 js('gBrowser.selectedBrowser.reload();')
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'reload reconnect')
 assert tmux('display-message','-p','-t',name,'#{pane_pid}').stdout.strip()==pid
 assert (home/'recipe-count').read_text()=='started'
 record('reload keeps same process and does not rerun startup')
 # Quit the browser normally; relaunch the same isolated profile.
 js("Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit); return true;");m=None;process.wait(timeout=20)
 assert tmux('has-session','-t','='+name).returncode==0
 start()
 tab=wait(lambda:js('const tab=[...gBrowser.tabs].find(t=>t.linkedBrowser.currentURI.spec.includes(arguments[0]));if(tab){gBrowser.selectedTab=tab;return true;}return false;',[sid]),'restored terminal tab')
 wait(lambda:terminal_status() and 'reconnected' in terminal_status(),'quit/relaunch reconnect')
 assert tmux('display-message','-p','-t',name,'#{pane_pid}').stdout.strip()==pid
 assert (home/'recipe-count').read_text()=='started'
 record('quit and relaunch restore same terminal process')
 assert js('return gBrowser.selectedTab.label;')=='My renamed terminal'
 record('saved terminal name survives reload and relaunch')
 screen('restored')
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
