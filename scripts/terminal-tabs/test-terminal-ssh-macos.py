#!/usr/bin/env python3
"""Firefox156 native browser/security boundaries on disposable data only.
Uses actual public methods and real DOM; no extracted functions or remote shares.
"""
import argparse, json, os, shlex, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.keys import Keys

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='packaged')

parser.add_argument('--ssh-host', required=True, choices=['chubs@100.92.30.93'])
parser.add_argument('--known-hosts', type=Path, default=Path.home()/'.ssh/known_hosts')
parser.add_argument('--identity-file', type=Path, help='Optional existing private-key path passed to OpenSSH; never read/copied by this test')
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

def launch_recipe(name,steps):
 sid=js("""const cis=ChromeUtils.importESModule('moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs').ContextualIdentityService;
 const store=ChromeUtils.importESModule('chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs');
 const identity=cis.create(arguments[0],'briefcase','purple');store.setTerminalContainerRecipe(identity.userContextId,{recipe:{steps:arguments[1]}});
 window.sshProofTab=gZenTerminalTabs.openTerminalContainerTab(identity.userContextId);
 return sshProofTab.getAttribute('zen-terminal-session-id');""",[name,steps])
 test_sessions.append(sid)
 wait(lambda:js('return gBrowser.selectedBrowser.contentDocument?.getElementById("zen-terminal-surface")?.hasAttribute("terminal-ready");'),'real terminal viewer ready')
 wait(lambda:tmux('has-session','-t','=zt_'+sid).returncode==0,'owned SSH recipe shell')
 return sid

def capture(sid):
 result=tmux('capture-pane','-p','-t','zt_'+sid,'-S','-100')
 assert result.returncode==0,result.stderr
 return result.stdout

failure=None
try:
 # Read only trusted entries matching the exact allowed endpoint, not an entire
 # personal config/profile. ssh-keygen retains hashed-host entries correctly.
 lookup=subprocess.run(['/usr/bin/ssh-keygen','-F','100.92.30.93','-f',str(args.known_hosts)],capture_output=True,text=True,timeout=5)
 if lookup.returncode!=0:raise AssertionError('No pre-existing trusted Chubs host key; refusing connection without prompting or keyscan')
 entries=[line for line in lookup.stdout.splitlines() if line and not line.startswith('#')]
 assert entries,'No matching trusted host-key entries'
 trusted=home/'chubs_known_hosts';trusted.write_text('\n'.join(entries)+'\n');trusted.chmod(0o600)
 # No permissive host-key setting and no password prompt. Never forward agent,
 # X11, TCP forwarding, or reuse an uncontrolled pre-existing connection.
 options=['-F','/dev/null','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','-o','ServerAliveInterval=3','-o','ServerAliveCountMax=2','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(trusted),'-o','GlobalKnownHostsFile=/dev/null','-o','UpdateHostKeys=no','-o','ForwardAgent=no','-o','ForwardX11=no','-o','ClearAllForwardings=yes','-o','ControlMaster=no','-o','ControlPath=none']
 if args.identity_file:
  identity=args.identity_file.expanduser().resolve();assert identity.is_file(),'Existing identity reference required'
  options+=['-o','IdentitiesOnly=yes','-i',str(identity)]
 else:
  assert os.environ.get('SSH_AUTH_SOCK'),'No existing SSH agent; supply an existing --identity-file path (no copy)'
  options+=['-o','IdentityFile=none','-o','IdentityAgent='+os.environ['SSH_AUTH_SOCK']]
 start()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 assert socket and socket.startswith('zen-terminal-p')
 record('owned app/profile/home; exact pre-trusted Chubs key; noninteractive authentication without copying a key')
 marker='ZT_SSH_'+uuid.uuid4().hex
 quote=shlex.join
 # Direct SSH rows intentionally make subsequent rows remote. These commands
 # only print markers on Chubs; they do not create files or start paid tools.
 sid=launch_recipe('SSH remote ordered proof',[quote(['/usr/bin/ssh',*options,args.ssh_host]),"printf '%s\\n' "+shlex.quote(marker+'_REMOTE_FIRST'),"printf '%s\\n' "+shlex.quote(marker+'_REMOTE_SECOND')])
 output=wait(lambda:(text if marker+'_REMOTE_SECOND' in (text:=capture(sid)) else None),'real remote ordered printf',timeout=35)
 assert output.index(marker+'_REMOTE_FIRST')<output.index(marker+'_REMOTE_SECOND'),output
 record('actual SSH connection completes before ordered remote printf rows')
 # env makes this an explicit local one-shot command, rather than the saved
 # setup language's SSH connection boundary. Its next row remains local.
 local_marker=home/'ssh-then-local.txt'
 local_step="printf '%s\\n' "+shlex.quote(marker+'_LOCAL')+' > '+shlex.quote(str(local_marker))
 sid=launch_recipe('SSH one-shot then local proof',[quote(['/usr/bin/env','/usr/bin/ssh',*options,args.ssh_host,"printf '%s\\n' "+shlex.quote(marker+'_ONESHOT')]),local_step])
 wait(lambda:local_marker.exists(),'local step after successful one-shot SSH',timeout=35)
 assert local_marker.read_text()==marker+'_LOCAL\n'
 assert marker+'_ONESHOT' in capture(sid)
 record('explicit local one-shot SSH returns before following local recipe row')
 forbidden=home/'ssh-failure-must-not-run.txt'
 # Exit 23 is deliberate remote failure after one harmless printed marker.
 # It proves the actual SSH status prevents later local steps, not just a
 # simulated network failure or unavailable-host timeout.
 sid=launch_recipe('SSH failure stops local proof',[quote(['/usr/bin/env','/usr/bin/ssh',*options,args.ssh_host,"printf '%s\\n' "+shlex.quote(marker+'_EXPECTED_FAILURE')+'; exit 23']),"printf forbidden > "+shlex.quote(str(forbidden))])
 wait(lambda:marker+'_EXPECTED_FAILURE' in capture(sid),'remote deliberate failure',timeout=35)
 # The shell reports recipe failure before returning to its normal prompt.
 wait(lambda:'Startup steps stopped (exit 23).' in capture(sid),'reported failed recipe status',timeout=10)
 assert not forbidden.exists()
 record('real SSH exit 23 stops subsequent local step without remote side effects')
 results.append({'test':'paid/authenticated AI-agent startup','result':'not_run','detail':'No AI agent or paid tool invoked; remote commands only printf and intentional exit.'})
except Exception as error:
 failure=repr(error)
 raise
finally:
 (proof/(args.label+'-ssh.json')).write_text(json.dumps({'app':str(args.app),'scope':'Actual pre-trusted Chubs SSH, only harmless printf/exit commands; saved-setup manager methods, not Settings editor UI','results':results,'failure':failure,'run':str(run)},indent=2)+'\n')
 if m:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 if socket:
  for sid in test_sessions:tmux('kill-session','-t','=zt_'+sid)
 log.close()
