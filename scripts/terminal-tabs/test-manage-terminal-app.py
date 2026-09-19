#!/usr/bin/env python3
"""Synthetic app-only transaction tests. Never uses /Applications or launches apps."""
import importlib.util
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest import mock
import subprocess
import sys
spec=importlib.util.spec_from_file_location('delivery',Path(__file__).with_name('manage-terminal-app.py'))
delivery=importlib.util.module_from_spec(spec);spec.loader.exec_module(delivery)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='zt-app-delivery-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.dest=self.root/'Zen Terminal.app';self.backup=self.root/'previous.app'
        self.source=self.root/'incoming.app';self.app(self.source,'new','156.0')
        self.profile=self.root/'private-data';self.profile.mkdir();(self.profile/'sentinel').write_bytes(b'SYNTHETIC PROFILE UNCHANGED')
        self.checks=[]

    def app(self,path,version='old',engine='155.0.1',bundle='app.zen-browser.zen-terminal',build_id='20260919120000'):
        (path/'Contents/Resources').mkdir(parents=True)
        (path/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':bundle,'CFBundleExecutable':'zen-terminal'}))
        (path/'Contents/Resources/application.ini').write_text(f'[App]\nProfile=zen-terminal\nVersion={version}\nBuildID={build_id}\n')
        (path/'Contents/Resources/platform.ini').write_text(f'[Build]\nMilestone={engine}\n')
        (path/'payload').write_text(version)

    def verify(self,app,root,version,engine):
        self.checks.append(app)
        return delivery.identity(app,version,engine)

    def run_action(self,action='install',**kwargs):
        options=dict(action=action,destination=self.dest,backup=self.backup,source=self.source,root=self.root,
                     expected_version='new',expected_engine='156.0',verifier=self.verify,activity=lambda paths:None)
        options.update(kwargs)
        result=delivery.manage(**options)
        self.assertEqual((self.profile/'sentinel').read_bytes(),b'SYNTHETIC PROFILE UNCHANGED')
        return result

    def test_dry_run_has_no_filesystem_changes(self):
        before=set(self.root.iterdir());self.run_action();self.assertEqual(set(self.root.iterdir()),before)

    def test_install_verifies_source_and_stage_then_publishes(self):
        self.run_action(apply=True);self.assertEqual((self.dest/'payload').read_text(),'new')
        self.assertEqual(len(self.checks),2);self.assertFalse(self.backup.exists());self.assertTrue(self.source.exists())

    def test_upgrade_retains_previous_app_byte_for_byte(self):
        self.app(self.dest);old=delivery.snapshot(self.dest)
        self.run_action('upgrade',apply=True)
        self.assertEqual(delivery.snapshot(self.backup),old);self.assertEqual((self.dest/'payload').read_text(),'new')

    def test_remove_retains_app_and_never_touches_profile(self):
        self.app(self.dest,'new','156.0')
        self.run_action('remove',source=None,apply=True)
        self.assertFalse(self.dest.exists());self.assertTrue(self.backup.exists())

    def test_rollback_requires_ack_and_matching_old_verification(self):
        self.app(self.dest,'newer','157.0')
        with self.assertRaisesRegex(ValueError,'acknowledgement'):self.run_action('rollback',apply=True)
        self.run_action('rollback',apply=True,acknowledge_profile_risk=True)
        self.assertEqual((self.dest/'payload').read_text(),'new');self.assertEqual((self.backup/'payload').read_text(),'newer')

    def test_upgrade_refuses_engine_downgrade(self):
        self.app(self.dest,'newer','157.0')
        with self.assertRaisesRegex(ValueError,'downgrade'):self.run_action('upgrade',apply=True)

    def test_original_zen_and_other_destination_names_refused(self):
        self.app(self.dest,bundle='app.zen-browser.zen')
        with self.assertRaisesRegex(ValueError,'original Zen'):self.run_action('upgrade',apply=True)
        with self.assertRaisesRegex(ValueError,'named'):self.run_action(destination=self.root/'Zen.app',apply=True)

    def test_links_existing_backup_and_overlap_refused(self):
        self.backup.symlink_to(self.root/'missing')
        with self.assertRaises(delivery.copy_tool.CopyError):self.run_action(apply=True)
        self.backup.unlink();self.backup.mkdir()
        with self.assertRaises(ValueError):self.run_action(apply=True)
        self.backup.rmdir()
        with self.assertRaises(ValueError):self.run_action(source=self.dest,apply=True)
        (self.source/'external').symlink_to(self.profile)
        with self.assertRaises(ValueError):self.run_action(apply=True)

    def test_live_app_refusal_makes_no_changes(self):
        self.app(self.dest);before=delivery.snapshot(self.dest)
        with self.assertRaisesRegex(ValueError,'live'):
            self.run_action('upgrade',apply=True,activity=lambda paths:(_ for _ in ()).throw(ValueError('live')))
        self.assertEqual(delivery.snapshot(self.dest),before);self.assertFalse(self.backup.exists())

    def test_stage_verification_failure_preserves_installed_app(self):
        self.app(self.dest);before=delivery.snapshot(self.dest)
        def reject(app,*args):
            if app!=self.source:raise ValueError('bad stage')
            return self.verify(app,*args)
        with self.assertRaisesRegex(ValueError,'bad stage'):self.run_action('upgrade',apply=True,verifier=reject)
        self.assertEqual(delivery.snapshot(self.dest),before);self.assertFalse(self.backup.exists())

    def test_publish_failure_restores_old_app(self):
        self.app(self.dest);before=delivery.snapshot(self.dest)
        def publish(source,destination):
            if '.zen-terminal-app-stage-' in str(source):raise OSError('publish failure')
            delivery.copy_tool.atomic_publish(source,destination)
        with self.assertRaisesRegex(OSError,'publish failure'):self.run_action('upgrade',apply=True,publisher=publish)
        self.assertEqual(delivery.snapshot(self.dest),before);self.assertFalse(self.backup.exists())

    def test_racing_foreign_destination_never_overwritten_during_recovery(self):
        self.app(self.dest);old=delivery.snapshot(self.dest)
        def publish(source,destination):
            if '.zen-terminal-app-stage-' in str(source):
                destination.mkdir();(destination/'foreign').write_text('KEEP');raise OSError('race')
            delivery.copy_tool.atomic_publish(source,destination)
        with self.assertRaises(Exception):self.run_action('upgrade',apply=True,publisher=publish)
        self.assertEqual((self.dest/'foreign').read_text(),'KEEP');self.assertEqual(delivery.snapshot(self.backup),old)

    def test_concurrent_process_lock_refuses_change(self):
        self.app(self.dest)
        with delivery.delivery_lock(self.root):
            code="import importlib.util,sys; from pathlib import Path; s=importlib.util.spec_from_file_location('d',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m); c=m.delivery_lock(Path(sys.argv[2]));c.__enter__()"
            result=subprocess.run([sys.executable,'-c',code,str(Path(delivery.__file__)),str(self.root)],capture_output=True)
            self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.dest/'payload').read_text(),'old')

    def test_source_mutation_during_copy_never_replaces_destination(self):
        self.app(self.dest);old=delivery.snapshot(self.dest)
        real_copy=delivery.shutil.copytree
        def changing(source,stage,*args,**kwargs):
            result=real_copy(source,stage,*args,**kwargs)
            if Path(source)==self.source:(self.source/'payload').write_text('changed after stage')
            return result
        with mock.patch.object(delivery.shutil,'copytree',side_effect=changing):
            with self.assertRaisesRegex(ValueError,'changed while staging'):self.run_action('upgrade',apply=True)
        self.assertEqual(delivery.snapshot(self.dest),old);self.assertFalse(self.backup.exists())

    def test_racing_install_destination_is_not_moved_into_backup(self):
        calls=0
        def activity(paths):
            nonlocal calls
            calls+=1
            if calls==2:
                self.dest.mkdir();(self.dest/'foreign').write_text('KEEP')
        with self.assertRaises(delivery.copy_tool.CopyError):self.run_action(apply=True,activity=activity)
        self.assertEqual((self.dest/'foreign').read_text(),'KEEP');self.assertFalse(self.backup.exists())

    def test_racing_backup_is_never_overwritten(self):
        self.app(self.dest);old=delivery.snapshot(self.dest);calls=0
        def activity(paths):
            nonlocal calls
            calls+=1
            if calls==2:
                self.backup.mkdir();(self.backup/'foreign').write_text('KEEP')
        with self.assertRaises(delivery.copy_tool.CopyError):self.run_action('upgrade',apply=True,activity=activity)
        self.assertEqual(delivery.snapshot(self.dest),old);self.assertEqual((self.backup/'foreign').read_text(),'KEEP')

    def test_same_engine_older_build_requires_explicit_rollback(self):
        self.app(self.dest,'newer','156.0',build_id='20260919130000')
        with self.assertRaisesRegex(ValueError,'older app BuildID'):self.run_action('upgrade',apply=True)
        self.assertFalse(self.backup.exists());self.assertEqual((self.dest/'payload').read_text(),'newer')
        result=self.run_action('rollback',apply=True,acknowledge_profile_risk=True)
        self.assertEqual(result['app']['build_id'],'20260919120000')

    def test_same_engine_equal_and_newer_build_upgrade_allowed(self):
        self.app(self.dest,'old','156.0',build_id='20260919110000')
        result=self.run_action('upgrade',apply=True)
        self.assertEqual(result['app']['build_id'],'20260919120000')
        self.backup.rename(self.root/'earlier.app')
        self.run_action('upgrade',apply=True)

    def test_missing_malformed_and_impossible_build_ids_refused(self):
        file=self.source/'Contents/Resources/application.ini'
        for value in ['', '20260919', '2026091912000X', '20261319120000', '20260230120000', '２０２６０９１９１２００００']:
            with self.subTest(value=value):
                file.write_text('[App]\nProfile=zen-terminal\nVersion=new\nBuildID='+value+'\n')
                with self.assertRaisesRegex(ValueError,'BuildID'):self.run_action(apply=True)
                self.assertFalse(self.dest.exists())

    def test_build_id_swap_after_initial_verification_is_refused(self):
        self.app(self.dest);old=delivery.snapshot(self.dest)
        def activity(paths):
            file=self.source/'Contents/Resources/application.ini'
            file.write_text(file.read_text().replace('20260919120000','20260918120000'))
        with self.assertRaisesRegex(ValueError,'identity changed'):
            self.run_action('upgrade',apply=True,activity=activity)
        self.assertEqual(delivery.snapshot(self.dest),old);self.assertFalse(self.backup.exists())

    def test_large_file_snapshot_does_not_use_read_bytes(self):
        file=self.source/'large-native-fixture'
        with file.open('wb') as stream:
            for _ in range(4):stream.write(b'x'*(1024*1024))
        with mock.patch.object(Path,'read_bytes',side_effect=AssertionError('Whole-file read forbidden')):
            result=delivery.snapshot(self.source)
        self.assertEqual(result['large-native-fixture'][1],delivery.hashlib.sha256(b'x'*(4*1024*1024)).hexdigest())

    def test_production_verifier_requires_signature_and_exact_assets(self):
        with mock.patch.object(delivery.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['codesign'])):
            with self.assertRaises(subprocess.CalledProcessError):delivery.verify(self.source,self.root,'new','156.0')
        with mock.patch.object(delivery.subprocess,'run') as command:
            with self.assertRaises((AssertionError,FileNotFoundError)):
                delivery.verify(self.source,self.root,'new','156.0')
            self.assertIn('--strict',command.call_args.args[0])


if __name__=='__main__':unittest.main(verbosity=2)
