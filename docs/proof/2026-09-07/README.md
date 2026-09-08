# Evidence labels

Current final app: `/Applications/Zen Terminal.app`, compiled from19f7539 on Firefox155.0.1.

- `packaged-*`: actual recovered, genuinely resource-packed development DMG and installed app. `packaged-macos-results.json` records26 passing native checks on the final installed path. `packaged-failure.png` is historical debug evidence, NOT a successful result.
- `installed-app.json`: installation directly from the inspected DMG, file-by-file equality and strict signature.
- `installed-profile-selection.json`: actual final-path ordinary launch with synthetic copied profiles; all three profiles retained and correct default selected without profile-selection launch flags.
- `recovered-package-provenance.json`: exact cloud archive/source, real Firefox packaging-tool hashes, transformations, original input checks, signatures and development limitations.
- `recovered-packaging-source-audit.md`: independent upstream-source review of startup failure and the real packing fix.
- `recovery-first-launch-failure.json`, `recovery-v2-dialog-first-failure.*`: retained failed attempts. First raw build lacked actual resource packing; second test clicked before native dialog readiness. Neither is a passing acceptance claim.
- `terminal-page-*`: current rendered production terminal page exercised in Chromium with a test-only browser-services bridge and real helper/tmux. Ten checks; not native Zen menu or installation proof.
- `stable-overlay-*`: earlier stable155.0.1 disposable app with terminal files overlaid. Not freshly compiled installer evidence.
- `local-integration-*`: historical older152.0.3 test-app checks, not155 acceptance.

All screenshots, browser profiles and test commands are synthetic. No personal credentials are included. Personal profile copying has NOT happened: original Zen remains open. This is a private development distribution, not Apple notarization or public-release certification. Stock automatic updates are disabled; future browser security updates need a tested rebuild.
