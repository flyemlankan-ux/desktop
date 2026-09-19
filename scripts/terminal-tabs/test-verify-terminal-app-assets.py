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
        (self.browser.parent / 'platform.ini').write_text('[Build]\nMilestone=156.0\n')
        (self.browser / 'chrome.manifest').write_text('manifest chrome/browser.manifest\n')
        entries = {}
        for line in (ROOT / 'src/zen/terminal/jar.inc.mn').read_text().splitlines():
            match = re.search(r'content/browser/(\S+)\s+\(../../zen/terminal/(.+)\)', line)
            if match:
                entries[match[1]] = (ROOT / 'src/zen/terminal' / match[2]).read_bytes()
        entries['ZenPreloadedScripts.js'] = (ROOT / 'src/zen/common/ZenPreloadedScripts.js').read_bytes()
        entries['ZenUIManager.mjs'] = (ROOT / 'src/zen/common/modules/ZenUIManager.mjs').read_bytes()
        module_path = self.browser / 'modules/zen/ZenSpaceManager.mjs'
        module_path.parent.mkdir(parents=True, exist_ok=True)
        module_path.write_bytes((ROOT / 'src/zen/spaces/ZenSpaceManager.mjs').read_bytes())
        for name in ('ZenShareManager.mjs', 'ZenShareClient.sys.mjs', 'ZenShareSafety.sys.mjs', 'share.schema.json'):
            module_path = self.browser / 'modules/zen/share' / name
            module_path.parent.mkdir(parents=True, exist_ok=True)
            module_path.write_bytes((ROOT / 'src/zen/share' / name).read_bytes())
        entries['zen-components/ZenPinnedTabManager.mjs'] = (ROOT / 'src/zen/tabs/ZenPinnedTabManager.mjs').read_bytes()
        entries['zen-components/ZenViewSplitter.mjs'] = (ROOT / 'src/zen/split-view/ZenViewSplitter.mjs').read_bytes()
        for name in ('ZenFolder.mjs', 'ZenFolders.mjs'):
            entries['zen-components/' + name] = (ROOT / 'src/zen/folders' / name).read_bytes()
        entries['browser.xhtml'] = b'gZenTerminalTabs.populateUnifiedContainerMenu(event)'
        for name, data in entries.items():
            path = self.browser / 'chrome/browser/content/browser' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        for bundled, data in module.expected_native_assets(ROOT).items():
            if bundled.startswith('moz-src/'):
                continue
            target = self.browser / bundled
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def pack(self):
        # Synthetic archive fixtures only, not claimed as a runnable browser.
        with zipfile.ZipFile(self.browser.parent / 'omni.ja', 'w') as archive:
            archive.writestr('chrome.manifest', 'synthetic')
            archive.writestr('modules/AppConstants.sys.mjs', 'synthetic')
            for bundled, data in module.expected_native_assets(ROOT).items():
                if bundled.startswith('moz-src/'):
                    archive.writestr(bundled, data)
        with zipfile.ZipFile(self.browser / 'omni.ja', 'w') as archive:
            for directory in ('chrome', 'modules'):
                for path in (self.browser / directory).rglob('*'):
                    if path.is_file():
                        archive.write(path, path.relative_to(self.browser))

    def test_loose_resources_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Missing required packaged resources'):
            module.verify(self.app, ROOT)

    def test_compressed_resources(self):
        self.pack()
        self.assertEqual(module.verify(self.app, ROOT)['terminal_assets'], 14)

    def test_unused_copy_does_not_hide_stale_registered_module(self):
        for entry, source in [
            ('chrome/browser/content/browser/zen-components/ZenPinnedTabManager.mjs', 'src/zen/tabs/ZenPinnedTabManager.mjs'),
            ('chrome/browser/content/browser/zen-components/ZenViewSplitter.mjs', 'src/zen/split-view/ZenViewSplitter.mjs'),
            ('modules/zen/ZenSpaceManager.mjs', 'src/zen/spaces/ZenSpaceManager.mjs'),
        ]:
            with self.subTest(entry=entry):
                target = self.browser / entry
                target.write_text('stale actual loaded module')
                wrong = self.browser / 'chrome/browser/content/browser' / Path(entry).name
                wrong.write_bytes((ROOT / source).read_bytes())
                self.pack()
                with self.assertRaisesRegex(AssertionError, 'Stale browser integration'):
                    module.verify(self.app, ROOT)
                target.write_bytes((ROOT / source).read_bytes())

    def test_stale_engine_restore_and_tab_management_rejected(self):
        for entry in ('moz-src/browser/components/sessionstore/SessionStore.sys.mjs',
                      'moz-src/browser/components/tabbrowser/Tabbrowser.sys.mjs'):
            with self.subTest(entry=entry):
                self.pack()
                path = self.browser.parent / 'omni.ja'
                with zipfile.ZipFile(path) as archive:
                    entries = {n: archive.read(n) for n in archive.namelist()}
                entries[entry] = b'stale engine module'
                with zipfile.ZipFile(path, 'w') as archive:
                    for name, data in entries.items():
                        archive.writestr(name, data)
                with self.assertRaisesRegex(AssertionError, 'Stale native engine patch'):
                    module.verify(self.app, ROOT)

    def test_stale_native_settings_rejected(self):
        (self.browser / 'chrome/browser/content/browser/usercontext/ContainerEditor.mjs').write_text('old editor')
        self.pack()
        with self.assertRaisesRegex(AssertionError, 'Stale native UI patch'):
            module.verify(self.app, ROOT)

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
