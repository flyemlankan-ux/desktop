#!/usr/bin/env python3
"""Package the browser and its languages. Never generate stock updater files."""
from pathlib import Path
import re
import subprocess


def package_commands(root):
    mapping = {}
    for row in (root / 'locales/language-maps').read_text().splitlines():
        if row.strip():
            key, value = row.strip().split(':')
            mapping[key] = value
    locales = [mapping.get(row.strip(), row.strip()) for row in
               (root / 'locales/supported-languages').read_text().splitlines() if row.strip()]
    if not locales or any(not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]+)*', locale) for locale in locales):
        raise ValueError('Invalid supported language list')
    mach = str(root / 'engine/mach')
    return [[mach, 'package'], [mach, 'package-multi-locale', '--locales', *locales]]


def main():
    root = Path(__file__).resolve().parents[2]
    for command in package_commands(root):
        subprocess.run(command, cwd=root / 'engine', check=True)


if __name__ == '__main__':
    main()
