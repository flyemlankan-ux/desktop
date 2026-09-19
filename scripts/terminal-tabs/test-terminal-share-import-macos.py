#!/usr/bin/env python3
"""Firefox156 native browser/security boundaries on disposable data only.
Uses actual public methods and real DOM; no extracted functions or remote shares.
"""
import argparse, copy, http.server, json, os, socket as net_socket, subprocess, threading, time, uuid
from pathlib import Path
from marionette_driver.marionette import Marionette
from marionette_driver.keys import Keys
from marionette_driver.by import By
from marionette_driver.errors import ElementClickInterceptedException

parser=argparse.ArgumentParser()
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='packaged')
parser.add_argument('--extended', action='store_true', help='Also test preview dismissal, workspace/nested-folder import and rapid real double activation')

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

# Transport-only fixture: real HTTP on loopback. No production method, fetch,
# validator, private importer, or UI handler is replaced. Never upload a share.
fixtures={};requests=[];unexpected=[]
class FixtureServer(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass  # Never log auth headers or browser data.
 def do_POST(self):
  unexpected.append({'method':'POST','path':self.path});self.send_error(405)
 def do_GET(self):
  requests.append(self.path)
  if self.path.startswith('/api/shares/'):
   identifier=self.path.rsplit('/',1)[-1]
   if identifier not in fixtures:self.send_error(404);return
   body=json.dumps({'id':identifier,'name':'Local fixture only','data':fixtures[identifier]}).encode();kind='application/json'
  elif self.path.startswith(('/folder/','/space/')):
   body=b'<!doctype html><title>Local share fixture</title><p>Local transport fixture; no uploaded share.</p>';kind='text/html'
  elif self.path in ['/web/a','/web/b']:
   label='Safe A' if self.path.endswith('/a') else 'Safe B'
   body=('<!doctype html><title>'+label+'</title><p>Owned loopback website fixture</p>').encode();kind='text/html'
  elif self.path=='/favicon.ico':self.send_error(404);return
  else:unexpected.append({'method':'GET','path':self.path});self.send_error(404);return
  self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),FixtureServer)
server.daemon_threads=True
base_url='http://127.0.0.1:'+str(server.server_port)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
# Synthetic preferences only. The normal client derives its fetch destination
# and share-page recognition from this supported server setting.
prefs['zen.share.base-url']=base_url;prefs['zen.share.secret-key']=''
(profile/'user.js').write_text('\n'.join('user_pref(%s, %s);'%(json.dumps(k),json.dumps(v)) for k,v in prefs.items()))
def state():
 return js("""return {tabs:gBrowser.tabs.map(t=>t.id).sort(),folders:[...document.querySelectorAll('zen-folder')].map(f=>f.id).sort(),spaces:gZenWorkspaces.getWorkspaces().map(s=>s.uuid).sort(),sessions:Services.prefs.getStringPref('zen.terminal.sessions','{}'),recipes:Services.prefs.getStringPref('zen.terminal.containerRecipes','{}')};""")
def host_tab():
 js("window.shareProofHost=gBrowser.addTrustedTab('about:blank');gBrowser.selectedTab=shareProofHost;")
def navigate(identifier,kind="folder"):
 js('shareProofHost.linkedBrowser.loadURI(Services.io.newURI(arguments[0]),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});',[base_url+'/'+kind+'/'+identifier])
def overlay_status():
 return js('return shareProofHost.linkedBrowser._zenShareOverlay?.querySelector(".zen-share-overlay-status")?.getAttribute("data-l10n-id");')

