#!/usr/bin/env python3
"""Native performance acceptance smoke; fresh synthetic profile, never personal data.
Budgets are provisional product acceptance limits, not measured baseline claims.
"""
import argparse, json, math, os, re, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--app',required=True,type=Path)
p.add_argument('--label',default='native-performance')
p.add_argument('--expected-engine',default='156.0')
a=p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]+',a.label):p.error('Invalid proof label')
root=Path(__file__).resolve().parents[2];app=a.app.resolve();exe=app/'Contents/MacOS/zen-terminal'
if not exe.is_file():p.error('Expected separate Zen Terminal app')
if 'Milestone='+a.expected_engine not in (app/'Contents/Resources/platform.ini').read_text().splitlines():p.error('Unexpected engine; no launch')
if os.environ.get('MOZ_HEADLESS'):p.error('This is a headed native test; no launch')
tmux_exe=Path('/opt/homebrew/bin/tmux')
if not tmux_exe.is_file():p.error('Real tmux required; no launch')
run=root/'.terminal-test'/('performance-'+uuid.uuid4().hex[:8]);home=run/'home';profile=run/'profile'
home.mkdir(parents=True);profile.mkdir()
proof=root/'docs/proof/2026-09-19';proof.mkdir(parents=True,exist_ok=True)
(home/'.zshenv').write_text('export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n')
(home/'.zshrc').write_text("PROMPT='performance-proof> '\n")
with net_socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
prefs={'marionette.port':port,'browser.shell.checkDefaultBrowser':False,'browser.startup.page':0,'browser.startup.homepage':'about:blank','zen.welcome-screen.seen':True,'browser.aboutwelcome.enabled':False,'app.update.disabledForTesting':True,'app.update.enabled':False,'privacy.userContext.enabled':True,'privacy.userContext.ui.enabled':True}
(profile/'user.js').write_text('\n'.join('user_pref(%s,%s);'%(json.dumps(k),json.dumps(v)) for k,v in prefs.items()))
env=dict(os.environ,MOZ_APP_DATA=str(home/'app-data'),MOZ_LOCAL_APP_DATA=str(home/'local-app-data'),HOME=str(home),ZDOTDIR=str(home),SHELL='/bin/zsh',PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',MOZ_NO_REMOTE='1')
for key in list(env):
 if key.startswith(('XRE_PROFILE_','SELECTABLE_PROFILE_RESET_')) or key in {'XRE_RESTARTED_BY_PROFILE_MANAGER','MOZ_RESET_PROFILE_RESTART','MOZ_LEGACY_PROFILES'}:env.pop(key,None)
manager='chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs'
store='chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs'
cis='moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs'
budgets={'startup_seconds':20,'each_terminal_seconds':8,'six_terminals_seconds':30,'idle_total_one_core_percent':25,'idle_increment_one_core_percent':15,'six_terminal_rss_increment_mib':512,'burst_seconds':10,'heartbeat_p95_ms':150,'heartbeat_max_ms':500,'cleanup_seconds':10}
results=[];metrics={};process=None;m=None;owned=False;socket=None;server_pid=None;session_ids=[];log=(run/'gecko.log').open('w')
def js(code,args=None):return m.execute_script(code,script_args=args or [])
def wait(check,label,timeout=30):
 end=time.monotonic()+timeout;last=None
 while time.monotonic()<end:
  try:
   result=check()
   if result:return result
  except Exception as exc:last=exc
  time.sleep(.1)
 raise AssertionError('Timed out '+label+'; '+str(last))
def check(name,value,limit):
 passed=value<=limit;results.append({'test':name,'result':'pass' if passed else 'fail','actual':value,'limit':limit});print('PASS' if passed else 'FAIL',name,value,'limit',limit,flush=True)
 # Collect the remaining measurements even when a budget fails.
def tmux(*args):
 assert owned and socket and re.fullmatch(r'zen-terminal-p[A-Za-z0-9_-]+',socket)
 return subprocess.run([str(tmux_exe),'-L',socket,*args],capture_output=True,text=True,timeout=5)
def cpu_seconds(value):
 days=0
 if '-' in value:day,value=value.split('-',1);days=int(day)
 pieces=[float(n) for n in value.split(':')]
 return days*86400+sum(n*(60**i) for i,n in enumerate(reversed(pieces)))
def process_sample():
 # Read process counters, not arguments, paths or other applications' UI.
 rows={}
 for line in subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,time=,rss='],text=True).splitlines():
  fields=line.split()
  if len(fields)==4:rows[int(fields[0])]=(int(fields[1]),cpu_seconds(fields[2]),int(fields[3]))
 roots={process.pid}
 if server_pid:roots.add(server_pid) # Detached tmux server still belongs to our verified profile socket.
 selected=set(roots)
 while True:
  expanded=selected|{pid for pid,row in rows.items() if row[0] in selected}
  if expanded==selected:break
  selected=expanded
 return {pid:rows[pid][1:] for pid in selected if pid in rows}
def idle_measure():
 time.sleep(3) # Let initial layout/first shell prompt settle; not a measured improvement.
 start=time.monotonic();previous=process_sample();cpu=0;peak=sum(x[1] for x in previous.values());count=0
 while time.monotonic()-start<8:
  time.sleep(.25);current=process_sample();count+=1
  for pid,(seconds,rss) in current.items():cpu+=max(0,seconds-previous.get(pid,(seconds,0))[0])
  peak=max(peak,sum(x[1] for x in current.values()));previous=current
 elapsed=time.monotonic()-start
 return {'one_core_cpu_percent':100*cpu/elapsed,'peak_aggregate_rss_mib':peak/1024,'seconds':elapsed,'samples':count,'pids_at_end':sorted(previous)}
def page(index,code,args=None):
 return js('const w=performanceTabs[arguments[0]].linkedBrowser.contentWindow.wrappedJSObject;const terminal=w.__performanceTerminal;'+code,[index]+(args or []))
try:
 started=time.monotonic();process=subprocess.Popen([str(exe),'-no-remote','-marionette','--remote-allow-system-access','-profile',str(profile)],env=env,stdout=log,stderr=log)
 m=Marionette(host='127.0.0.1',port=port,startup_timeout=30,socket_timeout=30);m.raise_for_port(timeout=30);m.start_session();m.set_context('chrome')
 assert js('return Services.appinfo.processID;')==process.pid
 assert Path(js('return Services.dirsvc.get("ProfD",Ci.nsIFile).path;')).resolve()==profile.resolve()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 owned=True
 wait(lambda:js('return Boolean(window.gZenTerminalTabs && gBrowserInit.delayedStartupFinished);'),'startup ready')
 metrics['startup_seconds']=time.monotonic()-started;check('Process launch to browser ready (includes driver handshake)',metrics['startup_seconds'],budgets['startup_seconds'])
 metrics['baseline_idle']=idle_measure()
 socket=js('return ChromeUtils.importESModule(arguments[0]).getTerminalTmuxSocket();',[manager])
 # Observe the real unchanged xterm instance, only to confirm output reaches its buffer.
 js('''window.performanceObserver={observe(doc){
 if(!doc.documentURI.startsWith('chrome://browser/content/zen-terminal/terminal.xhtml'))return;
 const w=doc.defaultView.wrappedJSObject;let Original;
 Object.defineProperty(w,'Terminal',{configurable:true,get(){return Original;},set(value){Original=new Proxy(value,{construct(target,args){const instance=Reflect.construct(target,args);w.__performanceTerminal=instance;return instance;}});}});
 }};Services.obs.addObserver(performanceObserver,'document-element-inserted');
 window.performanceTabs=[];
 const identity=ChromeUtils.importESModule(arguments[0]).ContextualIdentityService.create('Performance proof','briefcase','purple');
 window.performanceOwner=identity.userContextId;
 ChromeUtils.importESModule(arguments[1]).setTerminalContainerRecipe(performanceOwner,{recipe:{steps:[]}});''',[cis,store])
 all_started=time.monotonic();durations=[]
 for index in range(6):
  began=time.monotonic()
  sid=js('const tab=gZenTerminalTabs.openTerminalContainerTab(performanceOwner);performanceTabs.push(tab);return tab.getAttribute("zen-terminal-session-id");')
  session_ids.append(sid)
  wait(lambda:page(index,'return w.document.getElementById("zen-terminal-surface")?.hasAttribute("terminal-ready") && !!terminal;'),'real terminal '+str(index))
  assert tmux('has-session','-t','=zt_'+sid).returncode==0
  durations.append(time.monotonic()-began)
 metrics['six_terminal_seconds']=time.monotonic()-all_started;metrics['terminal_ready_seconds']=durations
 check('Each real terminal reaches ready',max(durations),budgets['each_terminal_seconds']);check('Six independent real terminal tabs',metrics['six_terminal_seconds'],budgets['six_terminals_seconds'])
 server_pid=int(tmux('display-message','-p','-t','zt_'+session_ids[0],'#{pid}').stdout.strip());assert server_pid>1
 metrics['six_terminal_idle']=idle_measure()
 check('Six idle terminals plus browser CPU',metrics['six_terminal_idle']['one_core_cpu_percent'],budgets['idle_total_one_core_percent'])
 check('Additional idle CPU above browser baseline',metrics['six_terminal_idle']['one_core_cpu_percent']-metrics['baseline_idle']['one_core_cpu_percent'],budgets['idle_increment_one_core_percent'])
 check('Additional aggregate RSS above browser baseline',metrics['six_terminal_idle']['peak_aggregate_rss_mib']-metrics['baseline_idle']['peak_aggregate_rss_mib'],budgets['six_terminal_rss_increment_mib'])
 js('window.performancePulse={last:performance.now(),gaps:[]};window.performanceTimer=setInterval(()=>{const now=performance.now();performancePulse.gaps.push(now-performancePulse.last);performancePulse.last=now;},50);')
 token='PERF_DONE_'+uuid.uuid4().hex;burst_start=time.monotonic()
 # 4096 lines x ~97 bytes x 6 jobs: ~2.3 MiB from actual PTYs, bounded output.
 command="/usr/bin/awk 'BEGIN { for(i=0;i<4096;i++) printf \"%096d\\n\",i; print \""+token+"\" }'"
 for sid in session_ids:
  assert tmux('send-keys','-t','=zt_'+sid,'-l',command).returncode==0
  assert tmux('send-keys','-t','=zt_'+sid,'Enter').returncode==0
 def all_rendered():
  return js('return performanceTabs.every(tab=>{const t=tab.linkedBrowser.contentWindow.wrappedJSObject.__performanceTerminal;const b=t?.buffer.active;if(!b)return false;for(let i=Math.max(0,b.length-8);i<b.length;i++){if(b.getLine(i)?.translateToString(true).trim()===arguments[0])return true;}return false;});',[token])
 wait(all_rendered,'all actual terminal buffers contain completed output',timeout=20)
 metrics['burst_seconds']=time.monotonic()-burst_start
 gaps=js('clearInterval(performanceTimer);performancePulse.gaps.push(performance.now()-performancePulse.last);return performancePulse.gaps;')
 assert gaps;ordered=sorted(gaps);metrics['heartbeat']={'samples':len(gaps),'p95_ms':ordered[max(0,math.ceil(.95*len(gaps))-1)],'max_ms':max(gaps)}
 check('All six output bursts reach actual xterm buffers',metrics['burst_seconds'],budgets['burst_seconds'])
 check('Browser main-thread heartbeat p95 during output',metrics['heartbeat']['p95_ms'],budgets['heartbeat_p95_ms']);check('Worst browser main-thread heartbeat during output',metrics['heartbeat']['max_ms'],budgets['heartbeat_max_ms'])
 cleanup_started=time.monotonic()
 js('ChromeUtils.importESModule(arguments[0]).ContextualIdentityService.remove(performanceOwner);',[cis])
 wait(lambda:all(tmux('has-session','-t','=zt_'+sid).returncode!=0 for sid in session_ids),'exact test jobs stopped')
 wait(lambda:js('const records=ChromeUtils.importESModule(arguments[0]).readTerminalSessionRecords();return arguments[1].every(id=>!records[id]);',[manager,session_ids]),'session records removed')
 metrics['cleanup_seconds']=time.monotonic()-cleanup_started;check('Native setup removal stops all six jobs and clears records',metrics['cleanup_seconds'],budgets['cleanup_seconds'])
 js('Services.obs.removeObserver(performanceObserver,"document-element-inserted");')
except Exception as exc:
 results.append({'test':'performance journey','result':'fail','detail':str(exc)});print('FAIL',repr(exc),flush=True)
 raise
finally:
 if m and owned:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);return true;')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:
   process.terminate()
   try:process.wait(timeout=5)
   except subprocess.TimeoutExpired:process.kill();process.wait()
 if socket and owned:
  for sid in session_ids:tmux('kill-session','-t','=zt_'+sid) # Exact owned jobs only; no kill-server.
 log.close()
 (proof/(a.label+'-results.json')).write_text(json.dumps({'app':str(app),'engine':a.expected_engine,'budgets':budgets,'metrics':metrics,'results':results,'log':str(run/'gecko.log'),'limitations':['single-machine smoke, not cross-hardware certification','startup includes Marionette handshake','aggregate RSS counts shared pages more than once','process sampling can miss CPU from jobs shorter than 250ms','heartbeat measures browser main-thread scheduling, not compositor paint latency','output completion checks actual xterm buffer, not screenshot pixels']},indent=2)+'\n')
if any(r['result']=='fail' for r in results):raise SystemExit(1)
