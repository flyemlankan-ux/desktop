#!/usr/bin/env python3
"""Actual synthetic Zen155 -> fork156 profile migration. Never personal profiles.
No launch occurs on --help. Parent exclusively schedules native UI execution.
"""
import argparse, configparser, hashlib, importlib.util, json, os, plistlib, re
import socket, subprocess, sys, tempfile, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from marionette_driver.marionette import Marionette

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-app',required=True,type=Path)
p.add_argument('--target-app',required=True,type=Path)
p.add_argument('--label',default='synthetic-native-migration')
a=p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9_-]+',a.label):p.error('Invalid proof label')
root=Path(__file__).resolve().parents[2];source_app=a.source_app.resolve();target_app=a.target_app.resolve()
if not source_app.is_relative_to((root/'.terminal-test').resolve()) or source_app.name!='Official Zen.app':p.error('Source must be the copied Official Zen.app under .terminal-test, not the installed original')
for app,engine,binary in [(source_app,'155.0.1','zen'),(target_app,'156.0','zen-terminal')]:
 if not (app/'Contents/MacOS'/binary).is_file():p.error('Expected executable missing')
 if 'Milestone='+engine not in (app/'Contents/Resources/platform.ini').read_text().splitlines():p.error('Unexpected source or target engine; no launch')
if plistlib.loads((source_app/'Contents/Info.plist').read_bytes()).get('CFBundleIdentifier')!='app.zen-browser.zen':p.error('Unexpected official source identity')
proof=root/'docs/proof/2026-09-19';proof.mkdir(parents=True,exist_ok=True)
report=proof/(a.label+'-results.json')
if report.exists():p.error('Use a new label; prior evidence must be preserved')
# Copy utility deliberately forbids destinations inside a repository.
run=Path(tempfile.mkdtemp(prefix='zen-synthetic-native-migration-')).resolve();run.chmod(0o700)
source=run/'source-app-data';source.mkdir(mode=0o700);destination=run/'copied-app-data'
source_home=run/'source-home';target_home=run/'target-home';source_home.mkdir();target_home.mkdir()
results=[];process=None;client=None;owned=False;browser_log=None;failure=None;current_port=None
seed_cookies=True
fixtures={name:{'token':uuid.uuid4().hex,'password':'synthetic-only-'+uuid.uuid4().hex} for name in ['first','second']}
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  name=self.path.strip('/').split('?')[0]
  if name not in fixtures:self.send_error(404);return
  fixture=fixtures[name];body=('<!doctype html><title>Migration '+name+'</title><h1>Synthetic '+fixture['token']+'</h1>').encode()
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));
  if seed_cookies:self.send_header('Set-Cookie','migration_fixture='+fixture['token']+'; Max-Age=86400; Path=/; SameSite=Lax')
  self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
origin='http://127.0.0.1:'+str(server.server_port)
spec=importlib.util.spec_from_file_location('migration',root/'scripts/terminal-tabs/copy-zen-profiles.py');migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
def record(name,details=True):results.append({'test':name,'result':'pass','detail':details});print('PASS',name,details,flush=True)
def wait(check,label,timeout=35):
 end=time.monotonic()+timeout;last=None
 while time.monotonic()<end:
  try:
   value=check()
   if value:return value
  except Exception as exc:last=exc
  time.sleep(.1)
 raise AssertionError('Timed out '+label+'; '+str(last))
def js(code,args=None):return client.execute_script(code,script_args=args or [])
def asyncjs(code,args=None):
 value=client.execute_async_script('const done=arguments[arguments.length-1];(async()=>{'+code+'})().then(value=>done({value}),error=>done({error:String(error)}));',script_args=args or [])
 assert 'error' not in value,value.get('error');return value.get('value')
def prefs_file(profile,port):
 prefs={'marionette.port':port,'browser.shell.checkDefaultBrowser':False,'browser.startup.page':3,'browser.startup.homepage':'about:blank','zen.welcome-screen.seen':True,'browser.aboutwelcome.enabled':False,'app.update.disabledForTesting':True,'app.update.enabled':False,'browser.sessionstore.resume_from_crash':True,'privacy.userContext.enabled':True,'privacy.userContext.ui.enabled':True}
 (profile/'user.js').write_text('\n'.join('user_pref(%s,%s);'%(json.dumps(k),json.dumps(v)) for k,v in prefs.items()))
