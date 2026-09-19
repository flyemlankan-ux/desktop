# Mixed-project native test readiness

New script: `scripts/terminal-tabs/test-terminal-project-workflows.py`
Status: syntax and `--help` pass; NO actual-app execution by this agent.
Parent is sole owner of headed-app scheduling.

Command (replace app with the freshly overlaid exact-source test app):

```
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 \
 scripts/terminal-tabs/test-terminal-project-workflows.py \
 --app '/path/to/Zen Terminal Test.app' --label project-review
```

Add `--pointer-drag` to attempt actual pointer reordering. This must be run separately
if an input limitation would stop later integration cases. No synthetic drag event
or direct folder-creation call is presented as pointer acceptance. The default report
explicitly records pointer drag/drop as `not_run`.

## Expected checks
- Exact launched process id, profile folder and app-data folder match synthetic run.
- Same newly saved setup creates two distinct terminal ids/PIDs and exactly two
  startup-recipe marker lines; later operations retain those PIDs and count.
- Real Zen folder contains website and two terminals after selection, collapse,
  expansion and native reorder.
- Real Zen new workspace plus `changeFolderToSpace` moves whole mixed folder intact.
- Real `splitTabs` creates web/terminal split; actual window resize changes terminal
  columns/rows; unsplit preserves shell and startup count.
- Real second browser window mirrors both terminal tab identities. Closing that
  window preserves original jobs. Closing one final tab deletes only its own job.
- Optional W3C pointer drag reorders a terminal before the web tab inside its folder;
  verified by resulting order/membership, not merely event dispatch success.

The methods were checked against this checkout: ZenSpaceManager.createAndSaveWorkspace,
ZenFolders.changeFolderToSpace, ZenViewSplitter.splitTabs/removeTabFromGroup,
ZenWindowSync.getItemFromWindow, plus native OpenBrowserWindow. Same-device mirroring
must actually be enabled; otherwise that case fails rather than silently duplicating
a tab and calling it mirroring.

## Scope and safety
Synthetic HOME, explicit app-data overrides, private test profile; restart/profile
selection environment stripped; original browser untouched. Temporary per-profile
tmux socket only; exact session targets for existence/deletion. `display-message`
uses native plain session-name target (not `=`, which is unsupported there).
Cleanup quits the owned application process, then kills only generated sessions.
Failure report is written even when an assertion fails. No full-desktop captures.

This is a new test harness requiring real execution/debugging, NOT an acceptance
receipt. It does not yet prove restart of mixed split/workspace layout, nested folder
reorder, keyboard accessibility, full drag-to-split, or paid/authenticated agent work.
Those remain separate obligations. Reasoning high; proof strong native scoped checks.
