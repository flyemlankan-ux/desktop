# Firefox156 compatibility native test readiness

New script `scripts/terminal-tabs/test-terminal-compatibility156-macos.py`.
Syntax and --help pass; NOT executed by author. Parent controls app scheduling.

Run with existing test venv, `--app '.terminal-test/Zen Terminal Test 156.app'`
and `--label compatibility156` after exact source assets are freshly overlaid.

Planned native checks (real public methods, no extracted source functions):
- Exact Firefox156 process/profile/appdata isolation.
- Actual All Tabs ViewShowing builds real DOM; terminal omitted, web retained,
  selected website unchanged. Method/event-driven, not pointer-open menu proof.
- Actual loaded container-select module returns website-only options.
- Native workspace save with stale terminal default -> real BrowserOpenTab stays
  normal web identity0, creates no terminal record; original space restored.
- Actual packaged ShareClient.validateDocument rejects nested chrome, javascript,
  file and data URIs, accepts safe HTTPS with no tabs/workspaces/selection/session
  changes. No external network: only local resource schema lookup.
- Actual preferences subdialog renders website-only options. Test selects a web
  identity programmatically, changes setup kind while dialog open, then clicks the
  real accept button; expects visible error and no association creation.

Important scope: share manager import methods are private and invoked through
network-share navigation. The script explicitly records full share-import UI as
NOT RUN. Public validation does NOT prove UI importing. No fetched share links,
no mocked/extracted private methods, no remote upload, no paid commands.

Synthetic browser data only; no terminal shell intentionally opened. Cleanup quits
owned process. Result JSON includes failure and each completed check; original Zen,
real browser profiles and remote Chubs remain untouched.
