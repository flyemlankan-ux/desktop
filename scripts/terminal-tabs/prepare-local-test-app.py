#!/usr/bin/env python3
"""Patch ONLY a disposable copy of the saved July-4 app for fast integration tests.
This is a development test harness, never a substitute for a fresh cloud build.
"""
from pathlib import Path
import re, subprocess, zipfile
root=Path(__file__).resolve().parents[2]
test=root/'.terminal-test'
app=test/'Zen Terminal Test.app'
assert app.is_dir() and app.parent==test
base=test/'baseline-browser-omni.ja'
assert base.is_file(), 'Copy the untouched July-4 browser omni.ja first'
with zipfile.ZipFile(base) as z:
    entries={n:z.read(n) for n in z.namelist()}
prefix='chrome/browser/content/browser/'
for line in (root/'src/zen/terminal/jar.inc.mn').read_text().splitlines():
    match=re.search(r'content/browser/(\S+)\s+\(../../zen/terminal/(.+)\)', line)
    if match:entries[prefix+match[1]]=(root/'src/zen/terminal'/match[2]).read_bytes()
for name in ['ZenTerminalContainers.mjs','containers.xhtml','zen-terminal-containers.css']:
    entries.pop(prefix+'zen-terminal/'+name,None)
for rel in ['browser/components/preferences/containers.js','browser/components/preferences/dialogs/containers.js']:
    original=test/'engine-source'/Path(rel).with_suffix('.js.base')
    dest=test/'engine-source'/rel
    dest.write_bytes(original.read_bytes())
    subprocess.run(['patch','--batch','-p1'],input=(root/('src/'+rel.replace('.js','-js.patch'))).read_bytes(),cwd=test/'engine-source',check=True,stdout=subprocess.DEVNULL)
    entry=prefix+'preferences/'+('dialogs/' if '/dialogs/' in rel else '')+'containers.js'
    entries[entry]=dest.read_bytes()
entries[prefix+'zen-sets.js']=(root/'src/zen/common/zen-sets.js').read_bytes()
# Replace the exact old popup fragment, leaving the rest of native Zen untouched.
old=subprocess.check_output(['git','show','2ffbfae:src/browser/base/content/zen-panels/popups.inc'],cwd=root).decode()
new=(root/'src/browser/base/content/zen-panels/popups.inc').read_text()
old=old[old.index('<menupopup'):old.index('</menupopup>\n\n')+len('</menupopup>')]
new=new[new.index('<menupopup'):new.index('</menupopup>\n\n')+len('</menupopup>')]
page=entries[prefix+'browser.xhtml'].decode()
# Build preprocessing may indent included lines; keep this harness strict.
assert old in page, 'Old popup differs; do not patch by guessing'
entries[prefix+'browser.xhtml']=page.replace(old,new,1).encode()
archive=app/'Contents/Resources/browser/omni.ja'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name,data in entries.items(): z.writestr(name,data)
subprocess.run([str(root/'scripts/terminal-tabs/build-terminal-pty.sh'),str(app/'Contents/MacOS/zen-terminal-pty')],check=True)
print('Updated isolated local integration app:',app)
