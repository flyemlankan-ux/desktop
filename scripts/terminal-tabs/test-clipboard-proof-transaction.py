#!/usr/bin/env python3
"""Synthetic in-memory policy tests only. Never accesses any macOS pasteboard."""
import importlib.util
import sys
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('clipboard_policy',Path(__file__).with_name('clipboard-proof-transaction.py'))
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
Flavor=module.Flavor;Transaction=module.ClipboardProofTransaction;Unsafe=module.UnsafeClipboard

class MemoryBoard:
    disposable_exclusive=True
    complete_enumeration=True
    def __init__(self, entries=None):
        self.entries=list(entries if entries is not None else [(Flavor(1,'public.utf8-plain-text'),b'fixture'),(Flavor(1,'public.html'),b'<b>fixture</b>'),(Flavor(2,'public.png'),b'\x89PNG\x00\xff')])
        self.count=7;self.reads=0;self.writes=0;self.during_read=None
    def change_count(self):return self.count
    def flavors(self):return [f for f,data in self.entries]
    def read(self,flavor):
        self.reads+=1
        if self.during_read:self.during_read(self)
        return next(data for f,data in self.entries if f==flavor)
    def replace(self,entries):
        self.entries=list(entries);self.count+=1;self.writes+=1;return self.count

class Tests(unittest.TestCase):
    def test_multiformat_multiitem_exact_roundtrip(self):
        board=MemoryBoard();original=board.entries.copy();t=Transaction(board);t.capture();t.install("printf '%s\\n' 'snow 雪'\n");self.assertEqual(t.close(),'fixture_restored');self.assertEqual(board.entries,original);self.assertIsNone(t.snapshot)
    def test_later_writer_not_overwritten(self):
        board=MemoryBoard();t=Transaction(board);t.capture();t.install('test');board.replace([(Flavor(1,'public.text'),b'new writer')]);self.assertEqual(t.close(),'later_writer_preserved');self.assertEqual(board.entries[0][1],b'new writer');self.assertEqual(board.writes,2)
    def test_unsafe_flavor_preflight_reads_nothing(self):
        for flag in [1,2,4,8,256,512,1<<20]:
            board=MemoryBoard([(Flavor(1,'public.text'),b'fine'),(Flavor(2,'opaque',flag),b'not read')]);t=Transaction(board)
            with self.assertRaises(Unsafe):t.capture()
            self.assertEqual((board.reads,board.writes),(0,0))
    def test_changed_during_capture(self):
        board=MemoryBoard();board.during_read=lambda b:setattr(b,'count',b.count+1);t=Transaction(board)
        with self.assertRaises(Unsafe):t.capture()
        self.assertEqual(board.writes,0)
    def test_changed_before_install(self):
        board=MemoryBoard();t=Transaction(board);t.capture();board.count+=1
        with self.assertRaises(Unsafe):t.install('test')
        self.assertEqual(board.writes,0)
    def test_bounded_snapshot(self):
        board=MemoryBoard();t=Transaction(board,max_bytes=2)
        with self.assertRaises(Unsafe):t.capture()
        self.assertEqual(board.writes,0)
    def test_missing_representation(self):
        board=MemoryBoard([(Flavor(1,'public.text'),None)]);t=Transaction(board)
        with self.assertRaises(Unsafe):t.capture()
        self.assertEqual(board.writes,0)
    def test_personal_board_refused_without_read(self):
        board=MemoryBoard();board.disposable_exclusive=False
        with self.assertRaises(Unsafe):Transaction(board)
        self.assertEqual((board.reads,board.writes),(0,0))
    def test_incomplete_inventory_refused(self):
        board=MemoryBoard();board.complete_enumeration=False
        with self.assertRaises(Unsafe):Transaction(board)
        self.assertEqual((board.reads,board.writes),(0,0))
    def test_empty_fixture(self):
        board=MemoryBoard([]);t=Transaction(board);t.capture();t.install('test');t.close();self.assertEqual(board.entries,[])
    def test_close_idempotent(self):
        board=MemoryBoard();t=Transaction(board);t.capture();t.install('test');t.close();self.assertEqual(t.close(),'already_closed');self.assertEqual(board.writes,2)
    def test_general_adapter_unconditionally_refuses(self):
        with self.assertRaises(Unsafe):module.system_clipboard_adapter()

if __name__=='__main__':unittest.main()
