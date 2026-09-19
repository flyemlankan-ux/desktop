#!/usr/bin/env python3
"""Fail-closed clipboard proof policy. No operating-system clipboard access.

A real general-pasteboard adapter is intentionally absent: macOS cannot enumerate
request-only formats or atomically compare-and-restore a concurrent clipboard.
Only a disposable, exclusively owned fixture can satisfy this interface honestly.
Never log, serialize or persist snapshot bytes.
"""
from dataclasses import dataclass

class UnsafeClipboard(RuntimeError):
    pass

@dataclass(frozen=True)
class Flavor:
    item: int
    kind: str
    flags: int = 0

class ClipboardProofTransaction:
    """Hold fixture bytes in memory; never restore over an observed later writer.

    Board protocol: disposable_exclusive, complete_enumeration, change_count(),
    flavors(), read(flavor), replace([(Flavor, bytes), ...]) -> new change count.
    replace is NOT a macOS atomic compare-and-swap. Live personal boards are
    forbidden even if someone claims they can enumerate their visible formats.
    """
    def __init__(self, board, max_bytes=8 * 1024 * 1024):
        if not getattr(board, 'disposable_exclusive', False):
            raise UnsafeClipboard('A disposable, exclusively owned clipboard fixture is required')
        if not getattr(board, 'complete_enumeration', False):
            raise UnsafeClipboard('Complete format enumeration cannot be guaranteed')
        self.board = board
        self.max_bytes = max_bytes
        self.snapshot = None
        self.original_count = None
        self.owned_count = None
        self.closed = False

    def capture(self):
        if self.snapshot is not None or self.closed:
            raise UnsafeClipboard('Transaction cannot be reused')
        before = self.board.change_count()
        flavors = list(self.board.flavors())
        if len(flavors) > 256 or len({(f.item, f.kind) for f in flavors}) != len(flavors):
            raise UnsafeClipboard('Unsupported clipboard inventory')
        # Preflight EVERY representation before reading ANY payload. Reject
        # promised, volatile, sender-only, request-only, translated and unknown
        # flags, rather than turning promises into data or silently losing flags.
        if any(not isinstance(f, Flavor) or f.flags != 0 for f in flavors):
            raise UnsafeClipboard('Clipboard contains unsupported representation semantics')
        snapshot = []
        total = 0
        for flavor in flavors:
            if self.board.change_count() != before:
                raise UnsafeClipboard('Clipboard changed during capture')
            payload = self.board.read(flavor)
            if not isinstance(payload, bytes):
                raise UnsafeClipboard('Clipboard representation could not be captured')
            total += len(payload)
            if total > self.max_bytes:
                raise UnsafeClipboard('Clipboard snapshot exceeds bounded memory budget')
            snapshot.append((flavor, payload))
        if self.board.change_count() != before:
            raise UnsafeClipboard('Clipboard changed during capture')
        self.snapshot = snapshot
        self.original_count = before

    def install(self, harmless_test_text):
        if self.snapshot is None or self.closed or self.owned_count is not None:
            raise UnsafeClipboard('Capture must precede exactly one fixture write')
        if self.board.change_count() != self.original_count:
            raise UnsafeClipboard('Clipboard changed before fixture write')
        payload = harmless_test_text.encode('utf-8')
        if len(payload) > 65536:
            raise UnsafeClipboard('Test payload too large')
        self.owned_count = self.board.replace([(Flavor(1, 'public.utf8-plain-text'), payload)])
        return self.owned_count

    def close(self):
        if self.closed:
            return 'already_closed'
        self.closed = True
        try:
            if self.owned_count is None:
                return 'unchanged'
            if self.board.change_count() != self.owned_count:
                return 'later_writer_preserved'
            self.board.replace(self.snapshot)
            return 'fixture_restored'
        finally:
            # Release references, not a claim of cryptographic memory erasure.
            self.snapshot = None


def system_clipboard_adapter():
    """Always refuse before even requesting NSPasteboard.generalPasteboard."""
    raise UnsafeClipboard(
        'Personal/system clipboard proof is disabled: public macOS APIs cannot '
        'guarantee all-format snapshot or atomic conditional restoration. '
        'Use a dedicated disposable macOS login session for native Cmd+V proof.'
    )