def launch(app,profile,data,home,binary):
 global process,client,owned,browser_log,current_port
 assert process is None
 with socket.socket() as listener:listener.bind(('127.0.0.1',0));current_port=listener.getsockname()[1]
 prefs_file(profile,current_port)
 env=dict(os.environ,HOME=str(home),ZDOTDIR=str(home),MOZ_APP_DATA=str(data),MOZ_LOCAL_APP_DATA=str(home/'local-app-data'),MOZ_NO_REMOTE='1')
 for key in list(env):
  if key.startswith(('XRE_PROFILE_','SELECTABLE_PROFILE_RESET_')) or key in {'XRE_RESTARTED_BY_PROFILE_MANAGER','MOZ_RESET_PROFILE_RESTART','MOZ_LEGACY_PROFILES'}:env.pop(key,None)
 browser_log=(run/(binary+'-'+profile.name+'.log')).open('w')
 process=subprocess.Popen([str(app/'Contents/MacOS'/binary),'-no-remote','-marionette','--remote-allow-system-access','-profile',str(profile)],env=env,stdout=browser_log,stderr=browser_log)
 client=Marionette(host='127.0.0.1',port=current_port,socket_timeout=40,startup_timeout=40);client.raise_for_port(timeout=40);client.start_session();client.set_context('chrome')
 assert js('return Services.appinfo.processID;')==process.pid
 assert Path(js('return Services.dirsvc.get("ProfD",Ci.nsIFile).path;')).resolve()==profile.resolve()
 assert Path(js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;')).resolve()==data.resolve()
 owned=True
 wait(lambda:js('return Boolean(gBrowserInit.delayedStartupFinished && window.gZenWorkspaces?.getWorkspaces()?.length);'),'owned browser/workspaces ready')
def stop(clean_required=True):
 global process,client,owned,browser_log
 if process is None:return
 if client and owned and process.poll() is None:
  try:js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);return true;')
  except Exception:pass
 forced=False
 try:process.wait(timeout=25)
 except subprocess.TimeoutExpired:
  forced=True;process.terminate()
  try:process.wait(timeout=5)
  except subprocess.TimeoutExpired:process.kill();process.wait()
 code=process.returncode;process=None;client=None;owned=False
 if browser_log:browser_log.close();browser_log=None
 if clean_required:assert not forced and code==0,'Source/target must close cleanly for persistence proof'
def hashes(folder):
 return {str(path.relative_to(folder)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.rglob('*')) if path.is_file() and not path.is_symlink()}
