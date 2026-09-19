# Zen 1.22.2b / Firefox 156.0 upgrade assessment

Read-only audit. No checkout, source changes, new worktree, or full-plan restoration.
Target pinned Zen commit: `04e7db5d3a84ec754c14d6fc6930fa3ccd00c836`.
Old upstream: `4f3bcb2f3254c33a14ef7f16f6a125f27709b76d` (1.22b/155.0.1).
Parent reports clean merge-tree against old HEAD; that is not working-tree merge or
behavioral compatibility proof. Upstream delta: 210 files, including session restore,
window mirroring, folders, workspaces, splits, URL handling and sharing.

## Recommended integration order
1. Preserve current uncommitted slice changes and test receipts without restoring
   the removed local full-product plan. Merge pinned upstream into the active tree
   only after parent checks all owners have stopped edits. No checkout of an old
   tree that recreates the removed plan.
2. Keep incoming Rust 1.95.0 (old 1.94.1), Firefox156 surrogate config and native
   changes. Keep terminal app identity/profile default/updater disable/helper build.
   Do not transplant whole old Zen manager modules onto a new official app.
3. Obtain clean official1.22.2b Mac app and verify its version/engine. Build a NEW
   disposable overlay destination. Current preparer only copies source app when
   destination absent: reusing old destination could silently combine Firefox155
   executables with Firefox156 resources. Refuse mismatched existing output or use
   a versioned fresh output path, never simply relax the source version assertion.
4. Fetch version156 fixtures with independent blob and SHA256 receipts; apply patches
   with fuzz=0 and compare baseline-patched files with actual official app bytes.
5. Pass focused Settings/entrypoint/security/build tests, then headed native tests.
   Full fresh compile/package and installed-app tests still required for delivery.

## Confirmed compatibility changes
- ZenPinnedTabManager TabStateCache path moves from resource:///modules/sessionstore
  to `moz-src:///browser/components/sessionstore/TabStateCache.sys.mjs`.
- Upstream pinned unload now blurs selected tab first; fixes `contains` to `includes`.
  Preserve these changes when adding terminal-only pin-decoration suppression.
- Split background restore calls `gBrowser.insertBrowser`, not `_insertBrowser`.
- New native site-container association UI in Firefox156 creates more choices that
  must exclude terminal identities from ordinary website navigation.
- New share-space/folder/split feature adds a trusted browser-tab import boundary;
  security details below. This cannot be ignored because text merge is clean.
- configs/common/mozconfig now honors ZEN_DISABLE_BOOTSTRAP and explicitly disables
  LTO when requested; otherwise cross,thin. Preserve upstream build behavior.

## Fixture evidence actually fetched (in memory, GitHub contents API)
Repository `mozilla-firefox/firefox`, tag `FIREFOX_156_0_RELEASE`:

| Source | Git blob | SHA256 | Change |
|---|---|---|---|
| browser/components/contextualidentity/content/ContainerEditor.mjs | 7d789c2a1d9b12e875ed0fa638036dd85d8827b4 | a8a57d0536c7e6f7cde110aed12c0bfcc5576ea3cb362b4a4c6d84e9c62d8f4b | identical155 |
| browser/components/contextualidentity/content/ContainerCreationPanel.mjs | 9868c288653b83717afb0403901c8adc0058bd4d | 5a2921ad459cefc8326c1a215f482e06abe6a52c9cd28046a0775c52df909f55 | open(sourceWin,entrypoint) + telemetry |
| browser/components/preferences/config/containers.mjs | ecd46c8cd4763c859476012c6a02c0e60a0c0e07 | 716ba2b28c1bdf7f5ac3e360d4c16f16b221d013420e1ad32c89b53ac38dea17 | site associations, history/doc events, telemetry, new import |
| browser/components/preferences/dialogs/containers.js | 52d38c8bddb53ff113013357f714d43381184502 | bf30b1e5c715f938e9dbe9dc6c967caf2175036e837cda734e4f8c6049071879 | identical155 |
| browser/installer/package-manifest.in | 46725ca0498537098daebed34a5e503306e44882 | ba18ff3089ba57bee4fb61602e38873fb56ca53e4b176bafee8f743c432da4b5 | changed |

