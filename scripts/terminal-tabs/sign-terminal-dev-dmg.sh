#!/usr/bin/env bash
# MPL-2.0. Local development signature only: this is NOT Apple notarization.
set -euo pipefail
[[ $# == 2 ]] || { echo "Usage: $0 input.dmg output.dmg" >&2; exit 64; }
input="$1"
output="$2"
[[ -f "$input" && ! -e "$output" ]] || { echo 'Input must exist and output must be new.' >&2; exit 1; }
work="$(mktemp -d "${TMPDIR:-/tmp}/zen-terminal-sign.XXXXXX")"
mounted=false
cleanup() {
  if [[ "$mounted" == true ]]; then
    hdiutil detach "$work/mount" >/dev/null 2>&1 || hdiutil detach -force "$work/mount" >/dev/null 2>&1 || true
  fi
  rm -rf "$work"
}
trap cleanup EXIT
mkdir "$work/mount" "$work/image"
hdiutil attach -readonly -nobrowse -mountpoint "$work/mount" "$input" >/dev/null
mounted=true
app="$work/image/Zen Terminal.app"
[[ -d "$work/mount/Zen Terminal.app" ]] || { echo 'Expected separate Zen Terminal app.' >&2; exit 1; }
ditto "$work/mount/Zen Terminal.app" "$app"
hdiutil detach "$work/mount" >/dev/null
mounted=false
[[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$app/Contents/Info.plist")" == app.zen-browser.zen-terminal ]] || exit 1
# Preserve the browser's existing capabilities. Never alter system security settings.
codesign --force --deep --sign - --preserve-metadata=entitlements "$app"
codesign --verify --deep --strict "$app"
ln -s /Applications "$work/image/Applications"
hdiutil create -quiet -format UDZO -volname 'Zen Terminal' -srcfolder "$work/image" "$output"
echo 'Created a fully sealed development DMG (not notarized).'
