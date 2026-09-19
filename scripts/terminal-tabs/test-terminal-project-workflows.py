#!/usr/bin/env python3
"""Mixed project integration on an actual app, always disposable synthetic data.
Native methods unless explicitly labelled pointer input. Optional pointer drag
uses real W3C input; unsupported/broken input fails rather than faking a pass.
"""
import argparse, json, os, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.keys import Keys

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='packaged')
parser.add_argument('--pointer-drag', action='store_true', help='Attempt real pointer reorder; failure is NOT replaced by a native-method pass')
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
 return m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{'+script+'})().then(value=>done({value}),error=>done({error:String(error)}));',script_args=args or [])
def pane(sid,format='#{pane_pid}'):
 result=tmux('display-message','-p','-t','zt_'+sid,format)
 assert result.returncode==0,result.stderr
 return result.stdout.strip()
def same_jobs():
 assert [pane(sid) for sid in test_sessions]==job_pids
 assert marker.read_text().splitlines()==['launch','launch']

failure=None
try:
 start()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 assert socket and socket.startswith('zen-terminal-p')
 record('owned process and synthetic profile/data root confirmed')
 import shlex
 marker=run/'recipe-launches.txt'
 js('const service=ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService;const store=ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs");window.projectIdentity=service.create("Mixed project proof","briefcase","purple");store.setTerminalContainerRecipe(projectIdentity.userContextId,{recipe:{steps:[arguments[0]]}});window.projectTerms=[];', ['printf "launch\\n" >> '+shlex.quote(str(marker))])
 for i in range(2):
  sid=js('const tab=gZenTerminalTabs.openTerminalContainerTab(projectIdentity.userContextId);projectTerms.push(tab);return tab.getAttribute("zen-terminal-session-id");')
  test_sessions.append(sid)
  wait(lambda:tmux('has-session','-t','=zt_'+sid).returncode==0,'owned terminal job')
  wait(lambda:terminal_status() and 'ready' in terminal_status(),'terminal ready')
 wait(lambda:marker.exists() and len(marker.read_text().splitlines())==2,'exactly two recipe launches')
 job_pids=[pane(sid) for sid in test_sessions]
 assert len(set(job_pids))==2 and len(set(test_sessions))==2
 record('same saved setup launches two independent shells exactly once')
 js('window.projectWeb=gBrowser.addTrustedTab("about:blank");window.projectFolder=gZenFolders.createFolder([projectWeb,...projectTerms],{name:"Mixed project proof"});gBrowser.selectedTab=projectWeb;gBrowser.selectedTab=projectTerms[0];')
 time.sleep(1.7)
 assert js('return [projectWeb,...projectTerms].every(t=>t.group===projectFolder && t.pinned);')
 same_jobs();record('mixed folder retains web and both terminals after selection')
 js('projectFolder.collapsed=true;projectFolder.collapsed=false;')
 assert js('return [projectWeb,...projectTerms].every(t=>t.group===projectFolder);')
 same_jobs();record('native collapse/expand retains members and jobs')
 if args.pointer_drag:
  # W3C pointer actions hit actual browser chrome. Never inject drag events or
  # silently substitute DOM moves when real pointer dragging fails.
  rects=js('return [projectTerms[1],projectWeb].map(t=>{t.scrollIntoView({block:"nearest"});const r=t.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,top:r.y+2};});')
  source,target=rects
  m.actions.sequence('pointer','project-drag',{'pointerType':'mouse'}).pointer_move(int(source['x']),int(source['y'])).pointer_down().pause(250).pointer_move(int(target['x']),int(target['top']),duration=800).pause(500).pointer_up().perform()
  m.actions.release()
  wait(lambda:js('return projectTerms[1].group===projectFolder && projectFolder.tabs.indexOf(projectTerms[1])<projectFolder.tabs.indexOf(projectWeb);'),'actual pointer reorder')
  same_jobs();record('actual pointer drag reordered terminal before web inside folder')
 else:
  results.append({'test':'actual pointer drag/drop','result':'not_run','detail':'Use --pointer-drag; native methods do not establish pointer acceptance'})
 # Use Zen's actual move helper, not direct DOM insertion.
 js('gBrowser.moveTabTo(projectTerms[1],{tabIndex:projectWeb._tPos});')
 assert js('return projectTerms[1].group===projectFolder && projectFolder.tabs.indexOf(projectTerms[1])<projectFolder.tabs.indexOf(projectWeb);')
 same_jobs();record('native tab reorder retains folder and live jobs')
 created=async_js('window.projectSpace=await gZenWorkspaces.createAndSaveWorkspace("Mixed proof workspace");return projectSpace?.uuid;')
 assert created.get('value'),created
 moved=async_js('gZenFolders.changeFolderToSpace(projectFolder,projectSpace.uuid);await gZenWorkspaces.changeWorkspaceWithID(projectSpace.uuid);return projectSpace.uuid;')
 assert moved.get('value'),moved
 wait(lambda:js('return [projectWeb,...projectTerms].every(t=>t.group===projectFolder && t.getAttribute("zen-workspace-id")===projectSpace.uuid);'),'whole mixed folder moves to workspace')
 js('gBrowser.selectedTab=projectTerms[0];')
 same_jobs();record('whole mixed folder moves to new workspace without restarting jobs')
 js('gZenViewSplitter.splitTabs([projectWeb,projectTerms[0]],"grid",1);')
 wait(lambda:js('return projectWeb.splitView && projectTerms[0].splitView && projectWeb.group===projectTerms[0].group;'),'mixed split view')
 old_size=pane(test_sessions[0],'#{pane_width}x#{pane_height}')
 m.set_window_rect(width=1100,height=700)
 m.set_window_rect(width=900,height=600)
 wait(lambda:pane(test_sessions[0],'#{pane_width}x#{pane_height}')!=old_size,'split terminal resize')
 same_jobs();record('mixed split and window resize retain shell and resize terminal')
 js('gZenViewSplitter.removeTabFromGroup(projectTerms[0],undefined,{forUnsplit:true});gBrowser.selectedTab=projectTerms[0];')
 wait(lambda:js('return !projectTerms[0].splitView && !projectWeb.splitView;'),'unsplit')
 same_jobs();record('unsplit retains live jobs and recipe counts')
 js('window.projectOther=OpenBrowserWindow();')
 wait(lambda:js('return projectOther?.gBrowserInit?.delayedStartupFinished && !!projectOther.gZenWorkspaces;'),'second owned browser window')
 sync_ready=async_js('await projectOther.gZenWorkspaces.promiseInitialized;return {original:gZenWorkspaces.currentWindowIsSyncing,other:projectOther.gZenWorkspaces.currentWindowIsSyncing};')
 assert sync_ready.get('value',{}).get('original') and sync_ready.get('value',{}).get('other'),sync_ready
 wait(lambda:js('return projectTerms.every(t=>Boolean(gZenWindowSync.getItemFromWindow(projectOther,t.id)));'),'mirrored terminal tabs')
 js('const mirrored=gZenWindowSync.getItemFromWindow(projectOther,projectTerms[0].id);projectOther.gBrowser.selectedTab=mirrored;')
 same_jobs();record('second native window mirrors both terminal tabs without rerunning recipes')
 js('projectOther.close();')
 wait(lambda:js('return projectOther.closed;'),'second window closes')
 same_jobs();record('closing one mirrored window preserves original live jobs')
 # Native synchronized tab deletion should remove the final tab viewers.
 js('gBrowser.removeTab(projectTerms[1],{animate:false});')
 wait(lambda:tmux('has-session','-t','=zt_'+test_sessions[1]).returncode!=0,'last viewer session cleanup')
 assert pane(test_sessions[0])==job_pids[0]
 record('closing last view destroys only its matching shell')
 screen('project-workflows')
except Exception as error:
 failure=repr(error)
 raise
finally:
 report={'app':str(args.app),'scope':'Synthetic data; native browser-method integration except explicitly labelled pointer action','results':results,'failure':failure,'run':str(run)}
 (proof/(args.label+'-project-workflows.json')).write_text(json.dumps(report,indent=2)+'\n')
 if m:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 if socket:
  for sid in test_sessions:
   tmux('kill-session','-t','=zt_'+sid)
 log.close()
