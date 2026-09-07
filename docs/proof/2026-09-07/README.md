# Evidence labels

- `local-integration-*`: historical real Mac checks on the older disposable152.0.3 test app; not proof of the155 installer. `local-integration-failure.png` is a retained debugging screenshot, not a successful acceptance result.
- `terminal-page-*`: current rendered terminal page exercised in Chromium with a test-only browser-services bridge and real native helper/tmux. Not native Zen menus or packaging proof.
- `stable-overlay-*`: current stable155.0.1 disposable app with terminal source overlaid, when its results JSON records success. This tests real native UI but not the freshly compiled installer.
- `packaged-*`: reserved for actual final installer checks. No final acceptance without these results.

Only synthetic profiles and commands are used. No personal credentials are included.
