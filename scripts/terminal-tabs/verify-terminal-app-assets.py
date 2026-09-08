#!/usr/bin/env python3
"""Verify real packaged resources, engine and exact shipped terminal assets."""
from pathlib import Path
import configparser
import io
import json
import plistlib
import re
import struct
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
    with open_omni(app / 'Contents/Resources/omni.ja') as gre:
        require({'chrome.manifest', 'modules/AppConstants.sys.mjs'}.issubset(gre.namelist()), 'Missing engine resource registration')
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
        require(count >= 10, 'Terminal asset manifest is incomplete')
        for bundled, source in [
            ('ZenPreloadedScripts.js', 'src/zen/common/ZenPreloadedScripts.js'),
            ('ZenUIManager.mjs', 'src/zen/common/modules/ZenUIManager.mjs'),
        ]:
            require(read('chrome/browser/content/browser/' + bundled) == (root / source).read_bytes(), f'Stale browser integration: {bundled}')
        require(b'gZenTerminalTabs.populateUnifiedContainerMenu(event)' in read('chrome/browser/content/browser/browser.xhtml'), 'Missing native terminal menu')
        return {'terminal_assets': count, 'engine': expected, 'layout': 'real GRE and browser omnijar resources'}
    finally:
        if archive:
            archive.close()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: verify-terminal-app-assets.py APP')
    print(json.dumps(verify(Path(sys.argv[1]), Path(__file__).resolve().parents[2]), indent=2))
