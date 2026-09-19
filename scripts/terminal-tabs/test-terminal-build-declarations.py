#!/usr/bin/env python3
"""Preflight literal sorted build declarations; not a full Gecko configure run."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def unsorted_declarations(source):
    failures = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.AugAssign) or not isinstance(node.value, ast.List):
            continue
        target = ast.unparse(node.target)
        # DIRS order is meaningful and is NOT one of these sorted declarations.
        if target.split('.')[0] not in {'EXTRA_JS_MODULES', 'SOURCES', 'UNIFIED_SOURCES'}:
            continue
        entries = [item.value for item in node.value.elts
                   if isinstance(item, ast.Constant) and isinstance(item.value, str)]
        if len(entries) != len(node.value.elts):
            continue  # This bounded check makes no claim about computed entries.
        # Mozilla StrictOrderingOnAppendList.ensure_sorted uses lowercase keys.
        if entries != sorted(entries, key=str.lower):
            failures.append((node.lineno, target, entries))
    return failures


class BuildDeclarations(unittest.TestCase):
    def test_current_zen_literal_module_and_source_lists_are_sorted(self):
        for path in sorted((ROOT / 'src/zen').rglob('moz.build')):
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertEqual(unsorted_declarations(path.read_text()), [])

    def test_cloud_failure_order_is_rejected(self):
        self.assertTrue(unsorted_declarations('EXTRA_JS_MODULES.zen.share += ["share.schema.json", "ZenShareClient.sys.mjs", "ZenShareSafety.sys.mjs", "ZenShareManager.mjs"]'))

    def test_case_insensitive_order_and_meaningful_directory_order(self):
        self.assertEqual(unsorted_declarations('EXTRA_JS_MODULES.zen.share += ["share.schema.json", "ZenShareClient.sys.mjs", "ZenShareManager.mjs", "ZenShareSafety.sys.mjs"]\nDIRS += ["z", "a"]'), [])

    def test_safety_module_is_still_registered_once(self):
        source = (ROOT / 'src/zen/share/moz.build').read_text()
        self.assertEqual(source.count('"ZenShareSafety.sys.mjs"'), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
