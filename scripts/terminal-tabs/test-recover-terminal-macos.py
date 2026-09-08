#!/usr/bin/env python3
"""Focused safety checks for the recovered-development-app packaging script."""
import importlib.util
import json
import os
import plistlib
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('recovery', Path(__file__).with_name('recover-terminal-macos.py'))
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoverySafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='zen-recovery-safety-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_manifest_rejects_symlinks(self):
        (self.root / 'link').symlink_to('/Applications')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            recovery.manifest(self.root)

    def test_manifest_rejects_fifo_without_reading_it(self):
        os.mkfifo(self.root / 'pipe')
        with self.assertRaisesRegex(ValueError, 'special file'):
            recovery.manifest(self.root)

    def test_atomic_publish_cannot_replace_empty_or_nonempty_directory(self):
        source = self.root / 'stage'
        source.mkdir()
        (source / 'proof').write_text('source remains intact')
        target = self.root / 'target'
        target.mkdir()
        with self.assertRaises(OSError):
            recovery.atomic_publish(source, target)
        self.assertTrue((source / 'proof').is_file())
        self.assertEqual(list(target.iterdir()), [])
        (target / 'existing').write_text('never overwrite')
        with self.assertRaises(OSError):
            recovery.atomic_publish(source, target)
        self.assertEqual((target / 'existing').read_text(), 'never overwrite')

    def test_atomic_publish_new_directory(self):
        source = self.root / 'stage'
        source.mkdir()
        (source / 'proof').write_text('preserved')
        recovery.atomic_publish(source, self.root / 'published')
        self.assertFalse(source.exists())
        self.assertEqual((self.root / 'published/proof').read_text(), 'preserved')

    def test_signing_cannot_change_resource_or_remove_file(self):
        original = {recovery.HELPER_OLD.as_posix(): 'helper', 'Contents/Resources/page.mjs': 'original'}
        altered = {recovery.HELPER_NEW.as_posix(): 'helper', 'Contents/Resources/page.mjs': 'changed'}
        source = self.root / 'source'
        app = self.root / 'app'
        for root in [source, app]:
            (root / 'Contents/Resources').mkdir(parents=True)
            (root / 'Contents/Resources/page.mjs').write_text('not a native executable')
        with self.assertRaisesRegex(ValueError, 'non-executable'):
            recovery.verify_signing_changes(original, altered, source, app)
        del altered['Contents/Resources/page.mjs']
        with self.assertRaisesRegex(ValueError, 'removed'):
            recovery.verify_signing_changes(original, altered, source, app)

    def test_developer_metadata_cleanup_only_removes_named_keys_and_marker(self):
        marker = self.root / recovery.DEVELOPMENT_MARKERS[0]
        marker.parent.mkdir(parents=True)
        marker.write_bytes(b'1')
        original = {'CFBundleIdentifier': 'test.identity', 'MozillaDeveloperObjPath': '/runner/obj',
                    'MozillaDeveloperRepoPath': '/runner/repo', 'nested': {'preserve': True}}
        for relative in ['Contents/Info.plist', 'Contents/MacOS/child.app/Contents/Info.plist']:
            file = self.root / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(plistlib.dumps(original))
        receipt = recovery.remove_development_only_metadata(self.root)
        self.assertFalse(marker.exists())
        self.assertEqual(len(receipt['removedDeveloperPathPlistKeys']), 2)
        for file in self.root.rglob('Info.plist'):
            self.assertEqual(plistlib.loads(file.read_bytes()),
                             {'CFBundleIdentifier': 'test.identity', 'nested': {'preserve': True}})
        again = recovery.remove_development_only_metadata(self.root)
        self.assertEqual(again['removedDevelopmentCacheMarkers'], [])
        self.assertEqual(again['removedDeveloperPathPlistKeys'], [])
        self.assertEqual(again['removedTestOnlyPlugins'], [])

    def test_modified_tool_receipt_is_rejected_before_import(self):
        (self.root / 'receipt.json').write_text(json.dumps({'ref': 'FIREFOX_155_0_1_RELEASE', 'files': {}}))
        with self.assertRaisesRegex(ValueError, 'tracked pinned receipt'):
            recovery.load_mozpack(self.root)

    def test_real_upstream_mozpack_creates_both_omnijars_without_changing_native_bytes(self):
        # Real pinned upstream Python, no mocked packer and no browser launch.
        tools = Path(__file__).resolve().parents[2] / '.terminal-test/mozpack155'
        self.assertTrue((tools / 'receipt.json').is_file(), 'Fetch pinned mozpack with fetch-terminal-mozpack.py first')
        source = self.root / 'raw'
        output = self.root / 'packed'
        for relative, package in [('Contents/Resources', 'global'), ('Contents/Resources/browser', 'browser')]:
            base = source / relative
            (base / 'chrome' / package / 'content' / package).mkdir(parents=True)
            (base / 'chrome.manifest').write_text(f'manifest chrome/{package}.manifest\n')
            (base / 'chrome' / f'{package}.manifest').write_text(f'content {package} {package}/content/{package}/\n')
            (base / 'chrome' / package / 'content' / package / 'probe.js').write_bytes(b'// real packaged resource')
        page = source / 'Contents/Resources/browser/chrome/browser/content/browser/zen-terminal/ZenTerminalPage.mjs'
        page.parent.mkdir()
        page.write_bytes(b'// exact terminal bytes')
        (page.parent.parent / 'ZenUIManager.mjs').write_bytes(b'// exact UI bytes')
        native = source / 'Contents/MacOS/zen-terminal'
        native.parent.mkdir()
        native.write_bytes(b'\xcf\xfa\xed\xfeNATIVE-FIXTURE')
        result = recovery.pack_omnijars(source, output, tools)
        self.assertEqual(result['nativeBinaryFilesByteVerifiedBeforeSigning'], 1)
        self.assertEqual((output / 'Contents/MacOS/zen-terminal').read_bytes(), native.read_bytes())
        self.assertEqual(len(result['omnijars']), 2)
        self.assertFalse((output / page.relative_to(source)).exists())

    def test_relocation_and_signature_metadata_are_allowed(self):
        original = {recovery.HELPER_OLD.as_posix(): 'helper'}
        signed = {recovery.HELPER_NEW.as_posix(): 'helper', 'Contents/_CodeSignature/CodeResources': 'signature'}
        self.assertEqual(recovery.verify_signing_changes(original, signed, self.root, self.root),
                         ['Contents/_CodeSignature/CodeResources'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
