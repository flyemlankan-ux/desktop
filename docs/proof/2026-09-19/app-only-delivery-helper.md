# App-only install, upgrade, rollback and removal

## Decision and scope

This is a **builder implementation decision** under the user's existing full
autonomy, not a newly invented user answer. Existing delivery instructions
provided a manual fallback but no tested app replacement/removal helper.

`manage-terminal-app.py` now offers explicit `install`, `upgrade`, `rollback`
and `remove` actions. The default is a read-only dry run. `--apply` is required
for changes. It never launches an app, reads a browser profile, changes a profile
selection, deletes profile data, disables downgrade protection or contacts an
update server. Removal means moving the app into the explicitly named backup,
not deleting it. Original Zen's identity and destination name are refused.

## Checks and transaction

- Require explicit expected app version, engine and verification checkout.
- Verify separate fork bundle/executable/profile identity, complete strict code
  signature, current source asset equality and absence of recognizable private
  data. A rollback needs the checkout matching that older app; current-source
  verification is never relaxed to allow arbitrary old resources.
- Refuse symbolic links, special files, existing backup, overlapping paths,
  running fork processes, open app files and upgrade engine downgrades.
- Hold a cross-process advisory file lock in the destination directory. Recheck
  the installed identity and path state after taking the lock.
- Stage on the destination filesystem; compare bytes and modes against source;
  verify the staged app again. Recheck app activity and existing app contents.
- Move the previous app to a new sibling backup using atomic no-overwrite rename,
  then publish the verified replacement the same way. On publication failure,
  restore the previous app. If an unrelated destination appeared, never overwrite
  it: keep the old app in backup and report that location.

Each individual rename is atomic; the two-renames sequence is **not** a
power-loss-proof atomic swap. A hard crash between them can leave the destination
absent while the retained backup remains intact. The helper never removes that
backup. Recovery requires an explicit, compatible app-only installation; it must
not auto-launch a downgraded app against upgraded profiles.

## Safe usage shape

Use an accepted source checkout and a source app whose exact version/engine are
known. Replace every placeholder. First omit `--apply`:

```sh
python3 scripts/terminal-tabs/manage-terminal-app.py upgrade \
  --source '/path/to/accepted/Zen Terminal.app' \
  --destination '/path/to/install/Zen Terminal.app' \
  --backup '/path/to/install/Zen Terminal.previous.app' \
  --verification-root '/path/to/exact/source-checkout' \
  --expected-version '<App.Version>' --expected-engine '<Firefox milestone>'
```

Rollback additionally requires `--acknowledge-profile-risk`. That acknowledges
the warning; it does not make an upgraded profile compatible. Retain a separately
compatible profile copy before any real upgrade. App removal leaves all browser
profile data and terminal work records untouched; the helper is not a session
stopper or private-data eraser.

## Proof

`test-manage-terminal-app.py`: **17 synthetic filesystem checks passed**:
read-only default; install; previous-app retention; app-only removal; rollback
acknowledgement; downgrade refusal; original-Zen refusal; links/overlap/existing
backup; active-app refusal; staged verification failure; publication failure and
restoration; racing destination/backup preservation; concurrent-process lock;
source mutation; strict signature/asset verifier failure.

The transaction fixtures inject synthetic verification/activity functions. They
prove file operations, not actual signed app acceptance. Separate tests call the
production verifier and prove signature and missing-asset failures are not
ignored. No `/Applications` change, browser launch or personal-data operation was
performed. Final signed-artifact verification plus a synthetic native upgrade and
rollback journey remain required before personal deployment.

Recommended handoff: high reasoning, strong destructive-path checks, then native
end-to-end proof against accepted distributables. No broader package or profile
claims follow merely from these filesystem tests.
