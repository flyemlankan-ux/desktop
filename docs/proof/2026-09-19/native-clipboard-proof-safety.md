# Clipboard proof: fail closed on the personal login session

## Decision

Do not read or replace the current system clipboard. No real clipboard access, clipboard metadata access, mutation, native paste or UI launch happened in this slice.

An honest all-format snapshot cannot be guaranteed through the inspected public macOS interface. A general-pasteboard helper therefore deliberately refuses before requesting the system pasteboard. Native Cmd+V proof is deferred to a dedicated disposable macOS login session, not merely a new browser profile.

## Why the simple backup/restore approach is insufficient

Apple's installed macOS 14.4 SDK `ApplicationServices/.../HIServices.framework/.../Pasteboard.h` documents:

- `kPasteboardFlavorPromised`: reading the bytes asks the sending application to fulfill a promise. A naïve `dataForType` snapshot may invoke another application's provider instead of passively copying existing bytes.
- `kPasteboardFlavorNotSaved`: volatile data should not be saved.
- `kPasteboardFlavorRequestOnly`: these representations are intentionally omitted from `PasteboardCopyItemFlavors`. Enumerating visible types does not prove that every original format has been captured.
- Sender-only and translated representations also carry semantics that a plain byte rewrite would not faithfully preserve.

The public flags query can reject known unsafe representations before reading their data, but it cannot reveal every intentionally hidden representation. AppKit's `changeCount` lets us detect a later writer, but checking the count and replacing the clipboard are separate operations. There is no inspected public compare-and-swap operation that makes conditional restore indivisible. A writer can act between the check and the write.

Primary documentation:
- [Apple NSPasteboardItemDataProvider](https://developer.apple.com/documentation/appkit/nspasteboarditemdataprovider)
- [Apple PasteboardGetItemFlavorFlags](https://developer.apple.com/documentation/applicationservices/1459353-pasteboardgetitemflavorflags)
- [Apple NSPasteboard](https://developer.apple.com/documentation/appkit/nspasteboard)

## Implemented bounded helper

`clipboard-proof-transaction.py` contains a transaction policy for a genuinely known, disposable, exclusively owned fixture, not a live system-clipboard adapter.

- Rejects personal/nonexclusive boards and incomplete format inventories before data reads.
- Preflights every fixture representation before reading any bytes; refuses all nonzero representation flags.
- Keeps bytes only in memory; never logs, serializes or persists them.
- Bounds snapshot size to 8 MiB and inventory to 256 representations.
- Refuses changes during snapshot or before installing the harmless test text.
- Restores only when the change count is still the test's own count; otherwise preserves the observed later writer.
- Releases snapshot references afterwards. This is not a claim of guaranteed secret-memory erasure.
- `system_clipboard_adapter()` always raises without accessing the operating system.

The non-atomic check/write limitation remains explicit. The fixture's exclusive ownership is a prerequisite, not something this helper can force on macOS.

## Synthetic checks completed

`python3 -B scripts/terminal-tabs/test-clipboard-proof-transaction.py`: **12 tests passed**.

They cover exact multi-item/multi-format binary preservation, later-writer preservation, unsafe flags rejected before reads, capture/install races, bounded memory, unavailable data, personal-board refusal, incomplete-inventory refusal, empty fixture, repeated cleanup, and unconditional system-adapter refusal. These tests use Python memory only. They do not prove macOS clipboard behavior.

## Exact future native proof scope

Requires a disposable macOS user/login session with no personal apps, clipboard history, cloud clipboard or competing clipboard writers. Do not change the founder's login settings to manufacture this condition.

1. Launch the correctly compiled separate browser with synthetic HOME, profile and app-data, and verify the actual PID and directories.
2. Create a genuine terminal setup and shell. All jobs, files and tmux sessions belong to the test profile.
3. Inside that shell, run a small test-owned raw-input receiver that enables bracketed paste, records only the known synthetic input, restores terminal modes in a finally block, and exits after the closing bracketed-paste sequence.
4. Seed only that disposable session's clipboard with harmless quoted multiline text such as `printf '%s\\n' 'first line'` followed by `printf '%s\\n' 'snow 雪'`. No secrets or user clipboard bytes are needed.
5. Focus the owned terminal textarea, verify the foreground PID, and send real native Command+V restricted to that test PID. Do not call xterm's paste method or dispatch a fabricated clipboard event.
6. Verify the receiver gets exact UTF-8 text surrounded by `ESC[200~` / `ESC[201~`, including the embedded newline. The raw receiver does not execute pasted text.
7. Separately return to the ordinary shell and check bracketed multiline paste waits for an explicit Return before harmless output appears. Never use destructive payloads to demonstrate safety.
8. Restore the known disposable fixture only if its own change count is unchanged. If another writer appeared, preserve it and report an interrupted proof, not a pass.
9. Remove only the test jobs/files and quit only the owned app.

This is a readiness specification, not an implemented or passed native clipboard journey. A new browser profile alone is insufficient isolation because the macOS clipboard is shared across applications in the login session.

## Slice recap

1. We identified why the apparently simple clipboard test could disturb personal data.
2. Added fail-closed policy and 12 in-memory safety tests.
3. Overall goal remains dependable normal Zen behavior plus terminal tabs.
4. Did not access the clipboard, implement a misleading all-format macOS adapter, or claim native paste passed.
5. Proof checked the policy and exact synthetic restoration behavior only.
6. Next: native paste proof in a disposable macOS login session; meanwhile the accessibility-tree slice can proceed independently.
7. Drift check: protecting the founder's existing browser and desktop remains more important than forcing a green test.

Recommended next handoff: high reasoning for native clipboard adapter and isolation review; proof level is actual disposable-session native Cmd+V plus exact shell bytes, never a mock-only pass.
