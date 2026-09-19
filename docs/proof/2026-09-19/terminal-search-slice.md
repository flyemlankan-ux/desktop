# Terminal scrollback search — source slice

## Where we are now
The terminal page now has a deliberately small search bar. This is source-level completion, not yet native keyboard acceptance or a newly built distributable.

## What changed
- Cmd+F / Ctrl+F inside the terminal page opens the hidden search bar and selects its query.
- Literal, case-insensitive incremental search reads the current viewer's 10,000-line scrollback. Enter/Shift+Enter move next/previous. Arrow buttons provide the same actions. Escape closes and restores terminal focus.
- A polite accessible status reports Match found / No matches; an empty query clears selection/status. No regular-expression controls, all-match decoration pass, misleading match counts, persisted query, or shell command forwarding.
- Search keys are captured before xterm. Search input is outside xterm's textarea. Composition Enter is not swallowed. Narrow layouts keep controls within the terminal surface and put results below the input.
- Search addon listeners are disposed on viewer shutdown without terminating the saved shell session.

## Overall project
Normal Zen browsing and native organization, with real terminal tabs and saved terminal setups.

## Not built by this slice
A new distributable; native Firefox accelerator routing proof; full OS input-method qualification; searching output that already fell outside bounded scrollback; regex search; global browser search across terminals.

## Evidence
`node scripts/terminal-tabs/test-terminal-search.mjs`: PASS — exact vendor bytes, pinned released commit, literal incremental options, next/previous, shortcut capture, composing Enter, blank/no-match, focus return, unchanged scrollback bound.
`node scripts/terminal-tabs/test-terminal-polish.mjs`: PASS — existing input queue, warning/recovery and reduced-motion lifecycle.
`node scripts/terminal-tabs/test-terminal-native-polish.mjs`: PASS — source checks, not native rendered proof.
`node scripts/terminal-tabs/check-terminal-tabs.mjs`: PASS — syntax and wiring.
`git diff --check`: PASS.
Added rendered bridge case to `test-terminal-browser.mjs`, intentionally NOT run by this worker because parent owns UI. It checks actual addon selection and confirms Enter on a command-shaped search query creates no shell file, followed by real shell input after Escape. Parent must also test actual Firefox Cmd+F because chrome accelerators can precede page listeners.

## Dependency receipt
Official `@xterm/addon-search` 0.16.0 from the npm registry. Tarball SHA512 checked before extracting. Published gitHead `f447274f430fd22513f6adbf9862d19524471c04` matches xterm 6.0.0 / fit 0.11.0 already shipped. Exact JavaScript and package MIT license are unmodified. Per-file SHA256, package URL and tarball integrity are in `src/zen/terminal/vendor/addon-search-receipt.json`. No npm installation/update occurred. The addon license differs from the existing xterm license, so its own exact license is separately shipped.
Two new jar entries: `content/browser/zen-terminal/vendor/addon-search.js`, `content/browser/zen-terminal/vendor/LICENSE.addon-search.txt`. Receipt is source-only.

## Next slice and drift check
Parent runs rendered bridge and native keyboard checks, then rebuilds the final source package. Recommended reasoning: high for keyboard interception/focus issues; proof: focused source tests plus real rendered/native key dispatch, not unrelated broad redesign. This stays within the requested terminal experience; no new account, process, session, or browser navigation policy.
