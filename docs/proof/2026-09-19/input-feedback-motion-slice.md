# Input feedback and reduced-motion slice

Source changes after cloud build34375b2; that build does NOT include this slice.
Changed Page, page CSS and focused polish test. No app or personal data touched.

1. Current state: source-tested small behavior fixes, native final-package proof pending.
2. Changed: rejected oversized/busy input remains nonfatal, visibly warns without
   dropping real ready state. A later successfully delivered USER input restores the
   exact previous saved/reconnected/not-saved status. Old queued writes or resize
   frames cannot erase a newer warning. Rejected text is never retried or truncated.
   Reduced-motion sets xterm blinkfalse and smooth-scroll0, follows changes, removes
   media listener at stop; ordinary preferences retain former behavior.
3. Overall product: real Zen with dependable terminal tabs; no new dashboard/UI manager.
4. Not built: terminal search, full clipboard/IME proof, final visual or screenreader
   acceptance, final rebuilt installer. No change to recipe/session ownership.
5. Proof: real function execution checks whole rejection, ready preserved, successful
   input recovery, earlier queued write race, resize not clearing warning, fallback
   not-saved status preserved. Actual init/change/stop functions tested for both media
   settings with listener cleanup. Existing Unicode/repeated keys/resize/helper tests,
   native polish checks,25 entrypoint cases and wiring remain passing.
6. Next: parent overlays exact new bytes, runs focused native warning/motion checks,
   then rebuilds final source package. Reasoning high, proof focused real functions
   plus native Firefox input/status/media behavior; no unrelated Core regressions.
7. Drift check: small correctness fixes, not terminal redesign. No functionality
   quietly declared deferred. Earlier cloud success cannot claim these changes.

## Minimal terminal-search implementation option (NOT built)

Canonical plan includes scrollback search; original explicit deferrals do not list it.
Recommend a small in-terminal find bar revealed only on deliberate Find action,
not a permanent toolbar or new manager. Use a compatible pinned upstream xterm
search addon rather than inventing text matching against visible DOM; vendor exact
bytes, record source/hash/version and include its license before shipping.

- Reuse ordinary Cmd+F intent when a terminal is selected; normal web tabs retain
  browser Find. Handle this at Zen's real Find command boundary, not just a content
  key listener that browser shortcuts may beat. Do not swallow shell Ctrl+F.
- Bar: labelled query, Previous, Next, result/no-match feedback, close. Enter/Shift+Enter
  navigate; Escape closes and returns terminal focus. Search must not send query text
  to the shell. Match scrollback already held by that terminal, not other tabs/jobs.
- Keep initial scope literal case-insensitive text with next/previous and optional
  match-case if the native find style offers it; no regex complexity by default.
- Search scrollback navigation must not replay output, change PID or rerun recipes.
  Clearing query restores normal cursor/input behavior. Resize/alternate-screen
  changes require predictable selection handling; test rather than assume.
- Proof: match outside visible rows, repeated matches, Unicode, no match, query edit,
  empty query, Escape/refocus, keyboard-only access, actual Cmd+F versus web Cmd+F,
  split view selected pane, bounded behavior at10000 lines. Search never reads shell
  history files or filesystem. No external service or upload.

Builder choice requires parent to adopt this explicit minimal scope before changes.
This note is an implementation option, not completion or a new founder answer.
