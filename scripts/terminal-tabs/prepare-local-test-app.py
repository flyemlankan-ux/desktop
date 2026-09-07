#!/usr/bin/env python3
"""Overlay terminal changes onto a disposable OFFICIAL Zen 1.22b copy.
This exercises the real current Mac engine, but is NOT a fresh release build.
Never edits /Applications, the original browser, or a real user profile.
"""
import argparse
import io
import struct
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
data = base.read_bytes()
if data[4:8] == b'PK\x01\x02':
    # Mozilla's optimized ZIP stores its directory first. Move a copy to the
    # end for Python's standard ZIP reader, retaining every local-file offset.
    footer = list(struct.unpack('<4s4H2IH', data[-22:]))
    assert footer[0] == b'PK\x05\x06' and footer[-1] == 0
    directory_size, directory_offset = footer[5:7]
    assert directory_offset == 4
    directory = data[directory_offset:directory_offset + directory_size]
    footer[6] = len(data) - 22
    data = data[:-22] + directory + struct.pack('<4s4H2IH', *footer)
with zipfile.ZipFile(io.BytesIO(data)) as archive:
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
    fixture = root / 'scripts/terminal-tabs/fixtures/firefox155-settings' / rel
    dest.write_bytes(fixture.read_bytes())
    patch_path = root / 'src' / rel.parent / patch_name
    baseline_patch = subprocess.run(['git', 'show', '1.22b:' + str(patch_path.relative_to(root))], cwd=root, capture_output=True)
    if baseline_patch.returncode == 0:
        subprocess.run(['patch', '--batch', '--fuzz=0', '-p1'], input=baseline_patch.stdout, cwd=engine, check=True)
    assert dest.read_bytes() == entries[candidates[0]], f'Official bundled source differs from pinned fixture: {relative}'
    dest.write_bytes(fixture.read_bytes())
    subprocess.run(['patch', '--batch', '--fuzz=0', '-p1'], input=patch_path.read_bytes(), cwd=engine, check=True)
    entries[candidates[0]] = dest.read_bytes()

for name in ['ZenPreloadedScripts.js', 'zen-sets.js']:
    entries[prefix + name] = (root / 'src/zen/common' / name).read_bytes()

entries[prefix + 'ZenUIManager.mjs'] = (root / 'src/zen/common/modules/ZenUIManager.mjs').read_bytes()

# The native popup's shape comes from this stable checkout's committed baseline.
old = subprocess.check_output(['git', 'show', '1.22b:src/browser/base/content/zen-panels/popups.inc'], cwd=root).decode()
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
# Disk-image Finder metadata is not code and prevents a valid new signature.
# Remove only these two attributes, only inside the disposable copy.
for attribute in ('com.apple.FinderInfo', 'com.apple.ResourceFork'):
    subprocess.run(['xattr', '-dr', attribute, str(app)], check=True)
# Ad-hoc signing applies only to this disposable copy; never weaken system policy.
subprocess.run(['codesign', '--force', '--deep', '--sign', '-', '--preserve-metadata=entitlements', str(app)], check=True)
# Official Apple-team-only claims cannot transfer to an ad-hoc test identity.
# Keep ordinary browser capabilities, never impersonate the official signing team.
entitlements = plistlib.loads(subprocess.check_output(['codesign', '-d', '--entitlements', ':-', str(source)], stderr=subprocess.DEVNULL))
for restricted in ('com.apple.application-identifier', 'com.apple.developer.web-browser.public-key-credential', 'com.apple.developer.team-identifier'):
    entitlements.pop(restricted, None)
entitlements_file = test / 'local-test-entitlements.plist'
entitlements_file.write_bytes(plistlib.dumps(entitlements))
subprocess.run(['codesign', '--force', '--sign', '-', '--entitlements', str(entitlements_file), str(app)], check=True)
subprocess.run(['codesign', '--verify', '--deep', '--strict', '--verbose=2', str(app)], check=True)
print('Updated disposable stable 1.22b integration app:', app)
print('Evidence scope: official current engine plus local overlay, NOT a fresh compiled release.')
