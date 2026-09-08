#!/usr/bin/env python3
"""Focused command-planning tests; actual packaging still requires the source build."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
spec = importlib.util.spec_from_file_location('terminal_packaging', Path(__file__).with_name('package-terminal-macos.py'))
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)

class Tests(unittest.TestCase):
    def test_real_supported_locales_and_no_updater_commands(self):
        commands = packaging.package_commands(Path(__file__).resolve().parents[2])
        self.assertEqual(commands[0][1:], ['package'])
        self.assertEqual(commands[1][1:3], ['package-multi-locale', '--locales'])
        self.assertIn('nb-NO', commands[1]); self.assertIn('en-GB', commands[1])
        self.assertFalse(any('mar' in value for command in commands for value in command[1:]))

    def test_failure_stops_before_next_package(self):
        with mock.patch.object(packaging.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, ['mach'])) as run:
            with self.assertRaises(subprocess.CalledProcessError): packaging.main()
            self.assertEqual(run.call_count, 1)
            self.assertTrue(run.call_args.kwargs['check'])

    def test_malformed_locale_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / 'locales').mkdir()
            (root / 'locales/language-maps').write_text('')
            (root / 'locales/supported-languages').write_text('en-US;bad')
            with self.assertRaises(ValueError): packaging.package_commands(root)

if __name__ == '__main__': unittest.main(verbosity=2)
