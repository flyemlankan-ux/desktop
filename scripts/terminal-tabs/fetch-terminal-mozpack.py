#!/usr/bin/env python3
"""Fetch the exact public Firefox packaging tools recorded in the source receipt.

Requires GitHub CLI (gh). Downloads source only; never runs downloaded code.
Output must be a new directory. No browser build or personal data is involved.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    receipt_path = Path(__file__).with_name('fixtures') / 'firefox155-mozpack-receipt.json'
    receipt = json.loads(receipt_path.read_text())
    # mkdir's exclusive creation rejects both an existing directory and a symlink.
    args.output.mkdir(mode=0o700)

    def fetch(item):
        relative, expected = item
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe receipt path')
        data = subprocess.check_output([
            'gh', 'api', f"{receipt['repository']}/git/blobs/{expected['git_blob_sha1']}",
            '-H', 'Accept: application/vnd.github.raw+json',
        ])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != expected['git_blob_sha1'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
            raise ValueError(f'Public source hash mismatch: {relative}')
        target = args.output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(fetch, receipt['files'].items()))
    # A receipt appears only after every file passes; recovery checks it again.
    (args.output / 'receipt.json').write_bytes(receipt_path.read_bytes())
    print(f"Fetched and verified {len(receipt['files'])} pinned Firefox packaging files.")


if __name__ == '__main__':
    main()
