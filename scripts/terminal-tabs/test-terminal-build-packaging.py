#!/usr/bin/env python3
"""Focused native-helper build and Firefox 155 bundle/repack proof.

Runs the pinned upstream assembler, not an imitation. Only temporary synthetic
app data is used. This is not a full Firefox compile or final installer test.
"""
import ast
import hashlib
import importlib.util
import json
import posixpath
from types import SimpleNamespace
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).with_name('fixtures') / 'firefox155-packaging'
ASSEMBLER = 'python/mozbuild/mozbuild/action/assemble_macos_bundle.py'
MACOS_LIST = 'browser/app/macbuild/Contents/MacOS-files.in'


class PackagingTests(unittest.TestCase):
    def test_pristine_source_receipts(self):
        receipt = json.loads((FIXTURES / 'receipt.json').read_text())
        self.assertEqual(receipt['ref'], 'FIREFOX_155_0_1_RELEASE')
        for name, expected in receipt['files'].items():
            data = (FIXTURES / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), expected['sha256'])
            self.assertEqual(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(), expected['git_blob_sha1'])

    def test_native_build_declaration_uses_standalone_program(self):
        # Execute the real small moz.build declaration on each platform, using
        # a recording Program template. No GeckoProgram/linkage is permitted.
        declaration = (ROOT / 'src/zen/terminal/moz.build').read_text()
        for platform in ['Darwin', 'Linux', 'WINNT']:
            programs = []
            context = {'CONFIG': {'OS_ARCH': platform}, 'Program': programs.append, 'SOURCES': []}
            exec(compile(declaration, 'terminal/moz.build', 'exec'), context)
            self.assertEqual(programs, ['zen-terminal-pty'] if platform == 'Darwin' else [])
            self.assertEqual(context['SOURCES'], ['native/zen-terminal-pty.c'] if platform == 'Darwin' else [])
        # Pinned Firefox Program template uses only PROGRAM, Binary and optional
        # profiling. It does not call GeckoProgram or request Gecko libraries.
        tree = ast.parse((FIXTURES / 'build/templates.mozbuild').read_text())
        program = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'Program')
        calls = [n.func.id for n in ast.walk(program) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertEqual(calls, ['MaybeAddProfiling', 'Binary'])
        self.assertIn('"terminal"', (ROOT / 'src/zen/moz.build').read_text())

    def test_pristine_program_output_is_the_staging_input(self):
        # Execute Firefox's actual output-path property in isolation. Its
        # ObjDirPath wrapper is replaced only with a transparent string return.
        tree = ast.parse((FIXTURES / 'python/mozbuild/mozbuild/frontend/data.py').read_text())
        linkable = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Linkable')
        method = next(n for n in linkable.body if isinstance(n, ast.FunctionDef) and n.name == 'output_path')
        method.decorator_list = []
        context = {'mozpath': posixpath, 'ObjDirPath': lambda context, path: path}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'pristine-data.py', 'exec'), context)
        program = SimpleNamespace(installed=True, _context={}, install_target='dist/bin', name='zen-terminal-pty')
        self.assertEqual(context['output_path'](program), '!/dist/bin/zen-terminal-pty')
        app = (FIXTURES / 'browser/app/moz.build').read_text()
        self.assertIn('stage=f"!/{FINAL_TARGET}"', app)
        self.assertIn('macos_files="!macbuild/Contents/MacOS-files.txt"', app)

    @unittest.skipUnless(sys.platform == 'darwin', 'Actual Mac helper compilation requires macOS')
    def test_real_helper_survives_pristine_assembly_and_repack(self):
        with tempfile.TemporaryDirectory(prefix='zen-packaging-proof-') as temporary:
            run = Path(temporary).resolve()
            staged = run / 'dist/bin'; staged.mkdir(parents=True)
            fixture = run / MACOS_LIST; fixture.parent.mkdir(parents=True)
            shutil.copy2(FIXTURES / MACOS_LIST, fixture)
            patch = ROOT / 'src/browser/app/macbuild/Contents/MacOS-files-in.patch'
            subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(patch)], cwd=run, check=True, capture_output=True)
            # These are rsync patterns; preprocess unrelated upstream #ifdefs
            # by retaining all patterns. /zen-terminal-pty must be unconditional.
            patterns = run / 'MacOS-files.txt'
            patterns.write_text('\n'.join(line for line in fixture.read_text().splitlines() if line.startswith('/')) + '\n')
            copy_patterns = run / 'MacOS-copy.txt'; copy_patterns.write_text('')
            helper = staged / 'zen-terminal-pty'
            subprocess.run([str(ROOT / 'scripts/terminal-tabs/build-terminal-pty.sh'), str(helper)], check=True, capture_output=True)
            self.assertTrue(helper.stat().st_mode & 0o111)
            linkage = subprocess.check_output(['otool', '-L', str(helper)], text=True)
            self.assertNotIn('mozglue', linkage)
            self.assertNotIn('XUL', linkage)
            helper_bytes = helper.read_bytes()
            # Include the nested .app that the previous workflow incorrectly
            # selected. It must never receive our main-app helper.
            plugin = staged / 'plugin-container.app/Contents/MacOS'; plugin.mkdir(parents=True)
            (plugin / 'plugin-container').write_text('synthetic plugin')
            (staged / 'ordinary-resource').write_text('synthetic resource')
            bundle = run / 'dist/Zen Terminal.app'
            spec = {'bundle': str(bundle), 'lproj': 'en.lproj', 'stage': str(staged),
                    'macos_files': str(patterns), 'macos_copy_files': str(copy_patterns)}
            specfile = run / 'bundle.json'; specfile.write_text(json.dumps(spec))
            module_spec = importlib.util.spec_from_file_location('pristine_assembler', FIXTURES / ASSEMBLER)
            assembler = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(assembler)
            for attempt in range(2):
                if attempt:
                    (bundle / 'must-be-removed-on-repack').write_text('stale bundle data')
                self.assertEqual(assembler.main([str(specfile)]), 0)
                packaged = bundle / 'Contents/MacOS/zen-terminal-pty'
                self.assertEqual(packaged.read_bytes(), helper_bytes)
                self.assertTrue(packaged.stat().st_mode & 0o111)
                self.assertFalse((bundle / 'Contents/Resources/zen-terminal-pty').exists())
                self.assertFalse((bundle / 'Contents/MacOS/plugin-container.app/Contents/MacOS/zen-terminal-pty').exists())
                self.assertFalse((bundle / 'must-be-removed-on-repack').exists())
                self.assertEqual((bundle / 'Contents/Resources/ordinary-resource').read_text(), 'synthetic resource')
                # Launch only the disposable helper with malformed arguments;
                # it must reject safely without starting a shell or PTY.
                result = subprocess.run([str(packaged)], capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
            self.assertEqual(helper.read_bytes(), helper_bytes)


if __name__ == '__main__':
    unittest.main(verbosity=2)
