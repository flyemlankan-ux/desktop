#!/usr/bin/env python3
"""Explicit, app-only delivery. Dry-run by default. Never launches or edits profiles.

Remove retains the app at --backup; it never erases it. Rollback requires the
source checkout matching the old app and explicit acknowledgement that upgraded
profiles may be incompatible. This tool never bypasses browser downgrade checks.
All app symlinks are currently refused, including internal framework links. A
future bundle needing those requires separate review; links are not silently followed.
"""
import argparse
import configparser
from datetime import datetime
import contextlib
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


copy_tool = module('copy-zen-profiles')


def safe_path(value):
    path = Path(os.path.abspath(value))
    copy_tool.reject_symlink_ancestors(path)
    return path


def file_digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def snapshot(app):
    safe_path(app)
    if not app.is_dir(): raise ValueError('App directory disappeared')
    result = {}
    def fail_walk(error): raise error
    for directory, dirs, files in os.walk(app, followlinks=False, onerror=fail_walk):
        for name in dirs + files:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ValueError('App links and special files require separate review')
            relative = path.relative_to(app).as_posix()
            result[relative] = (stat.S_IMODE(mode), file_digest(path) if stat.S_ISREG(mode) else None)
    return result


def identity(app, expected_version=None, expected_engine=None):
    if not app.is_dir(): raise ValueError('App directory is missing')
    snapshot(app)  # Refuse links before reading identity files.
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    if (info.get('CFBundleIdentifier'), info.get('CFBundleExecutable')) != ('app.zen-browser.zen-terminal', 'zen-terminal'):
        raise ValueError('Not the separate Zen Terminal app; original Zen is forbidden')
    config = configparser.ConfigParser(interpolation=None)
    config.read(app / 'Contents/Resources/application.ini')
    if config.get('App', 'Profile', fallback='') != 'zen-terminal':
        raise ValueError('App does not have its separate browser profile root')
    version = config.get('App', 'Version', fallback='')
    build_id = config.get('App', 'BuildID', fallback='')
    if not re.fullmatch(r'[0-9]{14}', build_id):
        raise ValueError('App BuildID must be a 14-digit build timestamp')
    try:
        datetime.strptime(build_id, '%Y%m%d%H%M%S')
    except ValueError as error:
        raise ValueError('App BuildID is not a valid build timestamp') from error
    platform = configparser.ConfigParser(interpolation=None)
    platform.read(app / 'Contents/Resources/platform.ini')
    engine = platform.get('Build', 'Milestone', fallback='')
    copy_tool.version_key(engine)
    if not version or (expected_version is not None and version != expected_version):
        raise ValueError('App version does not match the explicit expected version')
    if expected_engine is not None and engine != expected_engine:
        raise ValueError('Engine does not match the explicit expected engine')
    return {'version': version, 'engine': engine, 'build_id': build_id}


def verify(app, root, expected_version, expected_engine):
    result = identity(app, expected_version, expected_engine)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    module('verify-terminal-app-assets').verify(app, root)
    if module('check-terminal-package-privacy').check_image(app):
        raise ValueError('Recognizable profile data found inside app')
    return result


def closed(paths):
    result = subprocess.run(['/bin/ps', '-axo', 'comm='], text=True, capture_output=True, check=True)
    if any(Path(line.strip()).name.lower() == 'zen-terminal' for line in result.stdout.splitlines()):
        raise ValueError('Close every Zen Terminal window before changing the app')
    lsof = shutil.which('lsof') or '/usr/sbin/lsof'
    for app in paths:
        if not app.exists(): continue
        result = subprocess.run([lsof, '-t', '+D', str(app)], text=True, capture_output=True, timeout=30)
        if result.returncode not in (0, 1) or result.stderr.strip() or result.stdout.strip():
            raise ValueError('App files are open or activity cannot be checked safely')


@contextlib.contextmanager
def delivery_lock(parent):
    lock = parent / '.zen-terminal-app-delivery.lock'
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid():
            raise ValueError('Unsafe delivery lock file')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)  # Keep the lock file: unlinking permits competing lock inodes.


