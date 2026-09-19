# Delivery, update and personal-copy acceptance audit

## Scope

Read the Mac package planner, recovered-app packer, development DMG signer,
image inspector, shipped-resource verifier, profile-copy tool and their tests.
Only synthetic test fixtures were used. No personal profiles were read/copied,
no app was launched, no `/Applications` writes occurred, and no release was
published. The tiny signing test compiled a synthetic executable and mounted
only its own temporary disk images.

## Confirmed gap fixed: privacy scan covered too little

The old image inspector searched four profile filenames only inside the app.
A mistakenly included sibling `Profiles/.../logins.json` was outside its search;
history or session data alone also escaped that list. The new
`check-terminal-package-privacy.py` examines the whole mounted image for strong
profile-data names, including database sidecars and known workspace/session files.
It also inspects member names in `.ja`, `.zip` and `.xpi` archives without opening
member contents. Legitimate browser default `prefs.js` resources remain allowed.

The scanner never follows directory/file symlinks. Root `Applications` pointing
to `/Applications` is the sole allowed external shortcut; other external links
fail closed. Internal framework links are allowed but not traversed. Special
files, unreadable directories and malformed resource archives stop inspection.
Console output reports only a count or error category, not private names/content.

This is a recognizable-artifact check, not proof that arbitrary renamed files
contain no secrets. It must run against the actual final distributable. Its
11 synthetic cases are not final-installer acceptance.

## Results

| Check | Result |
| --- | --- |
| Synthetic profile-copy safety | 26 passed |
| Package command planning | 3 passed |
| Native helper packaging fixtures | 4 passed |
| Shipped asset verifier fixtures | 10 passed |
| Build declarations | 4 passed |
| Whole-image privacy scanner | 11 passed |
| Tiny real development DMG/signature/no-overwrite test | passed |
| Recovered packaging suite | 8 passed; 1 dependency error |
| Shell syntax and whitespace | passed |

The recovered packer's real pinned-mozpack test fails to import `packaging` in
both available test Python environments. No dependency was silently installed,
no test was skipped, and this is not counted as a packaging pass. Its recovery
loader also intentionally pins Firefox 155.0.1; it is a historical recovery tool,
not unqualified proof for the current Firefox 156 distribution.

## Remaining acceptance decisions and untested paths

1. **Final 156 artifact:** the compiled release must pass actual image inspection,
   source-equality checks, clean-profile launch and the native user journeys.
   Passing tests against fixtures or a local overlay does not establish this.
2. **Upgrade and rollback:** no complete automated install/upgrade/rollback tool
   exists in this reviewed slice. Current instructions retain the untouched
   original app/profile as a manual fallback. That does not prove restoring an
   upgraded terminal profile. Never open upgraded data with an older engine;
   rollback must use an independently retained compatible copy.
3. **Personal selection:** the copy tool correctly requires a new destination,
   explicit source/target engine assertions, closed source files and profile
   locks; it preserves database bytes and rewrites only profile registration.
   Automatic selection additionally needs the final installed app's measured
   install hash. No current personal-copy or final-path selection was performed.
4. **Version assertions:** source-engine age is an operator-supplied assertion
   because Zen's application version is not Firefox's engine version. A passing
   synthetic comparison does not establish the newest engine that actually
   touched the person's profiles. Resolve that before copying, never bypass
   Firefox's own compatibility protection.
5. **Updates and signature:** stock updater removal avoids replacing this fork
   with ordinary Zen. It is not a maintained security-update service. An ad-hoc
   development seal is not Apple notarization or a publisher identity guarantee.
6. **Local race boundary:** copy checks reject symlink paths, source changes,
   racing destination publication and active locks. They are not claimed as a
   security boundary against a malicious same-account process replacing ancestor
   directories while the operator runs the tool. Close competing writers; do not
   weaken the fail-closed checks to force a copy through.

## Next handoff

Run the new scanner test in CI, then run the inspector on the final 156 image.
Use high reasoning for real deployment/rollback decisions and native end-to-end
proof for profile selection and upgrade recovery. The user-facing goal remains
ordinary Zen with working terminal tabs and a separate safe copy of existing
browser data—not merely a well-tested terminal module.
