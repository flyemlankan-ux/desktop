#!/usr/bin/env python3
"""Seal a recovered compiled Mac app into a NEW development-only disk image.
The original archive/app are read-only inputs. Pinned Firefox mozpack builds
real omnijar resources offline. This does not run mach package, notarize,
install, or copy user data.
"""
import argparse
import configparser
import ctypes
import stat
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone


APP_NAME = 'Zen Terminal.app'
HELPER_OLD = Path('Contents/Resources/browser/zen-terminal-pty')
HELPER_NEW = Path('Contents/MacOS/zen-terminal-pty')
DEVELOPMENT_MARKERS = (Path('Contents/Resources/browser/.purgecaches'),)
DEVELOPER_PATH_KEYS = ('MozillaDeveloperObjPath', 'MozillaDeveloperRepoPath')
TEST_PLUGIN_DIRS = (Path('Contents/Resources/gmp-fake'), Path('Contents/Resources/gmp-fakeopenh264'))


def digest_stream(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
    return digest.hexdigest()


def digest_file(path):
    with path.open('rb') as stream:
        return digest_stream(stream)


def manifest(app):
    result = {}
    for item in sorted(app.rglob('*')):
        mode = item.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError(f'Recovered input must not contain unreviewed symlinks: {item}')
        if not stat.S_ISREG(mode) and not stat.S_ISDIR(mode):
            raise ValueError(f'Recovered input contains a special file: {item}')
        if stat.S_ISREG(mode):
            result[item.relative_to(app).as_posix()] = digest_file(item)
    return result


def atomic_publish(stage, destination):
    """macOS atomic no-replace rename, including an existing empty directory."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renamex_np
    rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(os.fsencode(stage), os.fsencode(destination), 4):  # RENAME_EXCL
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


def is_macho(path):
    with path.open('rb') as stream:
        magic = stream.read(4)
    return magic in {b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe',
                     b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe',
                     b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
                     b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca'}


def verify_signing_changes(raw_manifest, final_manifest, source, app):
    expected = dict(raw_manifest)
    if HELPER_OLD.as_posix() in expected:
        expected[HELPER_NEW.as_posix()] = expected.pop(HELPER_OLD.as_posix())
    changed = []
    for relative in sorted(expected.keys() | final_manifest.keys()):
        if expected.get(relative) == final_manifest.get(relative):
            continue
        if relative not in final_manifest:
            raise ValueError(f'Signing removed an unexpected file: {relative}')
        if relative.endswith('/_CodeSignature/CodeResources'):
            changed.append(relative)
            continue
        original = source / (HELPER_OLD if relative == HELPER_NEW.as_posix() else relative)
        if relative not in expected or not is_macho(original) or not is_macho(app / relative):
            raise ValueError(f'Signing changed a non-executable resource: {relative}')
        changed.append(relative)
    return changed


def remove_development_only_metadata(app):
    """Mirror reviewed upstream packaging cleanup, without touching user data."""
    removed_markers = []
    for relative in DEVELOPMENT_MARKERS:
        marker = app / relative
        if marker.exists():
            removed_markers.append({'path': relative.as_posix(), 'sha256': digest_file(marker)})
            marker.unlink()
    plist_changes = []
    for file in sorted(app.rglob('Info.plist')):
        data = file.read_bytes()
        original = plistlib.loads(data)
        removed = [key for key in DEVELOPER_PATH_KEYS if key in original]
        if not removed:
            continue
        cleaned = {key: value for key, value in original.items() if key not in DEVELOPER_PATH_KEYS}
        fmt = plistlib.FMT_BINARY if data.startswith(b'bplist') else plistlib.FMT_XML
        file.write_bytes(plistlib.dumps(cleaned, fmt=fmt, sort_keys=False))
        if plistlib.loads(file.read_bytes()) != cleaned:
            raise ValueError(f'Unexpected plist change: {file}')
        plist_changes.append({'path': file.relative_to(app).as_posix(), 'removedKeys': removed,
                              'beforeSha256': hashlib.sha256(data).hexdigest(), 'afterSha256': digest_file(file),
                              'otherValuesPreserved': True})
    removed_plugins = []
    policy = Path(__file__).resolve().parent / 'fixtures/firefox155-settings/browser/installer/package-manifest.in'
    policy_text = policy.read_text()
    if '@RESPATH@/gmp-clearkey/' not in policy_text or any(path.name in policy_text for path in TEST_PLUGIN_DIRS):
        raise ValueError('Pinned package policy does not justify excluding the two test-only plugins')
    for relative in TEST_PLUGIN_DIRS:
        directory = app / relative
        if directory.exists():
            removed_plugins.append({'path': relative.as_posix(), 'filesSha256': manifest(directory)})
            shutil.rmtree(directory)
    return {'removedDevelopmentCacheMarkers': removed_markers, 'removedDeveloperPathPlistKeys': plist_changes,
            'removedTestOnlyPlugins': removed_plugins, 'testPluginExclusionPolicySha256': digest_file(policy)}


def verify_archive(archive, raw_manifest):
    """Match every recovered file to the original cloud archive, without extracting."""
    archived = {}
    with tarfile.open(archive, 'r:gz') as source:
        for item in source:
            name = PurePosixPath(item.name)
            if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] != APP_NAME:
                raise ValueError(f'Unexpected archive path: {item.name}')
            if item.isdir():
                continue
            if not item.isfile():
                raise ValueError(f'Unexpected archive link or special file: {item.name}')
            relative = PurePosixPath(*name.parts[1:]).as_posix()
            if relative in archived:
                raise ValueError(f'Duplicate archive entry: {item.name}')
            with source.extractfile(item) as stream:
                archived[relative] = digest_stream(stream)
    if archived != raw_manifest:
        differences = sorted(key for key in archived.keys() | raw_manifest.keys()
                             if archived.get(key) != raw_manifest.get(key))
        raise ValueError(f'Recovered app differs from original archive: {differences[:10]}')


def load_mozpack(tool_root):
    receipt_file = tool_root / 'receipt.json'
    receipt = json.loads(receipt_file.read_text())
    tracked = Path(__file__).resolve().parent / 'fixtures/firefox155-mozpack-receipt.json'
    if receipt != json.loads(tracked.read_text()):
        raise ValueError('Local mozpack receipt differs from the tracked pinned receipt')
    if receipt.get('ref') != 'FIREFOX_155_0_1_RELEASE':
        raise ValueError('mozpack must be pinned to Firefox155.0.1')
    for relative, evidence in receipt['files'].items():
        if digest_file(tool_root / relative) != evidence['sha256']:
            raise ValueError(f'Pinned mozpack source changed: {relative}')
    for name, module in list(sys.modules.items()):
        if name.split('.')[0] in {'mozpack', 'mozbuild'} and getattr(module, '__file__', None):
            if tool_root not in Path(module.__file__).resolve().parents:
                raise ValueError(f'Already-loaded packaging module is outside the pinned tool root: {name}')
    sys.path.insert(0, str(tool_root / 'python/mozbuild'))
    from mozpack.copier import FileCopier
    from mozpack.files import FileFinder
    from mozpack.mozjar import JarReader
    from mozpack.packager import SimplePackager
    from mozpack.packager.formats import OmniJarFormatter
    return FileCopier, FileFinder, JarReader, SimplePackager, OmniJarFormatter, receipt_file


def pack_omnijars(prepared, destination, tool_root):
    FileCopier, FileFinder, JarReader, SimplePackager, OmniJarFormatter, receipt = load_mozpack(tool_root)
    copier = FileCopier()
    packer = SimplePackager(OmniJarFormatter(copier, 'omni.ja'))
    for relative, file in FileFinder(str(prepared), find_executables=False):
        packer.add(relative, file)
    packer.close()
    copier.copy(str(destination))
    before = manifest(prepared)
    after = manifest(destination)
    checked_binaries = 0
    for relative, sha in before.items():
        if is_macho(prepared / relative):
            if after.get(relative) != sha:
                raise ValueError(f'Offline resource packing changed a native binary: {relative}')
            checked_binaries += 1
    jars = {}
    for relative in ['Contents/Resources/omni.ja', 'Contents/Resources/browser/omni.ja']:
        archive = destination / relative
        if not archive.is_file():
            raise ValueError(f'Upstream mozpack did not create required archive: {relative}')
        with archive.open('rb') as stream:
            reader = JarReader(fileobj=stream)
            entries = list(reader)
            jars[relative] = {'sha256': digest_file(archive), 'entries': len(entries)}
            if relative.endswith('browser/omni.ja'):
                for name in ['chrome/browser/content/browser/zen-terminal/ZenTerminalPage.mjs',
                             'chrome/browser/content/browser/ZenUIManager.mjs']:
                    if reader[name].read() != (prepared / 'Contents/Resources/browser' / name).read_bytes():
                        raise ValueError(f'Packed browser source changed: {name}')
    return {'tool': 'Firefox155.0.1 mozpack SimplePackager + OmniJarFormatter (default resource rules)',
            'pinnedToolReceiptSha256': digest_file(receipt), 'omnijars': jars,
            'nativeBinaryFilesByteVerifiedBeforeSigning': checked_binaries}


def identity(app, expected_revision, engine, packed=False):
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    expected = {'CFBundleIdentifier': 'app.zen-browser.zen-terminal',
                'CFBundleExecutable': 'zen-terminal'}
    if any(info.get(key) != value for key, value in expected.items()):
        raise ValueError('Unexpected app identity or executable; refusing to relabel it')
    app_ini = configparser.ConfigParser()
    app_ini.read(app / 'Contents/Resources/application.ini')
    platform = configparser.ConfigParser()
    platform.read(app / 'Contents/Resources/platform.ini')
    if app_ini['App']['Profile'] != 'zen-terminal' or app_ini['App']['RemotingName'] != 'zen-terminal':
        raise ValueError('Compiled app metadata does not identify a separate Zen Terminal profile')
    if app_ini['App']['SourceStamp'] != expected_revision or platform['Build']['SourceStamp'] != expected_revision:
        raise ValueError('Compiled source revision does not match the requested recovery')
    if platform['Build']['Milestone'] != engine or app_ini['Gecko']['MinVersion'] != engine or app_ini['Gecko']['MaxVersion'] != engine:
        raise ValueError('Unexpected compiled browser engine')
    if app_ini['App']['BuildID'] != platform['Build']['BuildID']:
        raise ValueError('App/engine build IDs disagree')
    resources = app / 'Contents/Resources'
    if packed:
        if not (resources / 'omni.ja').is_file() or not (resources / 'browser/omni.ja').is_file():
            raise ValueError('Expected genuine GRE and browser omnijar archives')
    elif list(resources.rglob('omni.ja')):
        raise ValueError('Input must be the raw loose-resource recovery')
    page = resources / 'browser/chrome/browser/content/browser/zen-terminal/ZenTerminalPage.mjs'
    if (not packed and not page.is_file()) or not (app / 'Contents/MacOS/zen-terminal').is_file():
        raise ValueError('Missing real compiled executable or terminal page')
    return {'bundleIdentifier': info['CFBundleIdentifier'], 'executable': info['CFBundleExecutable'],
            'profile': app_ini['App']['Profile'], 'engine': engine, 'sourceRevision': expected_revision,
            'buildId': app_ini['App']['BuildID'], 'version': app_ini['App']['Version']}


def entitlements(app):
    result = subprocess.run(['codesign', '-d', '--entitlements', ':-', str(app)], capture_output=True, check=True)
    claims = plistlib.loads(result.stdout) if result.stdout.strip() else {}
    restricted = [key for key in claims if key == 'com.apple.application-identifier' or key.startswith('com.apple.developer.')]
    if restricted:
        raise ValueError(f'Restricted Apple signing claims cannot be preserved in a development signature: {restricted}')
    return claims


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--source-app', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--expected-revision', required=True)
    parser.add_argument('--expected-engine', default='155.0.1')
    parser.add_argument('--mozpack-root', type=Path, default=Path(__file__).resolve().parents[2] / '.terminal-test/mozpack155')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('This recovery requires macOS signing and disk-image tools')
    source = args.source_app.resolve(strict=True)
    archive = args.archive.resolve(strict=True)
    output = args.output_dir.absolute()
    if output.exists() or output.is_symlink():
        parser.error('Output must be a NEW directory; overwriting is never allowed')
    if source.name != APP_NAME or not source.is_dir() or not archive.is_file():
        parser.error('Expected the recovered Zen Terminal.app and original archive')
    parent = output.parent.resolve(strict=True)
    if parent == source or source in parent.parents or str(parent).startswith('/Applications'):
        parser.error('Output must be outside the source app and /Applications')
    output = parent / output.name
    expected_identity = identity(source, args.expected_revision, args.expected_engine)
    if not (source / HELPER_OLD).is_file() or (source / HELPER_NEW).exists():
        parser.error('Expected exactly the misplaced Resources/browser helper and no MacOS helper')
    raw_manifest = manifest(source)
    archive_sha = digest_file(archive)
    verify_archive(archive, raw_manifest)
    print(f'Verified {len(raw_manifest)} recovered files against the original archive.', flush=True)
    original_helper = raw_manifest[HELPER_OLD.as_posix()]
    original_entitlements = entitlements(source)
    work = Path(tempfile.mkdtemp(prefix='.zen-terminal-recovery-', dir=parent))
    try:
        image = work / 'finished'
        image.mkdir()
        app = work / 'prepared' / APP_NAME
        app.parent.mkdir()
        subprocess.run(['ditto', str(source), str(app)], check=True)
        if manifest(app) != raw_manifest:
            raise ValueError('Copy did not preserve recovered file bytes')
        (app / HELPER_OLD).rename(app / HELPER_NEW)
        moved_helper = digest_file(app / HELPER_NEW)
        if moved_helper != original_helper:
            raise ValueError('Relocating the helper changed its bytes')
        if not os.access(app / HELPER_NEW, os.X_OK):
            raise ValueError('Recovered helper is not executable; refusing an unexplained permission change')
        packaging_cleanup = remove_development_only_metadata(app)
        prepared = app
        app = image / APP_NAME
        omnijar_packing = pack_omnijars(prepared, app, args.mozpack_root.resolve(strict=True))
        if digest_file(app / HELPER_NEW) != moved_helper:
            raise ValueError('Resource packing changed relocated helper bytes')
        before_sign_manifest = manifest(app)
        # Only signing-forbidden Finder metadata, only in OUR new copy.
        for attribute in ('com.apple.FinderInfo', 'com.apple.ResourceFork'):
            subprocess.run(['xattr', '-dr', attribute, str(app)], check=True)
        subprocess.run(['codesign', '--force', '--deep', '--sign', '-', '--preserve-metadata=entitlements', str(app)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
        if entitlements(app) != original_entitlements:
            raise ValueError('Development signing unexpectedly changed browser capabilities')
        if identity(app, args.expected_revision, args.expected_engine, packed=True) != expected_identity:
            raise ValueError('Recovery changed the compiled app identity')
        (image / 'Applications').symlink_to('/Applications', target_is_directory=True)
        dmg_name = 'Zen-Terminal-recovered-development.dmg'
        dmg = work / dmg_name
        subprocess.run(['hdiutil', 'create', '-quiet', '-format', 'UDZO', '-volname', 'Zen Terminal Development', '-srcfolder', str(image), str(dmg)], check=True)
        subprocess.run(['hdiutil', 'verify', str(dmg)], check=True)
        final_manifest = manifest(app)
        changed = verify_signing_changes(before_sign_manifest, final_manifest, source, app)
        # Recheck original inputs after all write operations; do not trust only paths.
        if manifest(source) != raw_manifest or digest_file(archive) != archive_sha:
            raise ValueError('Original input changed during recovery')
        receipt = {
            'createdAtUtc': datetime.now(timezone.utc).isoformat(),
            'scope': 'Recovered cloud-compiled development app with real Firefox mozpack omnijars; NOT full upstream mach package and NOT Apple-notarized.',
            'limitations': ['Native developer extras outside the two explicitly excluded fake plugins remain; this is not full upstream package-manifest selection.',
                            'Disk image is a plain development image with an Applications shortcut, not upstream installer styling.',
                            'Signing and archive checks do not prove browser behavior; separate actual-app testing is required.'],
            'originalArchive': {'path': str(archive), 'sha256': archive_sha},
            'originalApp': {'path': str(source), 'fileCount': len(raw_manifest), 'matchesArchive': True, 'unchangedAfterRecovery': True},
            'identity': expected_identity,
            'reviewedDevelopmentPackagingCleanup': packaging_cleanup,
            'upstreamResourcePacking': omnijar_packing,
            'helper': {'originalRelativePath': HELPER_OLD.as_posix(), 'newRelativePath': HELPER_NEW.as_posix(),
                       'originalSha256': original_helper, 'afterRelocationSha256': moved_helper,
                       'afterDevelopmentSigningSha256': digest_file(app / HELPER_NEW), 'relocationPreservedBytes': True},
            'developmentSignature': {'wholeBundleStrictVerification': True, 'entitlementNames': sorted(original_entitlements),
                                     'signatureModifiedFiles': changed, 'onlyMachOOrSignatureMetadataChanged': True},
            'diskImage': {'name': dmg_name, 'sha256': digest_file(dmg), 'verified': True},
            'installed': False,
        }
        (image / 'recovery-provenance.json').write_text(json.dumps(receipt, indent=2) + '\n')
        dmg.rename(image / dmg_name)
        if output.exists() or output.is_symlink():
            raise FileExistsError('Output appeared during recovery; refusing to overwrite it')
        atomic_publish(image, output)
        print(f'Created development app, disk image, and provenance: {output}')
    finally:
        shutil.rmtree(work)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Recovery stopped: {error}', file=sys.stderr)
        sys.exit(1)
