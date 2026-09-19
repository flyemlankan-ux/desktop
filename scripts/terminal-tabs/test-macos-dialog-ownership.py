#!/usr/bin/env python3
"""Pure helper tests: no app, Accessibility calls, input or permissions."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('dialogs',Path(__file__).with_name('macos-test-dialogs.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class HelperTests(unittest.TestCase):
 def helper(self, data, foreign=()):
  h=module.OwnedAppDialogs.__new__(module.OwnedAppDialogs)
  h.root=1;h.refs=[1];h.errors=[]
  h.cf=SimpleNamespace(CFEqual=lambda a,b:a==b,CFRelease=lambda _:None)
  reads=[]
  def owner(node):
   if node in foreign:raise module.AccessibilityError('foreign PID')
  def attr(node,key):
   owner(node);reads.append((node,key));return data.get(node,{}).get(key)
  h.owner=owner;h.attr=attr;h.reads=reads
  return h
 def test_union_sheets_focused_cycles_and_external_boundary(self):
  h=self.helper({1:{'AXRole':'AXApplication','AXWindows':[2],'AXChildren':[3],'AXFocusedWindow':4},2:{'AXRole':'AXWindow','AXSheets':[4],'AXChildren':[1,9]},3:{'AXRole':'AXMenuBar'},4:{'AXRole':'AXSheet','AXChildren':[2]}},foreign=[9])
  self.assertEqual({n['element'] for n in h.flatten(h.tree())},{1,2,3,4})
  self.assertFalse(any(node==9 for node,key in h.reads))
 def test_node_limit_fails_closed(self):
  h=self.helper({1:{'AXChildren':[2]},2:{'AXChildren':[3]}})
  with self.assertRaises(module.AccessibilityError):h.tree(max_nodes=2)
 def test_unknown_button_enabled_refused(self):
  h=self.helper({2:{'AXRole':'AXButton'}})
  with self.assertRaisesRegex(module.AccessibilityError,'confirmed enabled'):h.press(2)
 def activation(self,h):
  h.string=lambda _:2
  h.ax=SimpleNamespace(AXUIElementSetAttributeValue=lambda *args:0)
  return patch.object(module.C.c_void_p,'in_dll',return_value=SimpleNamespace(value=1))
 def test_activation_requires_actual_frontmost(self):
  h=self.helper({1:{'AXWindows':[2],'AXFrontmost':False,'AXFocusedWindow':2},2:{'AXRole':'AXWindow'}})
  with self.activation(h),patch.object(module.time,'monotonic',side_effect=[0,1,11]),patch.object(module.time,'sleep'):
   with self.assertRaisesRegex(module.AccessibilityError,'foreground'):h.activate()
 def test_activation_requires_owned_focused_window(self):
  h=self.helper({1:{'AXWindows':[2],'AXFrontmost':True,'AXFocusedWindow':9}},foreign=[9])
  with self.activation(h):
   with self.assertRaisesRegex(module.AccessibilityError,'foreign PID'):h.activate()
 def test_activation_exact_owned_window_succeeds(self):
  h=self.helper({1:{'AXWindows':[2],'AXFrontmost':True,'AXFocusedWindow':2},2:{'AXRole':'AXWindow'}})
  with self.activation(h):h.activate()
if __name__=='__main__':unittest.main()
