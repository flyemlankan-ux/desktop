#!/usr/bin/env python3
"""Overlay terminal changes onto a disposable OFFICIAL Zen 1.22b copy.
This exercises the real current Mac engine, but is NOT a fresh release build.
Never edits /Applications, the original browser, or a real user profile.
"""
import argparse
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import zipfile

root = Path(__file__).resolve().parents[2]
test = root / '.terminal-test'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-app', type=Path, default=test / 'Official Zen.app')
args = parser.parse_args()
source = args.source_app.resolve()
app = test / 'Zen Terminal Test.app'
assert source.is_dir() and source != app.resolve()
assert not app.is_symlink() and app.parent.resolve() == test.resolve()
info = plistlib.loads((source / 'Contents/Info.plist').read_bytes())
assert info.get('CFBundleShortVersionString') == '1.22b', 'Only official stable 1.22b is supported'
if not app.exists():
    subprocess.run(['ditto', str(source), str(app)], check=True)
base = source / 'Contents/Resources/browser/omni.ja'
with zipfile.ZipFile(base) as archive:
    entries = {name: archive.read(name) for name in archive.namelist()}
prefix = 'chrome/browser/content/browser/'
for line in (root / 'src/zen/terminal/jar.inc.mn').read_text().splitlines():
    match = re.search(r'content/browser/(\S+)\s+\(../../zen/terminal/(.+)\)', line)
    if match:
        entries[prefix + match[1]] = (root / 'src/zen/terminal' / match[2]).read_bytes()

# Apply only the new terminal changes to native stable Settings components.
# Strict context matching deliberately rejects incompatible engine versions.
patches = [
    ('browser/components/contextualidentity/content/ContainerEditor.mjs', 'ContainerEditor-mjs.patch'),
    ('browser/components/contextualidentity/content/ContainerCreationPanel.mjs', 'ContainerCreationPanel-mjs.patch'),
    ('browser/components/preferences/config/containers.mjs', 'containers-mjs.patch'),
    ('browser/components/preferences/dialogs/containers.js', 'containers-js.patch'),
]
engine = test / 'stable-overlay-source'
for relative, patch_name in patches:
    rel = Path(relative)
    candidates = [name for name in entries if name.endswith('/' + rel.name)]
    if rel.name == 'containers.mjs':
        candidates = [name for name in candidates if '/preferences/config/' in name]
    if rel.name == 'containers.js':
        candidates = [name for name in candidates if '/preferences/dialogs/' in name]
    assert len(candidates) == 1, (relative, candidates)
    dest = engine / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(entries[candidates[0]])
    patch_path = root / 'src' / rel.parent / patch_name
    subprocess.run(['patch', '--batch', '--fuzz=0', '-p1'], input=patch_path.read_bytes(), cwd=engine, check=True)
    entries[candidates[0]] = dest.read_bytes()

for name in ['ZenPreloadedScripts.js', 'zen-sets.js']:
    entries[prefix + name] = (root / 'src/zen/common' / name).read_bytes()

# The native popup's shape comes from this stable checkout's committed baseline.
old = subprocess.check_output(['git', 'show', 'upstream/stable:src/browser/base/content/zen-panels/popups.inc'], cwd=root).decode()
new = (root / 'src/browser/base/content/zen-panels/popups.inc').read_text()
def first_popup(text):
    start = text.index('<menupopup')
    return text[start:text.index('</menupopup>\n\n', start) + len('</menupopup>')]
page = entries[prefix + 'browser.xhtml'].decode()
assert first_popup(old) in page, 'Official popup differs from stable baseline; refusing a guessed replacement'
page = page.replace(first_popup(old), first_popup(new), 1)
css = 'chrome://browser/content/zen-styles/zen-terminal-tabs.css'
if css not in page:
    # Same stylesheet declaration as the source build's zen-assets include.
    declaration = next(line for line in (root / 'src/browser/base/content/zen-assets.inc.xhtml').read_text().splitlines() if css in line)
    anchor = re.search(r'<link\b[^>]*href="chrome://browser/content/zen-styles/zen-tabs\.css"[^>]*/>', page)
    assert anchor, 'Expected native Zen tab stylesheet declaration'
    position = anchor.end()
    page = page[:position] + '\n' + declaration + page[position:]
entries[prefix + 'browser.xhtml'] = page.encode()
archive = app / 'Contents/Resources/browser/omni.ja'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
    for name, data in entries.items():
        output.writestr(name, data)
subprocess.run([str(root / 'scripts/terminal-tabs/build-terminal-pty.sh'), str(app / 'Contents/MacOS/zen-terminal-pty')], check=True)
original_executable = info['CFBundleExecutable']
exe = app / 'Contents/MacOS/zen-terminal'
if not exe.exists():
    shutil.copy2(app / 'Contents/MacOS' / original_executable, exe)
info.update(CFBundleIdentifier='app.zen-terminal.stable-local-test', CFBundleName='Zen Terminal Test', CFBundleDisplayName='Zen Terminal Test', CFBundleExecutable='zen-terminal')
(app / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
# Ad-hoc signing applies only to this disposable copy; never weaken system policy.
subprocess.run(['codesign', '--force', '--deep', '--sign', '-', '--preserve-metadata=entitlements', str(app)], check=True)
subprocess.run(['codesign', '--verify', '--deep', '--strict', '--verbose=2', str(app)], check=True)
print('Updated disposable stable 1.22b integration app:', app)
print('Evidence scope: official current engine plus local overlay, NOT a fresh compiled release.')
