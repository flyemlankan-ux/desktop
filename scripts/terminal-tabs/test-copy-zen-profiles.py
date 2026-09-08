#!/usr/bin/env python3
"""Synthetic-only profile migration proof. Never opens a real browser profile."""
import configparser
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("profile_copy", Path(__file__).with_name("copy-zen-profiles.py"))
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class CopyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-synthetic-profile-copy-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source"
        self.source.mkdir()
        self.destination = self.root / "private-copy"
        self.profile = self.source / "Profiles" / "main"
        self.profile.mkdir(parents=True)
        self.second = self.source / "Profiles" / "other"
        self.second.mkdir()
        self.write_ini()
        for profile in [self.profile, self.second]:
            (profile / "compatibility.ini").write_text("[Compatibility]\nLastVersion=1.21.6b_20260708000000/20260708000000\n")
            (profile / "key4.db").write_bytes(b"SYNTHETIC-key\x00\xff")
            (profile / "logins.json").write_text('{"synthetic": true, "password": "NOT-A-REAL-CREDENTIAL"}')
            (profile / "cookies.sqlite").write_bytes(b"SYNTHETIC-cookie-db\x00")
            (profile / "cookies.sqlite-wal").write_bytes(b"SYNTHETIC-wal\x01")
            (profile / "prefs.js").write_text('// SYNTHETIC preferences\n')
            (profile / "sessionstore-backups").mkdir()
            (profile / "sessionstore-backups" / "recovery.jsonlz4").write_bytes(b"SYNTHETIC-workspaces\xff")
            (profile / ".parentlock").write_bytes(b"")
            (profile / "cache2").mkdir()
            (profile / "cache2" / "rebuildable").write_bytes(b"cache")
        (self.source / "Profile Groups").mkdir()
        (self.source / "Profile Groups" / "synthetic-group.json").write_text('{"synthetic":true}')
        (self.source / "installs.ini").write_text("[OLD-APP-HASH]\nDefault=Profiles/main\n")

    def write_ini(self, install="Profiles/main"):
        (self.source / "profiles.ini").write_text(
            "[General]\nStartWithLastProfile=1\nVersion=2\n"
            "[Profile0]\nName=Main setup\nIsRelative=1\nPath=Profiles/main\nDefault=0\n"
            "[Profile1]\nName=Other setup\nIsRelative=1\nPath=Profiles/other\nDefault=1\n"
            f"[InstallOLDHASH]\nDefault={install}\nLocked=1\n")

    def hashes(self):
        return {p.relative_to(self.source).as_posix(): migration.digest(p)
                for p in self.source.rglob("*") if p.is_file()}

    def run_copy(self, **kwargs):
        values = dict(source_root=self.source, destination_root=self.destination,
                      source_engine_version="152.0.5", target_engine_version="152.0.5",
                      activity_check=lambda source: None)
        values.update(kwargs)
        return migration.copy_setup(**values)

    def assert_stopped(self, **kwargs):
        with self.assertRaises((migration.CopyError, OSError)):
            self.run_copy(copy=True, **kwargs)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.root.glob(".private-copy.private-copy-*")), [])

    def test_default_is_dry_run_and_changes_nothing(self):
        before = self.hashes()
        result = self.run_copy()
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["default_profile"], "Main setup")
        self.assertEqual(result["profile_count"], 2)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.hashes(), before)

    def test_copy_all_profiles_exact_private_and_source_unchanged(self):
        before = self.hashes()
        result = self.run_copy(copy=True)
        self.assertEqual(result["mode"], "copy")
        self.assertEqual(self.hashes(), before)
        self.assertNotIn("critical_sha256", result)
        for relative, value in before.items():
            if relative == "profiles.ini":
                continue  # Intentionally regenerated for the new application.
            if migration.excluded(relative, migration.registered_profiles(self.source)[0]):
                self.assertFalse((self.destination / relative).exists())
            else:
                self.assertEqual(migration.digest(self.destination / relative), value)
        parsed = migration.ini_file(self.destination / "profiles.ini")
        self.assertEqual(parsed["Profile0"]["Name"], "Main setup")
        self.assertEqual(parsed["Profile0"]["Default"], "1")
        self.assertEqual(parsed["Profile1"]["Default"], "0")
        self.assertFalse(any(s.startswith("Install") for s in parsed.sections()))
        self.assertFalse((self.destination / "installs.ini").exists())
        metadata = json.loads((self.destination / "zen-terminal-copy-verification.json").read_text())
        self.assertEqual(metadata["critical_sha256"]["Profiles/main/key4.db"], before["Profiles/main/key4.db"])
        self.assertNotIn("NOT-A-REAL-CREDENTIAL", json.dumps(metadata))
        for item in [self.destination, *self.destination.rglob("*")]:
            self.assertEqual(item.stat().st_mode & 0o077, 0)

    def test_absolute_inside_root_profiles_become_equivalent_relative_paths(self):
        ini = (self.source / "profiles.ini").read_text().replace("IsRelative=1\nPath=Profiles/main", f"IsRelative=0\nPath={self.profile}")
        (self.source / "profiles.ini").write_text(ini)
        self.run_copy(copy=True)
        parsed = migration.ini_file(self.destination / "profiles.ini")
        self.assertEqual(parsed["Profile0"]["Path"], "Profiles/main")
        self.assertEqual(parsed["Profile0"]["IsRelative"], "1")

    def test_ambiguous_default_requires_explicit_choice(self):
        with (self.source / "profiles.ini").open("a") as stream:
            stream.write("[InstallOTHERHASH]\nDefault=Profiles/other\n")
        self.assert_stopped()
        result = self.run_copy(default_profile="Other setup")
        self.assertEqual(result["default_profile"], "Other setup")

    def test_external_or_escaping_profile_is_not_skipped(self):
        ini = self.source / "profiles.ini"
        original = ini.read_text()
        for unsafe in ["../outside", str(self.root / "outside")]:
            ini.write_text(original.replace("IsRelative=1\nPath=Profiles/main", f"IsRelative=0\nPath={unsafe}"))
            self.assert_stopped()
        ini.write_text(original)

    def test_existing_destination_is_never_changed(self):
        self.destination.mkdir()
        marker = self.destination / "keep"
        marker.write_text("unchanged")
        with self.assertRaises(migration.CopyError):
            self.run_copy(copy=True)
        self.assertEqual(marker.read_text(), "unchanged")

    def test_overlapping_roots_are_rejected(self):
        for target in [self.source, self.profile / "copy", self.root]:
            with self.assertRaises(migration.CopyError):
                self.run_copy(copy=True, destination_root=target)

    def test_downgrade_and_invalid_engine_versions_are_rejected(self):
        for version in ["151.9", "152.0.5b1", "Zen 1.21.6b", ""]:
            self.assert_stopped(target_engine_version=version)
        self.assertEqual(self.run_copy(target_engine_version="153.0a1")["mode"], "dry-run")

    def test_never_used_registered_profiles_are_preserved_without_compatibility(self):
        for name in ["unused-empty", "unused-timestamp"]:
            (self.source / "Profiles" / name).mkdir()
        timestamp = self.source / "Profiles" / "unused-timestamp" / "times.json"
        timestamp.write_bytes(b'{"created":1234567890,"synthetic":true}\n')
        with (self.source / "profiles.ini").open("a") as stream:
            stream.write("[Profile2]\nName=Unused empty\nIsRelative=1\nPath=Profiles/unused-empty\n"
                         "[Profile3]\nName=Unused timestamp\nIsRelative=1\nPath=Profiles/unused-timestamp\n")
        before = self.hashes()
        result = self.run_copy(copy=True)
        self.assertEqual(result["profile_count"], 4)
        self.assertEqual(self.hashes(), before)
        self.assertEqual((self.destination / "Profiles" / "unused-timestamp" / "times.json").read_bytes(), timestamp.read_bytes())
        self.assertEqual(list((self.destination / "Profiles" / "unused-empty").iterdir()), [])
        parsed = migration.ini_file(self.destination / "profiles.ini")
        self.assertEqual(parsed["Profile3"]["Name"], "Unused timestamp")
        self.assertEqual(result["registered_profiles"][-1]["source_app_last_version"], "uninitialized")

    def test_missing_compatibility_with_even_an_empty_subdirectory_is_rejected(self):
        unused = self.source / "Profiles" / "unused"
        unused.mkdir()
        (unused / "some-data").mkdir()
        with (self.source / "profiles.ini").open("a") as stream:
            stream.write("[Profile2]\nName=Unknown\nIsRelative=1\nPath=Profiles/unused\n")
        self.assert_stopped()

    def test_zen_compressed_sessions_and_all_session_backups_have_private_hashes(self):
        (self.profile / "zen-sessions.jsonlz4").write_bytes(b"SYNTHETIC compressed sessions")
        backup = self.profile / "sessionstore-backups" / "upgrade.jsonlz4-20260708000000"
        backup.write_bytes(b"SYNTHETIC versioned backup")
        self.run_copy(copy=True)
        metadata = json.loads((self.destination / "zen-terminal-copy-verification.json").read_text())
        self.assertIn("Profiles/main/zen-sessions.jsonlz4", metadata["critical_sha256"])
        self.assertIn("Profiles/main/sessionstore-backups/upgrade.jsonlz4-20260708000000", metadata["critical_sha256"])

    def test_missing_compatibility_metadata_is_rejected(self):
        (self.second / "compatibility.ini").unlink()
        self.assert_stopped()

    def test_symlinks_in_data_or_cache_or_destination_ancestors_are_rejected(self):
        for directory in [self.profile, self.profile / "cache2"]:
            link = directory / "unsafe-link"
            link.symlink_to(self.root)
            self.assert_stopped()
            link.unlink()
        alias = self.root / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(migration.CopyError):
            self.run_copy(source_root=alias)

    def test_active_posix_lock_is_refused_but_stale_file_is_allowed(self):
        code = 'import fcntl,sys,time; f=open(sys.argv[1],"r+"); fcntl.lockf(f,fcntl.LOCK_EX); print("locked",flush=True); time.sleep(30)'
        process = subprocess.Popen([sys.executable, "-c", code, str(self.profile / ".parentlock")], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), "locked")
            self.assert_stopped()
        finally:
            process.terminate()
            process.wait(timeout=5)
            process.stdout.close()
        self.assertEqual(self.run_copy()["mode"], "dry-run")

    def test_open_file_guard_and_running_zen_guard_fail_closed(self):
        completed = subprocess.CompletedProcess
        with mock.patch.object(migration.subprocess, "run", return_value=completed([], 0, "22 /Applications/Zen.app/Contents/MacOS/zen\n", "")):
            with self.assertRaises(migration.CopyError):
                migration.ensure_closed(self.source)
        with mock.patch.object(migration.shutil, "which", return_value="/mock/lsof"), mock.patch.object(migration.subprocess, "run", side_effect=[completed([], 0, "", ""), completed([], 0, "999999\n", "")]):
            with self.assertRaises(migration.CopyError):
                migration.ensure_closed(self.source)

    def test_publish_error_cleans_own_staging_only(self):
        unrelated = self.root / ".private-copy.private-copy-other-person"
        unrelated.mkdir()
        with mock.patch.object(migration, "atomic_publish", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                self.run_copy(copy=True)
        self.assertFalse(self.destination.exists())
        self.assertTrue(unrelated.is_dir())
        self.assertEqual(list(self.root.glob(".private-copy.private-copy-*")), [unrelated])

    def test_atomic_publish_cannot_overwrite_racing_destination(self):
        stage = self.root / "stage"
        stage.mkdir()
        self.destination.mkdir()
        with self.assertRaises(migration.CopyError):
            migration.atomic_publish(stage, self.destination)
        self.assertTrue(stage.exists())
        self.assertTrue(self.destination.exists())

    def test_source_mutation_during_copy_discards_staging(self):
        count = 0
        def guard(source):
            nonlocal count
            count += 1
            if count == 2:
                (self.profile / "prefs.js").write_text("changed during copy")
        self.assert_stopped(activity_check=guard)

    def test_corrupt_copy_is_not_published(self):
        with mock.patch.object(migration.shutil, "copyfileobj", side_effect=lambda read, write, length: write.write(b"synthetic-corruption")):
            self.assert_stopped()

    def test_source_open_rejects_late_parent_symlink(self):
        original = self.profile / "sessionstore-backups"
        original.rename(self.profile / "moved-backups")
        original.symlink_to(self.profile / "moved-backups", target_is_directory=True)
        with self.assertRaises(OSError):
            with migration.source_file(self.source, "Profiles/main/sessionstore-backups/recovery.jsonlz4"):
                self.fail("Symlink parent should not be opened")

    def test_cli_requires_explicit_copy_and_both_engine_versions(self):
        argv = ["copy-zen-profiles.py", "--source-root", str(self.source), "--destination-root", str(self.destination),
                "--source-engine-version", "152.0.5", "--target-engine-version", "152.0.5"]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(migration, "copy_setup", return_value={"mode": "dry-run"}) as action, mock.patch("builtins.print"):
            self.assertEqual(migration.main(), 0)
            self.assertFalse(action.call_args.args[-1])
        with mock.patch.object(sys, "argv", argv + ["--copy"]), mock.patch.object(migration, "copy_setup", return_value={"mode": "copy"}) as action, mock.patch("builtins.print"):
            self.assertEqual(migration.main(), 0)
            self.assertTrue(action.call_args.args[-1])

    def test_target_install_hash_maps_only_final_app_to_selected_profile(self):
        before = self.hashes()
        result = self.run_copy(copy=True, default_profile="Other setup", target_install_hash="1234abcd5678ef90")
        profile_ini = migration.ini_file(self.destination / "profiles.ini")
        install_ini = migration.ini_file(self.destination / "installs.ini")
        self.assertEqual([s for s in profile_ini.sections() if s.startswith("Install")], ["Install1234ABCD5678EF90"])
        self.assertEqual(dict(profile_ini["Install1234ABCD5678EF90"]), {"Default": "Profiles/other", "Locked": "1"})
        self.assertEqual(install_ini.sections(), ["1234ABCD5678EF90"])
        self.assertEqual(dict(install_ini["1234ABCD5678EF90"]), {"Default": "Profiles/other", "Locked": "1"})
        self.assertEqual((self.destination / "installs.ini").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.hashes(), before)
        self.assertEqual((self.destination / "Profiles/main/compatibility.ini").read_bytes(), (self.profile / "compatibility.ini").read_bytes())
        self.assertEqual(result["profile_selection"], "dedicated-install")
        self.assertNotIn("warning", result)

    def test_generated_ini_bytes_use_firefox_exact_key_value_syntax(self):
        # Firefox155 xpcom/base/nsINIParser.cpp (blob
        # 0a56f3df026ddb2d4805a0f360aedf384c8674df), lines99-109,
        # splits on '=' but does not trim key/value whitespace. ConfigParser's
        # own roundtrip hides this incompatibility, so inspect actual bytes.
        before = self.hashes()
        self.run_copy(copy=True, default_profile="Other setup",
                      target_install_hash="1234abcd5678ef90")
        documents = {}
        for filename in ["profiles.ini", "installs.ini"]:
            content = (self.destination / filename).read_bytes()
            sections = {}
            current = None
            for line in content.splitlines():
                if not line:
                    continue
                if line.startswith(b"[") and line.endswith(b"]"):
                    current = line[1:-1]
                    sections[current] = {}
                    continue
                key, separator, value = line.partition(b"=")
                self.assertEqual(separator, b"=", (filename, line))
                self.assertEqual(key, key.strip(), (filename, line))
                self.assertEqual(value, value.strip(), (filename, line))
                self.assertIsNotNone(current)
                sections[current][key] = value
            documents[filename] = sections
        profiles = documents["profiles.ini"]
        self.assertEqual(profiles[b"General"][b"StartWithLastProfile"], b"1")
        self.assertEqual(profiles[b"General"][b"Version"], b"2")
        self.assertEqual(profiles[b"Profile0"][b"IsRelative"], b"1")
        self.assertEqual(profiles[b"Profile1"][b"Name"], b"Other setup")
        self.assertEqual(profiles[b"Profile1"][b"Path"], b"Profiles/other")
        self.assertEqual(profiles[b"Profile1"][b"Default"], b"1")
        mapping = {b"Default": b"Profiles/other", b"Locked": b"1"}
        self.assertEqual(profiles[b"Install1234ABCD5678EF90"], mapping)
        self.assertEqual(documents["installs.ini"][b"1234ABCD5678EF90"], mapping)
        self.assertEqual(self.hashes(), before)

    def test_no_hash_explicitly_warns_about_manual_profile_selection(self):
        result = self.run_copy()
        self.assertEqual(result["profile_selection"], "explicit-selection-required")
        self.assertIn("blank profile", result["warning"])

    def test_invalid_target_install_hash_is_rejected_without_copying(self):
        for value in ["", "A" * 15, "A" * 17, "G" * 16, "../1234567890123", "1234567890ABCDEF\n"]:
            self.assert_stopped(target_install_hash=value)

    def test_repository_destination_is_rejected(self):
        repo = self.root / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        with self.assertRaises(migration.CopyError):
            self.run_copy(destination_root=repo / "private", copy=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
