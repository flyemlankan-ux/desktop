#!/usr/bin/env python3
"""Actual Mac saved-setup journey; synthetic data only. Does NOT test the OS folder picker."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket as net_socket
import subprocess
import time
import uuid
from marionette_driver.marionette import Marionette

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--app', required=True, type=Path)
parser.add_argument('--label', default='saved-setups')
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
run = root / '.terminal-test' / ('saved-setups-' + uuid.uuid4().hex[:8])
home, profile = run / 'home', run / 'profile'
home.mkdir(parents=True)
profile.mkdir()
proof = root / 'docs/proof/2026-09-19'
proof.mkdir(parents=True, exist_ok=True)
folder_a = home / "Project 雪 ' $(literal); `name` "
folder_b = home / 'Second project'
folder_a.mkdir()
folder_b.mkdir()
(home / '.zshenv').write_text('export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin\n')
(home / '.zshrc').write_text("PROMPT='setup-proof> '\nRPROMPT=''\n")
with net_socket.socket() as listener:
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
prefs = {
    'marionette.port': port,
    'browser.shell.checkDefaultBrowser': False,
    'browser.startup.page': 0,
    'zen.welcome-screen.seen': True,
    'app.update.disabledForTesting': True,
    'app.update.auto': False,
    'app.update.enabled': False,
    'browser.startup.homepage': 'about:blank',
    'browser.aboutwelcome.enabled': False,
    'privacy.userContext.enabled': True,
    'privacy.userContext.ui.enabled': True,
}
(profile / 'user.js').write_text('\n'.join(f'user_pref({json.dumps(k)}, {json.dumps(v)});' for k, v in prefs.items()))
env = dict(os.environ, MOZ_APP_DATA=str(home / 'app-data'), MOZ_LOCAL_APP_DATA=str(home / 'local-app-data'), HOME=str(home), ZDOTDIR=str(home), SHELL='/bin/zsh', PATH='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin', MOZ_NO_REMOTE='1')
for key in list(env):
    if key.startswith(('XRE_PROFILE_', 'SELECTABLE_PROFILE_RESET_')) or key in {'XRE_RESTARTED_BY_PROFILE_MANAGER', 'MOZ_RESET_PROFILE_RESTART', 'MOZ_LEGACY_PROFILES'}:
        env.pop(key, None)
exe = args.app.resolve() / 'Contents/MacOS/zen-terminal'
if not exe.is_file():
    raise SystemExit('Expected a separate Zen Terminal app; no browser launched.')
tmux_exe = shutil.which('tmux', path=env['PATH'])
if not tmux_exe:
    raise SystemExit('tmux required; no browser launched.')
log = (run / 'gecko.log').open('w')
process = None
m = None
socket = None
results = []
session_ids = []
cid = None

def wait(check, label, timeout=30):
    end = time.monotonic() + timeout
    error = None
    while time.monotonic() < end:
        try:
            value = check()
            if value:
                return value
        except Exception as exc:
            error = exc
        time.sleep(.1)
    raise AssertionError(f'Timed out: {label}; {error}')

def js(source, values=None):
    return m.execute_script(source, script_args=values or [])

def record(name, detail=True):
    results.append({'test': name, 'result': 'pass', 'detail': detail})
    print('PASS', name, detail, flush=True)

def tmux(*values):
    assert socket and socket.startswith('zen-terminal-p')
    return subprocess.run([tmux_exe, '-L', socket, *values], capture_output=True, text=True, timeout=8)

def saved():
    m.set_context('chrome')
    return js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs").getTerminalContainerRecipe(arguments[0]);', [cid])

def deep(selector):
    return js('const find=root=>{const match=root.querySelector(arguments[0]);if(match)return match;for(const node of root.querySelectorAll("*")){if(node.shadowRoot){const match=find(node.shadowRoot);if(match)return match;}}return null;};return find(document);', [selector])

def settings():
    m.switch_to_frame()
    m.set_context('chrome')
    js('if(!window.__savedSetupSettingsTab || !window.__savedSetupSettingsTab.isConnected){window.__savedSetupSettingsTab=gBrowser.addTab("about:preferences#containers",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});}gBrowser.selectedTab=window.__savedSetupSettingsTab;')
    m.set_context('content')
    for handle in m.window_handles:
        m.switch_to_window(handle)
        if m.get_url().startswith('about:preferences'):
            break
    wait(lambda: deep('[data-l10n-id="containers-add-button2"]'), 'Settings controls')
    wait(lambda: js('return document.readyState === "complete" && Boolean(window.gSubDialog);'), 'Settings initialization')
    # Native Settings controls render asynchronously. Their presence precedes
    # completed custom-element updates and event wiring on a fresh profile.
    control = deep('[data-l10n-id="containers-add-button2"]')
    update = m.execute_async_script('const done=arguments[arguments.length-1];Promise.resolve(arguments[0].updateComplete).then(()=>done({ready:true}),error=>done({error:String(error)}));', script_args=[control])
    assert update.get('ready'), update
    wait(lambda: js('const e=arguments[0].shadowRoot?.querySelector("button")||arguments[0];const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&!e.disabled;', [control]), 'Visible enabled Settings Add button')
    time.sleep(.5)  # Same native first-paint/event-settling allowance as main Mac proof.

def dialog(edit=False):
    settings()
    selector = f'[action="edit"][value="{cid}"]' if edit else '[data-l10n-id="containers-add-button2"]'
    button = wait(lambda: deep(selector), 'Edit/Add native setup button')
    js('return arguments[0].shadowRoot?.querySelector("button") || arguments[0];', [button]).click()
    frame = wait(lambda: js('return [...document.querySelectorAll("browser.dialogFrame")].find(x=>x.contentDocument?.documentURI==="chrome://browser/content/preferences/dialogs/containers.xhtml");'), 'setup dialog')
    m.execute_async_script('const done=arguments[arguments.length-1];arguments[0]._dialogReady.then(()=>done(true));', script_args=[frame])
    m.switch_to_frame(frame)
    wait(lambda: js('return document.readyState==="complete" && !!document.querySelector("dialog")?.getButton("accept");'), 'Dialog document and native accept control')
    wait(lambda: m.find_element('id', 'zen-terminal-starting-directory'), 'Starting folder field')
    return frame

def field(value):
    element = m.find_element('id', 'zen-terminal-starting-directory')
    element.clear()
    element.send_keys(str(value))

def close_dialog(action):
    js('document.querySelector("dialog").getButton(arguments[0]).click();', [action])
    m.switch_to_frame()
    m.set_context('chrome')

def open_terminal():
    m.set_context('chrome')
    js('const popup=document.querySelector("#zenCreateBrowserContainerTabMenu menupopup");gZenTerminalTabs.populateUnifiedContainerMenu({target:popup});const item=popup.querySelector(`[data-usercontextid="${arguments[0]}"]`);if(!item)throw new Error("Setup absent from unified menu");item.doCommand();', [cid])
    sid = wait(lambda: js('return gBrowser.selectedTab.getAttribute("zen-terminal-session-id");'), 'new terminal session ID')
    session_ids.append(sid)
    wait(lambda: js('return gBrowser.selectedBrowser.contentDocument?.getElementById("zen-terminal-surface")?.hasAttribute("terminal-ready");'), 'terminal ready')
    pid = wait(lambda: tmux('display-message', '-p', '-t', 'zt_' + sid, '#{pane_pid}').stdout.strip(), 'shell PID')
    assert pid.isdigit()
    return sid, pid

def cwd(sid):
    return tmux('display-message', '-p', '-t', 'zt_' + sid, '#{pane_current_path}').stdout.rstrip('\n')

try:
    process = subprocess.Popen([str(exe), '-no-remote', '-marionette', '--remote-allow-system-access', '-profile', str(profile)], env=env, stdout=log, stderr=log)
    m = Marionette(host='127.0.0.1', port=port, socket_timeout=30, startup_timeout=30)
    m.raise_for_port(timeout=30)
    m.start_session()
    m.set_context('chrome')
    assert js('return Services.appinfo.processID;') == process.pid
    assert Path(js('return Services.dirsvc.get("ProfD",Ci.nsIFile).path;')).resolve() == profile.resolve()
    assert js('return Services.dirsvc.get("UAppData",Ci.nsIFile).path;') == str(home / 'app-data')
    wait(lambda: js('return Boolean(window.gZenTerminalTabs && gBrowserInit.delayedStartupFinished);'), 'browser ready')
    socket = js('return ChromeUtils.importESModule("chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs").getTerminalTmuxSocket();')
    record('App owns only disposable profile and app-data')
    dialog()
    m.find_element('id', 'zen-container-kind-terminal').click()
    name = wait(lambda: js('return document.querySelector("moz-input-text[name=name]")?.shadowRoot?.querySelector("input");'), 'name input')
    name.send_keys('Saved Setup Journey')
    field(home / 'missing-folder')
    js('document.querySelector("dialog").getButton("accept").click();')
    wait(lambda: m.find_element('id', 'zen-terminal-recipe-error').is_displayed(), 'missing folder feedback')
    assert js('return ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService.getPublicIdentities().every(x=>x.name!=="Saved Setup Journey");')
    record('Missing folder keeps editor open and creates nothing')
    field(folder_a)
    m.find_element('id', 'zen-terminal-add-step').click()
    m.find_element('css selector', '#zen-terminal-recipe-steps input').send_keys('printf "%s\\n" "$PWD" >> "$HOME/setup-cwd-proof"')
    layout = js('return [...document.querySelectorAll("#containerEditorHost,.container-editor,#zen-terminal-container-fields,#zen-terminal-starting-directory")].map(el=>({id:el.id,width:el.clientWidth,scroll:el.scrollWidth}));')
    # A long text INPUT is allowed to scroll its value; the containing form is not.
    assert all(x['scroll'] <= x['width'] + 1 for x in layout if x['id'] != 'zen-terminal-starting-directory'), layout
    (proof / (args.label + '-folder-dialog.png')).write_bytes(m.screenshot(format='binary'))
    record('Rendered folder editor contains long literal path without sideways form overflow', layout)
    close_dialog('accept')
    cid = wait(lambda: js('return ChromeUtils.importESModule("moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs").ContextualIdentityService.getPublicIdentities().find(x=>x.name==="Saved Setup Journey")?.userContextId;'), 'saved setup identity')
    assert saved()['recipe']['startingDirectory'] == str(folder_a)
    record('Native Save persists literal Unicode, spaces and shell punctuation')
    first, pid = open_terminal()
    wait(lambda: (home / 'setup-cwd-proof').is_file(), 'startup cwd marker')
    assert (home / 'setup-cwd-proof').read_text() == str(folder_a) + '\n'
    assert Path(cwd(first)).resolve() == folder_a.resolve()
    record('Real shell and startup command run in the exact chosen folder')
    second, second_pid = open_terminal()
    assert first != second and pid != second_pid
    wait(lambda: (home / 'setup-cwd-proof').read_text().count('\n') == 2, 'two startup markers')
    record('Opening saved setup twice creates independent shells, startup once each')
    dialog(edit=True)
    assert js('return document.getElementById("zen-terminal-starting-directory").value;') == str(folder_a)
    field(folder_b)
    close_dialog('cancel')
    assert saved()['recipe']['startingDirectory'] == str(folder_a)
    record('Edit then Cancel preserves previously saved folder')
    dialog(edit=True)
    assert js('return document.getElementById("zen-terminal-starting-directory").value;') == str(folder_a)
    field(folder_b)
    close_dialog('accept')
    assert saved()['recipe']['startingDirectory'] == str(folder_b)
    assert tmux('display-message', '-p', '-t', 'zt_' + first, '#{pane_pid}').stdout.strip() == pid
    assert Path(cwd(first)).resolve() == folder_a.resolve()
    third, _ = open_terminal()
    assert Path(cwd(third)).resolve() == folder_b.resolve()
    record('Edited folder applies only to new tabs; old job and cwd remain unchanged')
    dialog(edit=True)
    assert js('return document.getElementById("zen-terminal-starting-directory").value;') == str(folder_b)
    close_dialog('cancel')
    record('Reopened native editor shows saved replacement folder')
    (proof / (args.label + '-terminal.png')).write_bytes(m.screenshot(format='binary'))
except Exception as error:
    results.append({'test': 'saved-setup native journey', 'result': 'fail', 'detail': str(error)})
    print('FAIL', repr(error), flush=True)
    if m:
        try:
            (proof / (args.label + '-failure.png')).write_bytes(m.screenshot(format='binary'))
        except Exception:
            pass
    raise
finally:
    if m:
        try:
            m.switch_to_frame()
            m.set_context('chrome')
            js('Services.startup.quit(Ci.nsIAppStartup.eAttemptQuit);return true;')
        except Exception:
            pass
    if process and process.poll() is None:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    # Socket is derived from this newly created profile; never a founder/shared socket.
    if socket:
        subprocess.run([tmux_exe, '-L', socket, 'kill-server'], capture_output=True, timeout=8)
    log.close()
    (proof / (args.label + '-results.json')).write_text(json.dumps({'app': str(args.app), 'test_data': 'synthetic profile and folders only', 'results': results, 'native_picker_tested': False, 'log': str(run / 'gecko.log')}, indent=2) + '\n')