try:
 for name,fixture in fixtures.items():
  profile=source/'Profiles'/name;profile.mkdir(parents=True);url=origin+'/'+name;fixture['url']=url;fixture['historyUrl']=url+'?history-only'
  launch(source_app,profile,source,source_home,'zen')
  # Insert through actual source browser services, not hand-written databases.
  saved=asyncjs('''const [origin,url,name,token,password]=arguments;
 const places=ChromeUtils.importESModule('resource://gre/modules/PlacesUtils.sys.mjs').PlacesUtils;
 const bookmark=await places.bookmarks.insert({parentGuid:places.bookmarks.toolbarGuid,url,title:'Synthetic bookmark '+name});
 await places.history.insert({url:url+'?history-only',title:'Synthetic history '+name,visits:[{date:new Date(Date.now()-60000),transition:places.history.TRANSITIONS.LINK}]});
 const login=Cc['@mozilla.org/login-manager/loginInfo;1'].createInstance(Ci.nsILoginInfo);
 login.init(origin,origin,null,'synthetic-user-'+name,password,'username','password');
 const stored=await Services.logins.addLoginAsync(login);
 const cis=ChromeUtils.importESModule('moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs').ContextualIdentityService;
 const identity=cis.create('Synthetic container '+name,'briefcase','purple');
 const workspace=await gZenWorkspaces.createAndSaveWorkspace('Synthetic workspace '+name,'briefcase');
 Services.prefs.setStringPref('zen.terminal.syntheticMigrationMarker',token);
 gBrowser.selectedTab=gBrowser.addTab(url,{userContextId:identity.userContextId,triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});
 return {bookmark:bookmark.guid,login:stored.guid,container:identity.userContextId,workspace:workspace.uuid};''',[origin,url,name,fixture['token'],fixture['password']])
  fixture.update(saved)
  wait(lambda:js('return gBrowser.selectedBrowser.currentURI.spec===arguments[0] && gBrowser.selectedBrowser.contentTitle===arguments[1];',[url,'Migration '+name]),'local fixture tab loaded')
  assert asyncjs('const p=ChromeUtils.importESModule("resource://gre/modules/PlacesUtils.sys.mjs").PlacesUtils;return await p.history.hasVisits(arguments[0]);',[url])
  # Cookie belongs to the actual container used by the real local page.
  assert js('return Array.from(Services.cookies.getCookiesFromHost("127.0.0.1",{userContextId:arguments[0]})).some(c=>c.name==="migration_fixture" && c.value===arguments[1]);',[fixture['container'],fixture['token']])
  asyncjs('await ChromeUtils.importESModule("resource:///modules/sessionstore/TabStateFlusher.sys.mjs").TabStateFlusher.flush(gBrowser.selectedBrowser);Services.prefs.savePrefFile(null);return true;')
  stop()
  assert (profile/'key4.db').is_file() and (profile/'logins.json').is_file()
  encrypted=json.loads((profile/'logins.json').read_text())['logins'];assert any(x['guid']==fixture['login'] and x.get('encryptedPassword') and x.get('encryptedUsername') for x in encrypted)
  assert fixture['password'].encode() not in (profile/'logins.json').read_bytes()
  record('Official155 created and encrypted synthetic records; clean shutdown',{'profile':name,'real_services':True})
 seed_cookies=False # Restored pages must not recreate missing source cookies.
 ini=configparser.ConfigParser(interpolation=None);ini.optionxform=str;ini['General']={'StartWithLastProfile':'1','Version':'2'}
 for i,name in enumerate(fixtures):ini['Profile'+str(i)]={'Name':'Synthetic '+name,'IsRelative':'1','Path':'Profiles/'+name,'Default':'1' if i==0 else '0'}
 with (source/'profiles.ini').open('w') as stream:ini.write(stream,space_around_delimiters=False)
 before=hashes(source);real_run=subprocess.run
 def synthetic_activity_check(checked):
  assert Path(checked)==source and run in source.parents and process is None
  def only_global_guard(command,**kwargs):
   result=real_run(command,**kwargs)
   if command==['/bin/ps','-axo','pid=,comm=']:
    result.stdout='\n'.join(line for line in result.stdout.splitlines() if not(len(line.strip().split(None,1))==2 and Path(line.strip().split(None,1)[1]).name.lower() in {'zen','zen-bin'}))
   return result
  # Only synthetic test bypasses broad "any Zen running" rejection. Exact
  # source lsof, profile locks, snapshot stability and all copy checks remain.
  with mock.patch.object(migration.subprocess,'run',side_effect=only_global_guard):migration.ensure_closed(checked)
 copied=migration.copy_setup(source,destination,'155.0.1','156.0',default_profile='Synthetic first',copy=True,activity_check=synthetic_activity_check)
 assert copied['profile_count']==2 and hashes(source)==before
 record('Actual copy tool copied two closed synthetic profiles forward155 to156 without changing source',{'profiles':2,'source_files':len(before),'global_guard_difference':'only broad process-name guard bypassed; actual source locks/lsof retained'})
 for name,fixture in fixtures.items():
  launch(target_app,destination/'Profiles'/name,destination,target_home,'zen-terminal')
  wait(lambda:js('return gBrowser.tabs.some(t=>t.linkedBrowser.currentURI.spec===arguments[0] || t.getAttribute("pending") && JSON.stringify(ChromeUtils.importESModule("resource:///modules/sessionstore/SessionStore.sys.mjs").SessionStore.getTabState(t)).includes(arguments[0]));',[fixture['url']]),'restored synthetic tab')
  verified=asyncjs('''const [origin,fixture,name]=arguments;
 const places=ChromeUtils.importESModule('resource://gre/modules/PlacesUtils.sys.mjs').PlacesUtils;
 const bookmark=await places.bookmarks.fetch(fixture.bookmark);
 const logins=await Services.logins.searchLoginsAsync({origin});
 const login=logins.find(x=>x.guid===fixture.login);
 const cis=ChromeUtils.importESModule('moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs').ContextualIdentityService;
 return {bookmark:bookmark?.url.href===fixture.url,history:await places.history.hasVisits(fixture.historyUrl),
 loginDecrypted:login?.username==='synthetic-user-'+name && login?.password===fixture.password,
 container:cis.getPublicIdentities().some(x=>x.userContextId===fixture.container && x.name==='Synthetic container '+name),
 cookie:Array.from(Services.cookies.getCookiesFromHost('127.0.0.1',{userContextId:fixture.container})).some(c=>c.name==='migration_fixture' && c.value===fixture.token),
 workspace:gZenWorkspaces.getWorkspaces().some(w=>w.uuid===fixture.workspace && w.name==='Synthetic workspace '+name),
 preference:Services.prefs.getStringPref('zen.terminal.syntheticMigrationMarker')===fixture.token};''',[origin,fixture,name])
  assert all(verified.values()),verified
  assert js('return Boolean(window.gZenTerminalTabs);')
  record('Fork156 opens selected copied profile and decrypts original synthetic login',{'profile':name,'checks':verified,'selection':'explicit -profile; automatic install selection is a separate test'})
  stop();assert hashes(source)==before
 record('Source file hashes unchanged after both copied profiles opened in fork156')
except Exception as exc:
 failure=str(exc);print('FAIL',repr(exc),flush=True);raise
finally:
 stop(clean_required=False);server.shutdown();server.server_close();thread.join(timeout=5)
 report.write_text(json.dumps({'scope':'only synthetic official155 profiles and copied fork156 profiles; not personal migration proof','results':results,'failure':failure,'synthetic_data_root':str(run),'source_app':str(source_app),'target_app':str(target_app)},indent=2)+'\n')
