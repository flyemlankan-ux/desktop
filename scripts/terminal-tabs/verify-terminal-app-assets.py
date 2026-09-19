#!/usr/bin/env python3
"""Verify real packaged resources, engine and exact shipped terminal assets."""
from pathlib import Path
import configparser
import io
import json
import plistlib
import re
import struct
import subprocess
import tempfile
import sys
import zipfile


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def open_omni(path):
    require(path.is_file(), f'Missing required packaged resources: {path.name} in {path.parent.name}')
    data = path.read_bytes()
    if data[4:8] == b"PK\x01\x02":
        # Mozilla puts the ZIP directory first. Normalize only an in-memory copy.
        footer = list(struct.unpack("<4s4H2IH", data[-22:]))
        require(footer[0] == b"PK\x05\x06" and footer[-1] == 0, "Malformed optimized ZIP directory")
        size, offset = footer[5:7]
        require(offset == 4, "Malformed optimized ZIP directory")
        directory = data[offset:offset + size]
        footer[6] = len(data) - 22
        data = data[:-22] + directory + struct.pack("<4s4H2IH", *footer)
    archive = zipfile.ZipFile(io.BytesIO(data))
    try:
        require(archive.testzip() is None, "Damaged packaged resources")
    except BaseException:
        archive.close()
        raise
    return archive


def expected_native_assets(root):
    """Compile only pinned small Firefox UI patches; compare actual shipped bytes."""
    items = [
        ('browser/components/sessionstore/SessionStore.sys.mjs', 'moz-src/browser/components/sessionstore/SessionStore.sys.mjs', 'firefox156-sessionstore'),
        ('browser/components/tabbrowser/Tabbrowser.sys.mjs', 'moz-src/browser/components/tabbrowser/Tabbrowser.sys.mjs', 'firefox156-sessionstore'),
        ('browser/components/contextualidentity/content/ContainerEditor.mjs', 'chrome/browser/content/browser/usercontext/ContainerEditor.mjs', 'firefox156-settings'),
        ('browser/components/contextualidentity/content/ContainerCreationPanel.mjs', 'chrome/browser/content/browser/usercontext/ContainerCreationPanel.mjs', 'firefox156-settings'),
        ('browser/components/preferences/config/containers.mjs', 'chrome/browser/content/browser/preferences/config/containers.mjs', 'firefox156-settings'),
        ('browser/components/preferences/dialogs/containers.js', 'chrome/browser/content/browser/preferences/dialogs/containers.js', 'firefox156-settings'),
        ('browser/components/tabbrowser/content/browser-allTabsMenu.js', 'chrome/browser/content/browser/tabbrowser/browser-allTabsMenu.js', 'firefox-alltabs/156'),
        ('browser/components/contextualidentity/content/container-select.mjs', 'chrome/browser/content/browser/usercontext/container-select.mjs', 'firefox156-associations'),
        ('browser/components/preferences/dialogs/siteContainer.js', 'chrome/browser/content/browser/preferences/dialogs/siteContainer.js', 'firefox156-associations'),
    ]
    result = {}
    with tempfile.TemporaryDirectory(prefix='zen-native-assets-') as temporary:
        for source, bundled, fixture in items:
            relative = Path(source)
            target = Path(temporary) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / 'scripts/terminal-tabs/fixtures' / fixture / relative).read_bytes())
            patch = root / 'src' / relative.parent / (relative.name.replace('.', '-') + '.patch')
            subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(patch)], cwd=temporary, check=True, capture_output=True)
            result[bundled] = target.read_bytes()
    return result


def verify(app, root):
    for path in app.rglob('Info.plist'):
        metadata = plistlib.loads(path.read_bytes())
        require(not {'MozillaDeveloperRepoPath', 'MozillaDeveloperObjPath'}.intersection(metadata),
                f'Build-machine paths remain in {path.relative_to(app)}')
    require(not list(app.rglob('.purgecaches')), 'Development cache-reset marker would invalidate the signature on launch')
    config = configparser.ConfigParser()
    config.read(app / 'Contents/Resources/platform.ini')
    expected = json.loads((root / 'surfer.json').read_text())['version']['version']
    require(config['Build']['Milestone'] == expected, 'Packaged Firefox engine does not match source')
    native_assets = expected_native_assets(root)
    with open_omni(app / 'Contents/Resources/omni.ja') as gre:
        require({'chrome.manifest', 'modules/AppConstants.sys.mjs'}.issubset(gre.namelist()), 'Missing engine resource registration')
        for bundled, expected_bytes in native_assets.items():
            if bundled.startswith('moz-src/'):
                require(gre.read(bundled) == expected_bytes, f'Stale native engine patch: {bundled}')
    archive = open_omni(app / 'Contents/Resources/browser/omni.ja')
    read = archive.read
    try:
        count = 0
        for line in (root / 'src/zen/terminal/jar.inc.mn').read_text().splitlines():
            match = re.search(r'content/browser/(\S+)\s+\(../../zen/terminal/(.+)\)', line)
            if not match:
                continue
            entry = 'chrome/browser/content/browser/' + match[1]
            require(read(entry) == (root / 'src/zen/terminal' / match[2]).read_bytes(), f'Missing or stale terminal asset: {entry}')
            count += 1
        require(count >= 14, 'Terminal asset manifest is incomplete')
        for bundled, source in [
            ('chrome/browser/content/browser/ZenPreloadedScripts.js', 'src/zen/common/ZenPreloadedScripts.js'),
            ('chrome/browser/content/browser/ZenUIManager.mjs', 'src/zen/common/modules/ZenUIManager.mjs'),
            ('chrome/browser/content/browser/zen-components/ZenPinnedTabManager.mjs', 'src/zen/tabs/ZenPinnedTabManager.mjs'),
            ('chrome/browser/content/browser/zen-components/ZenFolder.mjs', 'src/zen/folders/ZenFolder.mjs'),
            ('chrome/browser/content/browser/zen-components/ZenFolders.mjs', 'src/zen/folders/ZenFolders.mjs'),
            ('chrome/browser/content/browser/zen-components/ZenViewSplitter.mjs', 'src/zen/split-view/ZenViewSplitter.mjs'),
            ('modules/zen/ZenSpaceManager.mjs', 'src/zen/spaces/ZenSpaceManager.mjs'),
            ('modules/zen/share/ZenShareManager.mjs', 'src/zen/share/ZenShareManager.mjs'),
            ('modules/zen/share/ZenShareClient.sys.mjs', 'src/zen/share/ZenShareClient.sys.mjs'),
            ('modules/zen/share/ZenShareSafety.sys.mjs', 'src/zen/share/ZenShareSafety.sys.mjs'),
            ('modules/zen/share/share.schema.json', 'src/zen/share/share.schema.json'),
        ]:
            require(read(bundled) == (root / source).read_bytes(), f'Stale browser integration: {bundled}')
        for bundled, expected_bytes in native_assets.items():
            if bundled.startswith('moz-src/'):
                continue
            require(read(bundled) == expected_bytes, f'Stale native UI patch: {bundled}')
        require(b'gZenTerminalTabs.populateUnifiedContainerMenu(event)' in read('chrome/browser/content/browser/browser.xhtml'), 'Missing native terminal menu')
        return {'terminal_assets': count, 'engine': expected, 'layout': 'real GRE and browser omnijar resources'}
    finally:
        if archive:
            archive.close()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: verify-terminal-app-assets.py APP')
    print(json.dumps(verify(Path(sys.argv[1]), Path(__file__).resolve().parents[2]), indent=2))
