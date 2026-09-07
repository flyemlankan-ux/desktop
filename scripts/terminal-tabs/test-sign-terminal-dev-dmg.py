#!/usr/bin/env python3
"""Exercise development DMG signing with a tiny synthetic native app, not Zen data."""
import pathlib, plistlib, subprocess, tempfile
root = pathlib.Path(__file__).resolve().parents[2]
script = root / 'scripts/terminal-tabs/sign-terminal-dev-dmg.sh'
with tempfile.TemporaryDirectory(prefix='zen-sign-proof-') as temporary:
    work = pathlib.Path(temporary)
    app = work / 'image/Zen Terminal.app'
    (app / 'Contents/MacOS').mkdir(parents=True)
    (app / 'Contents/Info.plist').write_bytes(plistlib.dumps({
        'CFBundleIdentifier': 'app.zen-browser.zen-terminal',
        'CFBundleName': 'Zen Terminal', 'CFBundleExecutable': 'zen-terminal',
        'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
    }))
    source = work / 'main.c'
    source.write_text('int main(void) { return 0; }\n')
    subprocess.run(['clang', str(source), '-o', str(app / 'Contents/MacOS/zen-terminal')], check=True)
    subprocess.run(['xattr', '-wx', 'com.apple.FinderInfo', '00'*32, str(app)], check=True)
    original = work / 'original.dmg'
    subprocess.run(['hdiutil', 'create', '-quiet', '-format', 'UDZO', '-srcfolder', str(work / 'image'), str(original)], check=True)
    output = work / 'signed.dmg'
    subprocess.run([str(script), str(original), str(output)], check=True)
    before = output.read_bytes()
    assert subprocess.run([str(script), str(original), str(output)], capture_output=True).returncode != 0
    assert output.read_bytes() == before
    assert subprocess.run([str(script), str(work / 'missing.dmg'), str(work / 'new.dmg')], capture_output=True).returncode != 0
    mount = work / 'mount'; mount.mkdir()
    subprocess.run(['hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', str(mount), str(output)], check=True, stdout=subprocess.DEVNULL)
    try:
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(mount / 'Zen Terminal.app')], check=True)
        assert (mount / 'Applications').is_symlink()
    finally:
        subprocess.run(['hdiutil', 'detach', str(mount)], check=True, stdout=subprocess.DEVNULL)
print('PASS development DMG signing, complete seal, Applications shortcut, no overwrite and missing-input refusal')
