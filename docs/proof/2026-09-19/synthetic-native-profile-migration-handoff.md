# Synthetic native profile migration — prepared, not run

New standalone script: `scripts/terminal-tabs/test-terminal-profile-migration-macos.py`.

This supplements the copy utility's unit tests. It does **not** read, copy, launch or verify the founder's actual profiles, original installed Zen or its existing process. No UI was launched while preparing this slice.

## Real journey the test will exercise

1. Require the explicitly copied `.terminal-test/Official Zen.app` with Firefox155.0.1, not the original installed app. Require the target fork's Firefox156.0 engine. Read-only checks against the copied source confirmed that version and its actual service/method names.
2. Allocate private temporary folders outside the repository, because the production copy utility correctly forbids browser data destinations inside a repository.
3. Launch the copied official source binary twice, creating two separate synthetic profiles. Every launch has explicit HOME, MOZ_APP_DATA, MOZ_LOCAL_APP_DATA and profile arguments. Verify the actual process ID, profile directory and app-data directory before interacting.
4. Use the source browser's actual services to save a bookmark, a separate historical visit, a real encrypted dummy login, a container, a workspace and a marker preference. A loopback-only HTTP page sets a real persistent cookie in that container and becomes the saved browser tab.
5. Flush tab state, quit the exact owned source process cleanly, and require zero exit status. Check that key4.db and logins.json exist, the login has encrypted fields and the known dummy password is not plaintext in logins.json.
6. Register both synthetic profiles in the synthetic source profiles.ini. Snapshot source file hashes. Run the actual production copy function forward from155.0.1 to156.0 into a new separate root; retain destination protections, engine checks, locks, real open-file checks, source consistency verification and hashing.
7. Open each copied profile explicitly with the fork. Verify the original bookmark, distinct history-only record, decrypted dummy username/password, real cookie/container, workspace identifier/name, marker preference and restored tab. Check terminal integration is present.
8. Close each fork launch cleanly and require all source file hashes to remain unchanged after copy and after both target launches.

The test uses a separate history-only URL which no restored tab opens. The local server stops setting cookies before target launches. These choices prevent a fresh page load from silently recreating missing history/cookie data and producing a false migration pass.

## Necessary synthetic-only guard exception

As in the existing profile-selection test, the utility's broad “any process named Zen is running” check is filtered only within this new synthetic test. Otherwise the founder's unrelated original Zen would prevent testing even though these new source profiles are closed.

The exception is restricted to this exact synthetic source root, after the test-owned process has stopped. The actual source-directory lsof check, profile locks and every other production copy guard still execute. No original browser is closed, inspected or manipulated. The production copy utility is unchanged and retains its broad guard for real migration.

## Parent run, exclusive UI only

```sh
/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 -B \
  scripts/terminal-tabs/test-terminal-profile-migration-macos.py \
  --source-app '.terminal-test/Official Zen.app' \
  --target-app '.terminal-test/Zen Terminal Test 156.app' \
  --label synthetic-migration155-to156-1
```

Use a new label; prior evidence is never overwritten. All generated passwords, cookies and web content are synthetic. The report records pass/fail booleans and synthetic paths, not decrypted password values. Synthetic working data is retained under the private temporary root for diagnosis, not copied into the repository.

## What this does not prove

- Actual personal account sessions or logins migrating successfully.
- Website server-side session validity or OS/keychain-bound credentials.
- Extensions, third-party add-ons, client certificates or a user-set primary password.
- Automatic final-installed-app profile selection. The second profile is explicitly selected with `-profile`; the existing separate install-selection test covers ordinary selection behavior.
- A production signed/notarized app. An overlay run is preliminary; final acceptance should repeat on the genuinely compiled separate fork.

## Current proof and recap

Python syntax and `--help` pass. Read-only source checks confirmed `addLoginAsync`, `searchLoginsAsync`, `History.hasVisits`, `createAndSaveWorkspace` and the ContextualIdentityService import used by the copied official155 app. No source or target browser was launched for this slice.

1. We have an end-to-end synthetic migration test ready to run.
2. It adds real source-browser encryption, cookies, saved tabs and two-profile verification rather than fabricated database fixtures alone.
3. Overall goal remains a separate terminal-enabled Zen that can safely receive a personal copy later.
4. No personal migration was performed or claimed.
5. Prepared-script checks passed; actual native migration proof is pending.
6. Next: parent runs this in its exclusive UI slot, then repeats on the final compiled app.
7. Drift check: synthetic proof must never be reported as the founder's real logins having moved.

Recommended handoff: high reasoning for failures involving storage, encryption or source integrity. Proof level: two actual closed source profiles, production copy utility and actual fork decryption/persistence, with original source hashes unchanged.
