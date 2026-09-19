#!/usr/bin/env python3
"""Negative website/ordinary-extension isolation in a disposable native browser.
No private profile data. Website attempts use actual rendered button clicks.
"""
import argparse, json, os, socket as net_socket, subprocess, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.keys import Keys

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='packaged')
parser.add_argument('--with-extension',action='store_true',help='Also install an unsigned temporary ordinary extension into this disposable profile only')
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
from threading import Thread, Lock
from urllib.parse import urlparse, parse_qs
import shlex, zipfile
from marionette_driver.addons import Addons
reports=[];report_lock=Lock();token=uuid.uuid4().hex;addon_id=None
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  query=parse_qs(urlparse(self.path).query)
  mode=query.get('mode',[''])[0];target=query.get('target',[''])[0]
  script='''const mode=MODE,target=TARGET,endpoint=ENDPOINT;
  document.getElementById('attempt').addEventListener('click',()=>{
    let result='attempted';
    try {
      if(mode==='iframe'){const frame=document.createElement('iframe');frame.id='probe';frame.src=target;document.body.append(frame);}
      else if(mode==='top'){location.assign(target);}
      else if(mode==='popup'){const child=window.open(target,'_blank');if(!child)result='popup-blocked';}
      else throw Error('unknown case');
    }catch(error){result=String(error);}
    navigator.sendBeacon(endpoint,JSON.stringify({kind:'web',mode,result}));
  });'''.replace('MODE',json.dumps(mode)).replace('TARGET',json.dumps(target)).replace('ENDPOINT',json.dumps('/report/'+token))
  data=('<!doctype html><meta charset="utf-8"><title>Terminal security probe</title><button id="attempt">Try opening terminal</button><script>'+script+'</script>').encode()
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_POST(self):
  if self.path!='/report/'+token:self.send_error(404);return
  size=int(self.headers.get('Content-Length','0'))
  if size>65536:self.send_error(413);return
  data=json.loads(self.rfile.read(size))
  with report_lock:reports.append(data)
  self.send_response(200);self.send_header('Access-Control-Allow-Origin','*');self.end_headers();self.wfile.write(b'ok')
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
server_thread=Thread(target=server.serve_forever,daemon=True);server_thread.start()
origin='http://127.0.0.1:'+str(server.server_address[1])
def click_web(url):
 chrome=m.current_chrome_window_handle
 try:
  m.set_context('content')
  found=False
  for handle in m.window_handles:
   m.switch_to_window(handle)
   if m.execute_script('return document.documentURI;')==url:found=True;break
  assert found,'Probe page not found'
  m.find_element('id','attempt').click()
 finally:m.set_context('chrome');m.switch_to_window(chrome)
def report_for(kind,mode=None):
 with report_lock:return next((item for item in reports if item.get('kind')==kind and (mode is None or item.get('mode')==mode)),None)
def no_process(sid):
 assert tmux('has-session','-t','=zt_'+sid).returncode!=0
 assert not js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalSessionRecord(arguments[0]);',[sid])
 assert not marker.exists()
def pid(sid):
 result=tmux('display-message','-p','-t','zt_'+sid,'#{pane_pid}');assert result.returncode==0,result.stderr
 value=result.stdout.strip();assert value.isdigit(),repr(value);return value