Do NOT relabel old receipt files as156. Fetch new exact files. Container settings
synthetic mocks need the new import, history/document event sources and telemetry,
or split tests so actual source coverage remains honest.

Refresh five packaging fixture files plus TWO embedded snippets currently outside
receipt coverage: browser/moz.build inherited DIST_SUBDIR and
python/mozbuild/mozbuild/frontend/context.py FinalTargetValue. Refresh mozpack
receipt against the156 tree for local recovery packager and package-manifest policy.
Check all fetched bytes against Git blob SHA1 and SHA256 as existing fetcher does.

## Exact version-bound tools needing review
- `.github/workflows/terminal-macos-dev-build.yml`: generated display version,
  upstream_stable receipt, Settings test filename; Rust reads incoming file already.
- `prepare-local-test-app.py`: source assertion, source fixture directory, both git
  baseline references, message/docs, importantly fresh destination executable rule.
- `test-terminal-settings155.mjs`: new fixture directory, tag/labels/mocks; rename to
  version-independent name or156 and update all callers.
- `test-terminal-build-packaging.py`: fixture directory/ref and embedded snippets.
- `fetch-terminal-mozpack.py`: receipt path.
- `recover-terminal-macos.py`: manifest fixture, mozpack receipt/ref, version labels,
  expected engine default, mozpack-root directory.
- `test-recover-terminal-macos.py`: ref and test tooling directory.
- `test-terminal-macos-app.py`: engine assertion should read surfer.json, not broad
  string search for155.0.1.
- `test-terminal-profile-selection.py`: expected engine default.
- `test-verify-terminal-app-assets.py`: synthetic platform fixture version should
  derive expected config to keep negative controls useful.
- `verify-terminal-app-assets.py` already derives engine from surfer; preserve strict
  native manager bytes and extend for any newly changed sharing modules.
- `inspect-terminal-macos-dmg.sh`: inherits verifier version; inspect rest of script
  for labels but do not weaken signature, identity, no-personal-data checks.
- `test-copy-zen-profiles.py`: comment references155 INI parser; validate156 parser
  behavior before treating old behavioral receipt as current. Migration caller must
  pass actual current source engine and156 target; never force downgrade.

Historical proof stays labelled155; do not mass-replace old evidence version strings.

## Mandatory sharing safety review and patch targets
Source finding, NOT demonstrated exploit:
- `src/zen/share/ZenShareManager.mjs` #serializeTab already accepts HTTP(S) only.
  Normal terminal chrome URLs currently excluded. Add explicit terminal marker/id
  rejection before URL/title/icon serialization, including unloaded/restored tabs.
- Same file #importTab calls `gBrowser.addTrustedTab(item.url)` without a local URL
  allowlist. Add HTTP(S)-only rejection before any trusted tab creation. Check nested
  folder and split import paths all funnel through this guard; reject whole malformed
  document before creating partial state when practical.
- `src/zen/share/share.schema.json` currently says only `format: uri` for tab.url.
  Add HTTP(S) restriction, alongside strict actual parsed-URI validation in
  `ZenShareClient.sys.mjs` validateDocument. Scheme checks must not rely solely on
  server validation or editor preview.
- #serializeFolder and shareSpace include native folder/workspace names. User-requested
  folder labels can remain part of intentional share, but never introduce terminal
  recipe fields, starting folders, terminal labels, sessions, or setup metadata.
- Terminal-only groups should not create misleading empty uploads. Mixed splits with
  one surviving website require clear handling; preserve appropriate website export.
- Test controlled synthetic payloads only: chrome terminal URI with session id,
  javascript/file/data URI, nested folder/split hidden payload, unloaded terminal,
  terminal-marked tab with stale HTTP URI. Assert no shell starts, no setup data or
  session id exported, safe HTTPS website still works. Stub network or use local
  payload validation; never post user data to upstream sharing service.

Proof level: high reasoning, focused strict-source and negative security tests plus
actual fresh packaged Mac workflows. No claim upgrade is complete or safe yet.
