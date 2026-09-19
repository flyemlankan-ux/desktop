#!/usr/bin/env python3
"""Reject recognizable browser profile data anywhere in a distributable image.

Only names are examined, including archive member names. No profile contents are
read or printed. Symlinks are not traversed; only the root Applications shortcut
may point outside the image. This is a known-artifact check, not secret detection.
"""
import argparse
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile

PRIVATE_NAMES = frozenset({
    'profiles.ini', 'installs.ini', 'cookies.sqlite', 'key3.db', 'key4.db',
    'logins.json', 'logins-backup.json', 'places.sqlite', 'favicons.sqlite',
    'formhistory.sqlite', 'webappsstore.sqlite', 'permissions.sqlite',
    'content-prefs.sqlite', 'sessionstore.jsonlz4', 'sessionstore.js',
    'sessionstore-backups', 'recovery.jsonlz4', 'recovery.baklz4',
    'previous.jsonlz4', 'containers.json', 'zen-workspaces.json',
    'zen-sessions.json', 'zen-sessions.jsonlz4', 'zen-terminal-copy-verification.json',
})


def private_name(name):
    lower = name.lower()
    if lower in PRIVATE_NAMES:
        return True
    return any(lower == database + suffix for database in PRIVATE_NAMES
               if database.endswith('.sqlite') for suffix in ('-wal', '-shm', '-journal'))


def check_image(image):
    image = Path(image)
    if image.is_symlink() or not image.is_dir():
        raise ValueError('Image root must be a real directory, not a symlink')
    image = image.resolve(strict=True)
    findings = []

    def walk_error(error):
        raise ValueError('Cannot inspect every image directory') from error

    for directory, dirs, files in os.walk(image, followlinks=False, onerror=walk_error):
        for name in dirs + files:
            path = Path(directory) / name
            relative = path.relative_to(image).as_posix()
            if private_name(name):
                findings.append(relative)
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                link = os.readlink(path)
                if relative == 'Applications' and link == '/Applications':
                    continue
                # Normalize lexically only: resolve() could inspect another
                # symlink outside the image. Every physical in-image link is
                # checked separately by this non-following walk.
                target = Path(os.path.abspath(path.parent / link))
                if target != image and image not in target.parents:
                    raise ValueError('Image has an external symlink other than the Applications shortcut')
                continue  # Never open or traverse a symlink, including archives.
            if stat.S_ISDIR(mode):
                continue
            if not stat.S_ISREG(mode):
                raise ValueError('Image has a special file that cannot be inspected safely')
            if path.suffix.lower() not in {'.ja', '.zip', '.xpi'}:
                continue
            # Read archive metadata only; never extract or open member contents.
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if len(entries) > 100000:
                    raise ValueError('Archive has too many entries to inspect safely')
                for member in entries:
                    parts = PurePosixPath(member.filename.replace('\\', '/')).parts
                    if any(private_name(part) for part in parts):
                        findings.append(relative + '::' + member.filename)
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    try:
        findings = check_image(args.image)
        if findings:
            print(f'Package privacy check failed: {len(findings)} recognizable profile artifacts.', file=sys.stderr)
            return 1
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        # Do not print paths/member names that could contain private profile names.
        print(f'Package privacy check could not safely complete ({type(error).__name__}).', file=sys.stderr)
        return 1
    print('Package privacy check passed: no recognized profile artifacts in image or resource archives.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
