#!/usr/bin/env python3
"""Synthetic artifact names only; no application launch or personal data."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile
spec = importlib.util.spec_from_file_location('privacy', Path(__file__).with_name('check-terminal-package-privacy.py'))
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='zt-package-privacy-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.image = self.root / 'image'
        self.image.mkdir()

    def put(self, relative, content=b'SYNTHETIC'):
        path = self.image / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_sibling_profile_not_only_app_is_rejected(self):
        self.put('Zen Terminal.app/Contents/defaults/pref/zen.js')
        self.put('Profiles/synthetic/logins.json')
        self.assertEqual(privacy.check_image(self.image), ['Profiles/synthetic/logins.json'])

    def test_history_sessions_and_sqlite_sidecars(self):
        for name in ['places.sqlite', 'cookies.sqlite-wal', 'cookies.sqlite-shm',
                     'places.sqlite-journal', 'zen-workspaces.json', 'sessionstore.jsonlz4']:
            with self.subTest(name=name):
                file = self.put('extras/' + name)
                self.assertIn('extras/' + name, privacy.check_image(self.image))
                file.unlink()

    def test_defaults_and_normal_resources_are_allowed(self):
        self.put('Zen Terminal.app/Contents/defaults/pref/prefs.js')
        self.put('Zen Terminal.app/Contents/Resources/containers.schema.json')
        self.put('README.txt')
        self.assertEqual(privacy.check_image(self.image), [])

    def test_private_member_in_each_supported_resource_archive(self):
        for extension in ['ja', 'zip', 'xpi']:
            with self.subTest(extension=extension):
                archive = self.image / ('resources.' + extension)
                with zipfile.ZipFile(archive, 'w') as file:
                    file.writestr('profile/LOGINS.JSON', 'SYNTHETIC')
                self.assertTrue(privacy.check_image(self.image))
                archive.unlink()

    def test_archive_names_checked_without_reading_member_contents(self):
        archive = self.image / 'omni.ja'
        with zipfile.ZipFile(archive, 'w') as file:
            file.writestr('defaults/pref/prefs.js', 'legitimate')
        with mock.patch.object(zipfile.ZipFile, 'open', side_effect=AssertionError('No member reads')):
            self.assertEqual(privacy.check_image(self.image), [])

    def test_applications_link_is_not_followed(self):
        (self.image / 'Applications').symlink_to('/Applications')
        self.assertEqual(privacy.check_image(self.image), [])

    def test_other_external_links_fail_before_target_is_read(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'safe-name.txt').write_text('SYNTHETIC')
        (self.image / 'external').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'external symlink'):
            privacy.check_image(self.image)

    def test_internal_framework_links_allowed_without_traversal(self):
        self.put('Framework/Versions/A/binary')
        (self.image / 'Framework/Versions/Current').symlink_to('A')
        self.assertEqual(privacy.check_image(self.image), [])

    def test_special_files_and_bad_archives_fail_closed(self):
        pipe = self.image / 'fifo'
        os.mkfifo(pipe)
        with self.assertRaises(ValueError): privacy.check_image(self.image)
        pipe.unlink()
        self.put('omni.ja', b'NOT A ZIP')
        with self.assertRaises(zipfile.BadZipFile): privacy.check_image(self.image)

    def test_cli_never_prints_private_names_or_contents(self):
        self.put('PRIVATE-PROFILE-NAME/logins.json', b'PRIVATE-CONTENT')
        result = subprocess.run([sys.executable, str(Path(privacy.__file__)), str(self.image)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('PRIVATE', result.stdout + result.stderr)

    def test_inspector_calls_scanner_on_whole_mount(self):
        source = Path(__file__).with_name('inspect-terminal-macos-dmg.sh').read_text()
        self.assertIn('check-terminal-package-privacy.py "$MOUNT_POINT"', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
