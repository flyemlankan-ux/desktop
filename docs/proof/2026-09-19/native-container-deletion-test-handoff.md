# Native service-deletion test handoff

New script: `scripts/terminal-tabs/test-terminal-container-deletion-macos.py`.
Syntax and `--help` checked; **no UI launched and no native passes claimed**.

Parent command:

```
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 -B \
  scripts/terminal-tabs/test-terminal-container-deletion-macos.py \
  --app '/path/to/156/Zen Terminal.app' --label service-deletion-156
```

Default expected engine is exactly156.0. Override `--expected-engine` only if the actual intended build version changes. A wrong engine or wrong app executable is rejected before launch.

## Designed actual-app checks

- Fresh test-owned HOME/profile/app-data and process identity assertions; no inherited profile overrides.
- Real native ContextualIdentityService creates two setups. Normal terminal opener creates two matching jobs and one neighboring job.
- One matching tab is background/unselected. Native discard is attempted only through Firefox's own method. Source inspection shows Firefox rejects unloading non-remote privileged pages, so the result records `page_unloaded:false` rather than pretending an unload occurred; it still requires a real unselected terminal tab.
- Second actual browser window obtains the same shared profile cleanup observer as the first. Compare the exact observer object rather than counting unrelated Firefox listeners.
- Remove setup through native ContextualIdentityService in the second window. Matching recipes/records disappear and real tmux jobs stop; neighboring setup/job survives. Repeated removal is harmless.
- First window's deleted terminal shows honest closed-state feedback; screenshot saved for inspection.
- Actual manager creation/settings callback is paused using a test-owned Promise (no production monkeypatch). Native identity removal occurs while paused; after release final guard refuses and a startup sentinel file is absent.
- Synthetic `.zprofile` temporarily hides tmux from the browser's login-shell lookup. A real direct shell records its own PID. Native service deletion must terminate that PID via page notification; neighboring tmux job remains. Restoring PATH and retrying resolves the pending record.

Cleanup quits/terminates only the process launched by this script and removes only the tmux server tied to the fresh temporary profile. The script does not kill the recorded direct PID itself; its disappearance must be caused by production deletion cleanup. Debug profile/logs remain under ignored `.terminal-test`.

## Limits

No actual extension install/removal path is exercised; it invokes the same native service directly. A non-remote tab is not forcibly unloaded. No Mac sleep/crash/public-release claims. JSON evidence is produced on success/failure; screenshots still require visual inspection. No production files changed in this follow-up.