failure=None
try:
 start()
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 socket=js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
 assert socket.startswith('zen-terminal-p')
 marker=run/'unexpected-or-owned-startup.txt'
 identity=js('const service=ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService;window.webProbeIdentity=service.create("Web isolation proof","briefcase","purple");window.webProbeOther=service.create("Other context","fingerprint","blue");ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs").setTerminalContainerRecipe(webProbeIdentity.userContextId,{recipe:{steps:[arguments[0]]}});return webProbeIdentity.userContextId;',['printf "launch\\n" >> '+shlex.quote(str(marker))])
 record('owned native browser with synthetic terminal setup')
 from urllib.parse import urlencode
 base='chrome://browser/content/zen-terminal/terminal.xhtml'
 for mode in ['iframe','top','popup']:
  sid='web-'+mode+'-'+uuid.uuid4().hex[:10];test_sessions.append(sid)
  target=base+'?'+urlencode({'session':sid,'userContextId':identity})
  url=origin+'/?'+urlencode({'mode':mode,'target':target})
  js('window.webProbeTab=gBrowser.addTab(arguments[0],{userContextId:arguments[1],triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});gBrowser.selectedTab=webProbeTab;',[url,identity])
  wait(lambda:js('return webProbeTab.linkedBrowser.currentURI.spec===arguments[0] && webProbeTab.linkedBrowser.contentPrincipal?.isContentPrincipal;',[url]),'ordinary web principal loaded')
  click_web(url)
  result=wait(lambda:report_for('web',mode),'website attempted '+mode)
  assert result['result']!='popup-blocked','Popup blocker hid the actual chrome permission test'
  time.sleep(.7)
  no_process(sid)
  assert js('return [...gBrowser.tabs].every(t=>!t.linkedBrowser.currentURI.spec.startsWith(arguments[0]));',[base])
  if mode=='iframe':
   frame_uris=js('const collect=bc=>[bc.currentWindowGlobal?.documentURI?.spec||"",...bc.children.flatMap(collect)];return collect(webProbeTab.linkedBrowser.browsingContext);')
   assert not any(uri.startswith(base) for uri in frame_uris),frame_uris
  record('ordinary same-container website cannot launch terminal via '+mode,result)
 if args.with_extension:
  sid='extension-'+uuid.uuid4().hex[:10];test_sessions.append(sid)
  target=base+'?'+urlencode({'session':sid,'userContextId':identity})
  manifest={'manifest_version':2,'name':'Disposable terminal isolation proof','version':'1.0','browser_specific_settings':{'gecko':{'id':'terminal-isolation-'+token+'@test.invalid'}},'permissions':['tabs','cookies','contextualIdentities','http://127.0.0.1/*'],'background':{'scripts':['background.js']}}
  background='''(async()=>{const output={kind:'extension',results:[]};let ordinary;
    try{ordinary=await browser.tabs.create({url:ORIGIN,cookieStoreId:STORE});
      for(const operation of ['create','update']){
        try{if(operation==='create')await browser.tabs.create({url:TARGET,cookieStoreId:STORE});else await browser.tabs.update(ordinary.id,{url:TARGET});output.results.push({operation,rejected:false});}
        catch(error){output.results.push({operation,rejected:true,message:String(error)});}
      }
    }catch(error){output.error=String(error);}
    await fetch(ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(output)});
  })();'''.replace('ORIGIN',json.dumps(origin)).replace('STORE',json.dumps('firefox-container-'+str(identity))).replace('TARGET',json.dumps(target)).replace('ENDPOINT',json.dumps(origin+'/report/'+token))
  extension=run/'ordinary-extension.xpi'
  with zipfile.ZipFile(extension,'w') as archive:
   archive.writestr('manifest.json',json.dumps(manifest));archive.writestr('background.js',background)
  addon_id=Addons(m).install(str(extension),temp=True)
  result=wait(lambda:report_for('extension'),'ordinary extension returns real API results')
  assert not result.get('error'),result
  assert len(result['results'])==2 and all(item['rejected'] for item in result['results']),result
  no_process(sid)
  record('ordinary temporary extension tabs.create/update reject terminal chrome',result)
  Addons(m).uninstall(addon_id);addon_id=None
 else:results.append({'test':'ordinary extension tabs.create/update','result':'not_run','detail':'Enable --with-extension; web proof does not substitute for extension proof.'})
 # Create one real shell, then detach its legitimate viewer by navigation and
 # deliberately clear ONLY that viewer's receipt in this disposable fixture.
 # This models an already-orphaned job, without using any shared/personal socket.
 sid=js('window.orphanTab=gZenTerminalTabs.openTerminalContainerTab(webProbeIdentity.userContextId);return orphanTab.getAttribute("zen-terminal-session-id");')
 test_sessions.append(sid)
 wait(lambda:terminal_status() and ('ready' in terminal_status()),'owned terminal started')
 wait(lambda:marker.exists(),'owned startup marker')
 original_pid=pid(sid)
 js('orphanTab.linkedBrowser.loadURI(Services.io.newURI("about:blank"),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});')
 wait(lambda:js('return orphanTab.linkedBrowser.currentURI.spec==="about:blank";'),'owned terminal viewer detaches')
 js('delete orphanTab.__zenTerminalOwnership;SessionStore.deleteCustomTabValue(orphanTab,"zenTerminalOwnership");SessionStore.deleteCustomTabValue(orphanTab,"zenTerminalSessionId");orphanTab.removeAttribute("zen-terminal-session-id");orphanTab.removeAttribute("zen-terminal-tab");gBrowser.removeTab(orphanTab,{animate:false});')
 assert pid(sid)==original_pid
 js('window.rejectedTab=gBrowser.addTab(arguments[0],{userContextId:webProbeOther.userContextId,triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});gBrowser.selectedTab=rejectedTab;',[base+'?'+urlencode({'session':sid,'userContextId':identity})])
 wait(lambda:js('return rejectedTab.linkedBrowser.contentDocument?.getElementById("zen-terminal-status-text")?.textContent.includes("does not match");'),'mismatched orphan address refuses')
 js('gBrowser.removeTab(rejectedTab,{animate:false});')
 time.sleep(.7)
 assert pid(sid)==original_pid
 assert marker.read_text().splitlines()==['launch']
 assert js('return !ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalSessionRecord(arguments[0]).pendingDelete;',[sid])
 record('closing rejected mismatched page cannot destroy a known orphan session',{'session':sid,'pid':original_pid,'fixture':'synthetic owned viewer receipt deliberately cleared after detachment'})
 screen('web-isolation-complete')
except Exception as error:
 failure=repr(error)
 raise
finally:
 (proof/(args.label+'-web-isolation.json')).write_text(json.dumps({'app':str(args.app),'scope':'Real localhost web actions, optional ordinary temporary extension, synthetic orphan fixture; no personal profiles','results':results,'failure':failure,'run':str(run)},indent=2)+'\n')
 if addon_id and m:
  try:Addons(m).uninstall(addon_id)
  except Exception:pass
 if m:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 if socket:
  for sid in test_sessions:tmux('kill-session','-t','=zt_'+sid)
 server.shutdown();server.server_close();log.close()
