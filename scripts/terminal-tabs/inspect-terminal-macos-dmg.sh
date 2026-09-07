#!/usr/bin/env bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -euo pipefail

readonly EXPECTED_APP_NAME="Zen Terminal.app"
readonly EXPECTED_BUNDLE_ID="app.zen-browser.zen-terminal"
readonly EXPECTED_EXECUTABLE="zen-terminal"
readonly STOCK_UPDATE_HOST="updates.zen-browser.app"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/zen-terminal.dmg" >&2
  exit 64
fi

readonly DMG_PATH="$1"
if [[ ! -f "$DMG_PATH" ]]; then
  echo "DMG does not exist: $DMG_PATH" >&2
  exit 66
fi

readonly MOUNT_POINT="$(mktemp -d "${TMPDIR:-/tmp}/zen-terminal-dmg.XXXXXX")"
mounted=false

cleanup() {
  if [[ "$mounted" == "true" ]]; then
    hdiutil detach "$MOUNT_POINT" >/dev/null 2>&1 ||
      hdiutil detach -force "$MOUNT_POINT" >/dev/null 2>&1 ||
      true
  fi
  rm -rf "$MOUNT_POINT"
}
trap cleanup EXIT

fail() {
  echo "DMG inspection failed: $*" >&2
  exit 1
}

read_plist_value() {
  local key="$1"
  local plist="$2"
  /usr/libexec/PlistBuddy -c "Print :${key}" "$plist"
}

echo "Verifying DMG structure..."
hdiutil verify "$DMG_PATH" >/dev/null
hdiutil attach \
  -readonly \
  -nobrowse \
  -mountpoint "$MOUNT_POINT" \
  "$DMG_PATH" >/dev/null
mounted=true

readonly APP_PATH="$MOUNT_POINT/$EXPECTED_APP_NAME"
[[ -d "$APP_PATH" ]] ||
  fail "expected $EXPECTED_APP_NAME at the top level"

shopt -s nullglob
packaged_apps=("$MOUNT_POINT"/*.app)
if [[ ${#packaged_apps[@]} -ne 1 ]]; then
  fail "expected exactly one top-level app, found ${#packaged_apps[@]}"
fi

codesign --verify --deep --strict "$APP_PATH" || fail "complete app development signature is invalid"

readonly INFO_PLIST="$APP_PATH/Contents/Info.plist"
[[ -f "$INFO_PLIST" ]] || fail "Info.plist is missing"

bundle_name="$(read_plist_value CFBundleName "$INFO_PLIST")"
bundle_id="$(read_plist_value CFBundleIdentifier "$INFO_PLIST")"
bundle_executable="$(read_plist_value CFBundleExecutable "$INFO_PLIST")"

[[ "$bundle_name" == "Zen Terminal" ]] ||
  fail "CFBundleName is '$bundle_name', expected 'Zen Terminal'"
[[ "$bundle_id" == "$EXPECTED_BUNDLE_ID" ]] ||
  fail "CFBundleIdentifier is '$bundle_id', expected '$EXPECTED_BUNDLE_ID'"
[[ "$bundle_executable" == "$EXPECTED_EXECUTABLE" ]] ||
  fail "CFBundleExecutable is '$bundle_executable', expected '$EXPECTED_EXECUTABLE'"
[[ -x "$APP_PATH/Contents/MacOS/$EXPECTED_EXECUTABLE" ]] ||
  fail "terminal executable is missing or not executable"

if [[ -e "$APP_PATH/Contents/MacOS/updater.app" ]]; then
  fail "updater.app is still packaged"
fi
if [[ -e "$APP_PATH/Contents/Library/LaunchServices/org.mozilla.updater" ]]; then
  fail "the privileged Mozilla updater is still packaged"
fi

[[ -x "$APP_PATH/Contents/MacOS/zen-terminal-pty" ]] ||
  fail "native terminal helper is missing"
codesign --verify "$APP_PATH/Contents/MacOS/zen-terminal-pty" ||
  fail "native terminal helper signature is invalid"

readonly APPLICATION_INI="$APP_PATH/Contents/Resources/application.ini"
[[ -f "$APPLICATION_INI" ]] || fail "application.ini is missing"

grep -Fxq 'Profile=zen-terminal' "$APPLICATION_INI" ||
  fail "application profile root is not isolated from stock Zen"
if find "$APP_PATH" \( -name profiles.ini -o -name cookies.sqlite -o -name key4.db -o -name logins.json \) -print -quit | grep -q .; then
  fail "private browser profile data found inside the distributable"
fi

if grep -Fq "[AppUpdate]" "$APPLICATION_INI"; then
  fail "application.ini still contains an AppUpdate section"
fi
if grep -Fq "$STOCK_UPDATE_HOST" "$APPLICATION_INI"; then
  fail "application.ini still points at the stock Zen update service"
fi
if grep -aFq \
  "$STOCK_UPDATE_HOST" \
  "$APP_PATH/Contents/MacOS/$EXPECTED_EXECUTABLE"; then
  fail "the terminal executable still contains the stock Zen update address"
fi

# Verify the shipped terminal assets, not merely the app's name.
python3 - "$APP_PATH" <<'VERIFY'
from pathlib import Path
import configparser, json, re, sys, zipfile
app = Path(sys.argv[1])
root = Path.cwd()
config = configparser.ConfigParser()
config.read(app / "Contents/Resources/platform.ini")
expected = json.loads((root / "surfer.json").read_text())["version"]["version"]
assert config["Build"]["Milestone"] == expected, "Packaged Firefox engine does not match source"
with zipfile.ZipFile(app / "Contents/Resources/browser/omni.ja") as archive:
    count = 0
    for line in (root / "src/zen/terminal/jar.inc.mn").read_text().splitlines():
        match = re.search(r"content/browser/(\S+)\s+\(../../zen/terminal/(.+)\)", line)
        if not match:
            continue
        entry = "chrome/browser/content/browser/" + match[1]
        expected_bytes = (root / "src/zen/terminal" / match[2]).read_bytes()
        assert archive.read(entry) == expected_bytes, f"Missing or stale terminal asset: {entry}"
        count += 1
    assert count >= 10, "Terminal asset manifest is incomplete"
print(f"Verified {count} shipped terminal assets and Firefox {expected}")
VERIFY

echo "DMG inspection passed:"
echo "- app: $EXPECTED_APP_NAME"
echo "- bundle id: $bundle_id"
echo "- executable: $bundle_executable"
echo "- updater: absent"
echo "- stock Zen update address: absent"
