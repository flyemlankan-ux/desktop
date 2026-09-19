# Firefox 156 settings fixture

Official files fetched with GitHub contents API from mozilla-firefox/firefox,
FIREFOX_156_0_RELEASE. receipt.json records both Git blob id and SHA256. Bytes were
checked against Git blob id immediately on fetch. The new Settings test verifies
both hashes before applying any production patch.

September19 strict applicability result against current terminal patches:
- ContainerEditor.mjs: PASS, fuzz0.
- ContainerCreationPanel.mjs: PASS, fuzz0.
- preferences/config/containers.mjs: FAIL first import hunk, 1 of3 hunks fails.
  Firefox156 inserts containerOptions import after SettingGroupManager; old patch
  expected a blank line. Preserve new import, retarget terminal imports deliberately.
  The later deletion-warning/session-cleanup hunks applied without fuzz in dryrun.
- preferences/dialogs/containers.js: PASS, fuzz0.
- installer/package-manifest.in: PASS, fuzz0.

No production patch was changed by fixture preparation. Old155 fixtures untouched.
New test test-terminal-settings156.mjs intentionally fails with all strict patch
blockers listed, rather than fuzzily applying or claiming behavior passed.

156-specific synthetic environment additions: Glean telemetry recorder,
ChromeUtils.defineLazyGetter, history/document URI, URL.fromURI, Preferences.addAll,
new containerOptions import placeholder. Creation-panel test supplies and asserts
entrypoint telemetry. Terminal behaviors are copied from current155 suite, including
starting-folder picker and validation. These156 behavior tests cannot run until
parent resolves the production import patch; additional runtime mocks may be needed.
Do not label this fixture receipt a real-app or Settings acceptance pass.

The new Firefox156 site-association UI is not accepted by these terminal-editor tests.
It needs separate safety tests proving terminal identities never appear as web
navigation choices. Do not erase that obligation by stubbing containerOptions.

Follow-up: parent retargeted only the shared import anchor, preserving156's new
containerOptions import and155 compatibility. Both155 and156 suites now apply all
five patches with fuzz0 and pass all12 behaviors. Site-association UI negative
proof and real156 app acceptance are still required.
