import unittest
import nbformat
from tooling.common import ROOT, load_manifest
from tooling.build.builder import build_notebook
from tests.regression.checks import layout_baseline
from tests.support.comparison import compare_structure
from tests.support.notebook_content import compare_legacy_content, legacy_notebook, extension_order_errors

class AssemblyTests(unittest.TestCase):
    def test_real_sources_preserve_baseline_and_remove_local_loaders(self):
        result = build_notebook()
        original = nbformat.read(ROOT / load_manifest()['baseline'], as_version=4)
        self.assertEqual(compare_structure(layout_baseline(original), legacy_notebook(result), compare_markdown=False), [])
        errors, outputs_preserved = compare_legacy_content(original, result, ROOT, load_manifest())
        self.assertEqual(errors, [])
        self.assertTrue(outputs_preserved)
        self.assertEqual(extension_order_errors(result), [])
        for cell in result.cells:
            if cell.cell_type == 'code':
                self.assertNotIn("exec(compile(__import__('pathlib')", cell.source)
            self.assertNotIn('modular', cell.metadata)

    def test_sandbox_runs_when_opened_from_notebooks_directory(self):
        import subprocess
        import sys
        code = """import contextlib, io, json
from pathlib import Path
notebook = json.loads(Path('sandbox.ipynb').read_text())
namespace = {}
with contextlib.redirect_stdout(io.StringIO()):
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            exec(''.join(cell['source']), namespace)
assert namespace['data'].shape == (32581, 12)
assert namespace['x'] == 4
"""
        subprocess.run([sys.executable, '-c', code], cwd=ROOT / 'src/notebooks', check=True)

    def test_seven_stage_contracts_and_assignment(self):
        import json
        manifest = load_manifest()
        self.assertEqual(len(manifest['stages']), 7)
        for stage in manifest['stages']:
            notebook = nbformat.read(ROOT / stage['file'], as_version=4)
            intro = notebook.cells[0].source
            for heading in ['**Входы**', '**Выходы**', '**Что делаем**']:
                self.assertIn(heading, intro)
        first = nbformat.read(ROOT / manifest['stages'][0]['file'], as_version=4)
        self.assertIn((ROOT / 'docs/specifications/assignment.txt').read_text().rstrip(), first.cells[0].source)
        # All Python splices are adjacent to their including notebook, in _code/
        for path in (ROOT / 'src/notebooks').rglob('*.ipynb'):
            if path.name == 'sandbox.ipynb':
                continue
            document = nbformat.read(path, as_version=4)
            for cell in document.cells:
                for splice in cell.metadata.get('modular', {}).get('splices', []):
                    self.assertEqual((ROOT / splice['path']).parent, path.parent / '_code')
