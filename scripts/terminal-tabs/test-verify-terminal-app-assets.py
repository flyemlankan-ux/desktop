#!/usr/bin/env python3
"""Asset acceptance must not quietly relax release or source-equality checks."""
import importlib.util
from pathlib import Path
import re
import plistlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('verify_assets', Path(__file__).with_name('verify-terminal-app-assets.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name) / 'Test.app'
        self.browser = self.app / 'Contents/Resources/browser'
        self.browser.mkdir(parents=True)
        (self.browser.parent / 'platform.ini').write_text('[Build]\nMilestone=155.0.1\n')
        (self.browser / 'chrome.manifest').write_text('manifest chrome/browser.manifest\n')
        entries = {}
        for line in (ROOT / 'src/zen/terminal/jar.inc.mn').read_text().splitlines():
            match = re.search(r'content/browser/(\S+)\s+\(../../zen/terminal/(.+)\)', line)
            if match:
                entries[match[1]] = (ROOT / 'src/zen/terminal' / match[2]).read_bytes()
        entries['ZenPreloadedScripts.js'] = (ROOT / 'src/zen/common/ZenPreloadedScripts.js').read_bytes()
        entries['ZenUIManager.mjs'] = (ROOT / 'src/zen/common/modules/ZenUIManager.mjs').read_bytes()
        entries['browser.xhtml'] = b'gZenTerminalTabs.populateUnifiedContainerMenu(event)'
        for name, data in entries.items():
            path = self.browser / 'chrome/browser/content/browser' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def pack(self):
        # Synthetic archive fixtures only, not claimed as a runnable browser.
        with zipfile.ZipFile(self.browser.parent / 'omni.ja', 'w') as archive:
            archive.writestr('chrome.manifest', 'synthetic')
            archive.writestr('modules/AppConstants.sys.mjs', 'synthetic')
        with zipfile.ZipFile(self.browser / 'omni.ja', 'w') as archive:
            for path in (self.browser / 'chrome').rglob('*'):
                if path.is_file():
                    archive.write(path, path.relative_to(self.browser))

    def test_loose_resources_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Missing required packaged resources'):
            module.verify(self.app, ROOT)

    def test_compressed_resources(self):
        self.pack()
        self.assertEqual(module.verify(self.app, ROOT)['terminal_assets'], 12)

    def test_stale_asset_rejected(self):
        path = self.browser / 'chrome/browser/content/browser/ZenUIManager.mjs'
        path.write_text('stale')
        self.pack()
        with self.assertRaisesRegex(AssertionError, 'Stale browser integration'):
            module.verify(self.app, ROOT)

    def test_build_machine_metadata_rejected(self):
        (self.app / 'Contents/Info.plist').write_bytes(plistlib.dumps({'MozillaDeveloperObjPath': '/absent/runner'}))
        with self.assertRaisesRegex(AssertionError, 'Build-machine paths'):
            module.verify(self.app, ROOT)

    def test_self_deleting_cache_marker_rejected(self):
        (self.browser / '.purgecaches').touch()
        with self.assertRaisesRegex(AssertionError, 'cache-reset marker'):
            module.verify(self.app, ROOT)

    def test_wrong_engine_rejected(self):
        (self.browser.parent / 'platform.ini').write_text('[Build]\nMilestone=152.0.5\n')
        with self.assertRaisesRegex(AssertionError, 'engine'):
            module.verify(self.app, ROOT)

    def test_missing_asset_rejected(self):
        (self.browser / 'chrome/browser/content/browser/ZenUIManager.mjs').unlink()
        self.pack()
        with self.assertRaises(KeyError):
            module.verify(self.app, ROOT)

    def test_optimized_python_keeps_rejections(self):
        script = str(Path(__file__).with_name('verify-terminal-app-assets.py'))
        command = [sys.executable, '-O', script, str(self.app)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing required packaged resources', result.stderr)
        (self.browser.parent / 'platform.ini').write_text('[Build]\nMilestone=152.0.5\n')
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('engine', result.stderr)


if __name__ == '__main__':
    unittest.main()
