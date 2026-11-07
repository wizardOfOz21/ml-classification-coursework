import unittest
import nbformat
from tooling.common import ROOT, load_manifest
from tooling.build.builder import build_notebook
from tests.regression.checks import layout_baseline
from tests.support.comparison import compare_structure

class AssemblyTests(unittest.TestCase):
    def test_real_sources_preserve_baseline_and_remove_local_loaders(self):
        result = build_notebook()
        original = nbformat.read(ROOT / load_manifest()['baseline'], as_version=4)
        self.assertEqual(compare_structure(layout_baseline(original), result), [])
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