def click_import_confirmation(double=False):
 # Fresh-profile update sweep is inserted from requestIdleCallback and removed
 # after its real 350ms animation +80ms delay. Never delete it or force-click.
 def ready_to_click():
  return js("""const b=shareProofHost.linkedBrowser._zenShareOverlay?.querySelector('.zen-share-overlay-add');
   if(!b||b.hidden||b.disabled||document.querySelector('#zen-update-animation,#zen-update-animation-border'))return false;
   const r=b.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;
   if(r.width<=0||r.height<=0||x<0||y<0||x>=innerWidth||y>=innerHeight)return false;
   const top=document.elementFromPoint(x,y);return top===b||b.contains(top);""")
 for attempt in range(3):
  wait(ready_to_click,'real import button hit-test after transient startup sweep',timeout=20)
  try:
   button=m.find_element(By.CSS_SELECTOR,'.zen-share-overlay-add:not([hidden])')
   if double:
    point=js('const r=arguments[0].getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};',[button])
    # Real W3C input, no handler calls. Disabled/removed button must not import
    # a second workspace. Both clicks remain within this owned test window.
    m.actions.sequence('pointer','share-confirm',{'pointerType':'mouse'}).pointer_move(int(point['x']),int(point['y'])).pointer_down().pointer_up().pause(30).pointer_down().pointer_up().perform()
    m.actions.release()
   else:button.click()
   return
  except ElementClickInterceptedException as error:
   # A late idle callback can start after the hit-test. Retry only this known
   # transient overlay; any other interception remains an actual test failure.
   if 'zen-update-animation' not in str(error) or attempt==2:raise
 raise AssertionError('Native import confirmation was never clicked')