def manage(action, destination, backup, source=None, root=None, expected_version=None,
           expected_engine=None, apply=False, acknowledge_profile_risk=False,
           verifier=verify, activity=closed, publisher=copy_tool.atomic_publish):
    if action not in {'install', 'upgrade', 'rollback', 'remove'}: raise ValueError('Unknown action')
    destination, backup = safe_path(destination), safe_path(backup)
    source = safe_path(source) if source else None
    if destination.name != 'Zen Terminal.app': raise ValueError('Destination must be named Zen Terminal.app')
    if not destination.parent.is_dir() or backup.parent != destination.parent or backup == destination:
        raise ValueError('Backup must be a distinct new sibling on the same filesystem')
    if backup.exists(): raise ValueError('Backup already exists; overwriting is forbidden')
    if action == 'install' and destination.exists(): raise ValueError('Install destination already exists')
    if action != 'install' and not destination.is_dir(): raise ValueError('Installed app is missing')
    if action == 'rollback' and not acknowledge_profile_risk:
        raise ValueError('Rollback may be incompatible with upgraded profiles; explicit acknowledgement required')
    if action != 'remove':
        if not source or not source.is_dir(): raise ValueError('Source app is required')
        if any(copy_tool.inside(source, path) or copy_tool.inside(path, source) for path in (destination, backup)):
            raise ValueError('Source, destination and backup must not overlap')
    elif source:
        raise ValueError('Remove does not accept a source')
    if not root or not expected_version or not expected_engine:
        raise ValueError('Explicit verification checkout, expected app version and engine are required')
    checked = source if source else destination
    details = verifier(checked, Path(root), expected_version, expected_engine)
    old = identity(destination) if destination.exists() else None
    if old and action != 'rollback' and copy_tool.version_key(details['engine']) < copy_tool.version_key(old['engine']):
        raise ValueError('Upgrade cannot downgrade the browser engine')
    if (old and action == 'upgrade' and
        copy_tool.version_key(details['engine']) == copy_tool.version_key(old['engine']) and
        details['build_id'] < old['build_id']):
        raise ValueError('Upgrade cannot install an older app BuildID on the same engine; use explicit rollback')
    activity([p for p in (source, destination) if p])
    summary = {'action': action, 'applied': False, 'profiles_changed': False,
               'launch_performed': False, 'app': details,
               'warning': 'Retained apps do not make upgraded profiles backward-compatible. No browser is launched.'}
    if not apply: return summary
    with delivery_lock(destination.parent):
        # Recheck after taking the cross-process lock; validation above is not a reservation.
        if backup.exists() or backup.is_symlink(): raise ValueError('Backup appeared during preparation')
        safe_path(destination); safe_path(backup)
        if (action == 'install') == destination.exists(): raise ValueError('Destination changed during preparation')
        before = snapshot(destination) if destination.exists() else None
        if destination.exists():
            current = identity(destination)
            if current != old: raise ValueError('Installed app identity changed during preparation')
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(destination)], check=True) if verifier is verify else None
        stage_root = Path(tempfile.mkdtemp(prefix='.zen-terminal-app-stage-', dir=destination.parent))
        stage = stage_root / 'Zen Terminal.app'
        retained = False
        try:
            if source:
                original = snapshot(source)
                shutil.copytree(source, stage, copy_function=shutil.copy2)
                if snapshot(stage) != original or snapshot(source) != original:
                    raise ValueError('Source app changed while staging')
                if verifier(stage, Path(root), expected_version, expected_engine) != details:
                    raise ValueError('Source app identity changed before staged verification')
            activity([p for p in (source, destination) if p])
            safe_path(destination); safe_path(backup)
            if before is not None and snapshot(destination) != before:
                raise ValueError('Installed app changed during preparation')
            if before is not None:
                publisher(destination, backup)
                retained = True
            if source:
                try:
                    publisher(stage, destination)
                except BaseException:
                    if retained:
                        # No-overwrite recovery. If another app appeared, keep the
                        # verified old copy at backup rather than destroying it.
                        try:
                            publisher(backup, destination)
                        except Exception as recovery_error:
                            raise RuntimeError(
                                f'Automatic restoration could not safely replace the destination. '
                                f'The previous app is retained at {backup}. Profiles are untouched; '
                                'do not launch an older app against upgraded profiles.'
                            ) from recovery_error
                    raise
            summary.update(applied=True, previous_app_retained=retained, backup=str(backup) if retained else None)
            return summary
        finally:
            shutil.rmtree(stage_root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'upgrade', 'rollback', 'remove'])
    for name in ('destination', 'backup', 'verification-root', 'expected-version', 'expected-engine'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--source')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--acknowledge-profile-risk', action='store_true')
    args = parser.parse_args()
    try:
        import json
        print(json.dumps(manage(args.action, args.destination, args.backup, args.source,
            args.verification_root, args.expected_version, args.expected_engine,
            args.apply, args.acknowledge_profile_risk), indent=2))
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, AssertionError) as error:
        print(f'App change stopped: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__': sys.exit(main())