failure=None
try:
 start()
 assert js('return Services.appinfo.platformVersion;')=='156.0'
 assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')==str(home/'app-data')
 wait(lambda:js('return !!window.gZenShareManager;'),'actual share manager')
 record('owned Firefox156 process/profile; loopback transport only; unmodified production share manager/client')
 safe={'shared':{'type':'folder','name':'Local safe import '+uuid.uuid4().hex[:8],'items':[{'type':'tab','url':base_url+'/web/a','label':'Safe A'},{'type':'tab','url':base_url+'/web/b','label':'Safe B'}]}}
 fixtures['SAFE-0000-0000-0001']=safe
 host_tab();before=state();navigate('SAFE-0000-0000-0001')
 wait(lambda:js('const b=shareProofHost.linkedBrowser._zenShareOverlay?.querySelector(".zen-share-overlay-add");return b&&!b.hidden&&!b.disabled&&b.getBoundingClientRect().width>0;'),'rendered import confirmation')
 assert state()==before,'Preview mutated browser folders/tabs/jobs before confirmation'
 assert js('return shareProofHost.linkedBrowser._zenShareOverlay.querySelector(".zen-share-overlay-badge-title").textContent;')==safe['shared']['name']
 screen('share-import-preview')
 # Marionette performs a real click on the actual rendered native overlay button.
 click_import_confirmation()
 wait(lambda:js('return !shareProofHost.isConnected;'),'accepted share closes preview host')
 imported=js('const f=[...document.querySelectorAll("zen-folder")].find(f=>f.label===arguments[0]);if(!f)return null;window.shareProofFolder=f;window.shareProofTabs=f.tabs.filter(t=>!t.hasAttribute("zen-empty-tab"));return {id:f.id,tabs:shareProofTabs.map(t=>({id:t.id,pinned:t.pinned,terminal:t.hasAttribute("zen-terminal-tab"),container:Number(t.getAttribute("usercontextid")||0)}))};',[safe['shared']['name']])
 assert imported and len(imported['tabs'])==2,imported
 assert all(t['pinned'] and not t['terminal'] and t['container']==0 for t in imported['tabs']),imported
 after=state();assert set(after['folders'])-set(before['folders'])=={imported['id']}
 assert after['spaces']==before['spaces'] and after['sessions']==before['sessions'] and after['recipes']==before['recipes']
 for i,url in enumerate([base_url+'/web/a',base_url+'/web/b']):
  js('gBrowser.selectedTab=shareProofTabs[arguments[0]];',[i]);wait(lambda:js('return gBrowser.selectedBrowser.currentURI.spec;')==url,'safe imported website URL')
  wait(lambda:url.removeprefix(base_url) in requests,'safe local website fetched')
 record('actual preview is mutation-free; real confirm creates one folder with two pinned ordinary website tabs',imported)
 screen('share-import-created')
 # Put a safe tab before the malicious nested item: rejecting only late while
 # already creating the first child would be caught by the state snapshot.
 bad_urls=['chrome://browser/content/zen-terminal/terminal.xhtml?session='+str(uuid.uuid4())+'&userContextId=1','javascript:throw new Error("must not execute")','file:///tmp/zen-share-must-not-open','data:text/html,blocked']
 for index,url in enumerate(bad_urls):
  doc=copy.deepcopy(safe);doc['shared']['name']='Rejected nested '+str(index)
  doc['shared']['items'].append({'type':'folder','name':'Nested bad child','items':[{'type':'tab','url':url}]})
  identifier='BAD0-0000-0000-'+str(index+1).zfill(4);fixtures[identifier]=doc
  host_tab();before=state();navigate(identifier)
  wait(lambda:overlay_status()=='zen-share-import-error-invalid-description','visible invalid share feedback')
  assert js('const b=shareProofHost.linkedBrowser._zenShareOverlay.querySelector(".zen-share-overlay-add");return b.hidden&&b.disabled;')
  assert state()==before,'Invalid nested payload partially mutated browser state'
  record('actual fetched nested '+url.split(':')[0]+' payload rejected before import mutation')
  js('gBrowser.removeTab(shareProofHost,{animate:false});')
 metadata=copy.deepcopy(safe)
 metadata['shared']['items'][0]['zenTerminalSession']=str(uuid.uuid4())
 fixtures['META-0000-0000-0001']=metadata
 host_tab();before=state();navigate('META-0000-0000-0001')
 wait(lambda:overlay_status()=='zen-share-import-error-invalid-description','unknown terminal metadata rejected by real schema')
 assert state()==before
 assert js('const b=shareProofHost.linkedBrowser._zenShareOverlay.querySelector(".zen-share-overlay-add");return b.hidden&&b.disabled;')
 record('actual fetched web URL with terminal-session metadata rejected before mutation')
 js('gBrowser.removeTab(shareProofHost,{animate:false});')
 if args.extended:
  exact_metadata=copy.deepcopy(safe)
  exact_metadata['shared']['items'][0].update({'zenTerminalSessionId':str(uuid.uuid4()),'zenTerminalOwnership':{'sessionId':str(uuid.uuid4()),'userContextId':1}})
  fixtures['META-0000-0000-0002']=exact_metadata
  host_tab();before=state();navigate('META-0000-0000-0002')
  wait(lambda:overlay_status()=='zen-share-import-error-invalid-description','actual terminal storage key names rejected')
  assert state()==before
  assert js('const b=shareProofHost.linkedBrowser._zenShareOverlay.querySelector(".zen-share-overlay-add");return b.hidden&&b.disabled;')
  record('real schema refuses actual terminal session/ownership key names on an otherwise safe web tab')
  js('gBrowser.removeTab(shareProofHost,{animate:false});')
  baseline=state();cancel_doc=copy.deepcopy(safe);cancel_doc['shared']['name']='Dismissed preview only'
  fixtures['CANC-0000-0000-0001']=cancel_doc
  host_tab();host_id=js('return shareProofHost.id;');navigate('CANC-0000-0000-0001')
  wait(lambda:js('const b=shareProofHost.linkedBrowser._zenShareOverlay?.querySelector(".zen-share-overlay-add");return b&&!b.hidden&&!b.disabled;'),'cancelable preview ready')
  pending=state();assert set(pending['tabs'])==set(baseline['tabs'])|{host_id}
  assert all(pending[key]==baseline[key] for key in ['folders','spaces','sessions','recipes'])
  # There is no Cancel button in this production overlay; closing the preview
  # is the actual available cancel action. Use the browser shortcut, not removeTab.
  js('window.focus();gBrowser.selectedTab=shareProofHost;')
  m.actions.sequence('key','share-cancel').key_down(Keys.META).key_down('w').key_up('w').key_up(Keys.META).perform();m.actions.release()
  wait(lambda:js('return !shareProofHost.isConnected;'),'actual Cmd+W dismisses preview')
  assert state()==baseline
  record('actual preview close cancels import with no folder/workspace/tab/job mutation')
  space_name='Safe imported workspace '+uuid.uuid4().hex[:8]
  fixtures['SPAC-0000-0000-0001']={'shared':{'type':'space','name':space_name,'items':[{'type':'tab','url':base_url+'/web/a','label':'Workspace safe A','isPinned':False},{'type':'folder','name':'Imported outer','items':[{'type':'folder','name':'Imported nested','items':[{'type':'tab','url':base_url+'/web/b','label':'Nested safe B'}]}]}]}}
  host_tab();before=state();navigate('SPAC-0000-0000-0001','space')
  wait(lambda:js('const b=shareProofHost.linkedBrowser._zenShareOverlay?.querySelector(".zen-share-overlay-add");return b&&!b.hidden&&!b.disabled;'),'workspace preview ready')
  assert state()==before
  click_import_confirmation(double=True)
  wait(lambda:js('return !shareProofHost.isConnected;'),'workspace import finishes')
  after=state();new_spaces=set(after['spaces'])-set(before['spaces']);assert len(new_spaces)==1,new_spaces
  new_space=next(iter(new_spaces));assert len(set(after['folders'])-set(before['folders']))==2
  imported_space=js("""const id=arguments[0];const space=gZenWorkspaces.getWorkspaces().find(s=>s.uuid===id);const folders=[...document.querySelectorAll('zen-folder')].filter(f=>f.getAttribute('zen-workspace-id')===id);const outer=folders.find(f=>f.label==='Imported outer'),nested=folders.find(f=>f.label==='Imported nested');const tabs=gBrowser.tabs.filter(t=>t.getAttribute('zen-workspace-id')===id&&!t.hasAttribute('zen-empty-tab'));return {name:space?.name,nested:!!outer&&!!nested&&outer.contains(nested),tabs:tabs.map(t=>({label:t.label,terminal:t.hasAttribute('zen-terminal-tab'),container:Number(t.getAttribute('usercontextid')||0)}))};""",[new_space])
  assert imported_space['name']==space_name and imported_space['nested'],imported_space
  assert len(imported_space['tabs'])==2 and all(not tab['terminal'] and tab['container']==0 for tab in imported_space['tabs']),imported_space
  assert after['sessions']==before['sessions'] and after['recipes']==before['recipes']
  record('real rapid double activation imports exactly one safe workspace with genuine nested folder and two web tabs',imported_space)
  screen('share-workspace-nested-created')
 assert not unexpected,unexpected
 assert sum(path.startswith('/api/shares/') for path in requests)==(9 if args.extended else 6),requests
 results.append({'test':'external sharing service/account authentication/upload','result':'not_run','detail':'Local loopback transport fixture only; real production parsing, validation, rendered confirmation and importer exercised unchanged.'})
except Exception as error:
 failure=repr(error)
 try:screen('share-import-failure')
 except Exception:pass
 raise
finally:
 (proof/(args.label+'-share-import.json')).write_text(json.dumps({'app':str(args.app),'scope':'Unmodified production native share client/validation/UI/importer; only service transport replaced by loopback fixture; no uploads or account services','results':results,'failure':failure,'run':str(run),'requests':requests,'unexpected_requests':unexpected},indent=2)+'\n')
 if m:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);')
  except Exception:pass
 if process and process.poll() is None:
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
 server.shutdown();server.server_close();thread.join(timeout=3)
 log.close()
