import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import nbformat
import numpy as np
import pandas as pd

from tooling.build.builder import build_notebook
from tests.support.comparison import compare_structure, compare_values
from tooling.testing.reporting import write_report


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'notebooks').mkdir()
        (self.root / 'src').mkdir()
        self.placeholder = "exec('development placeholder')\n"
        code = nbformat.v4.new_code_cell('offset = 4\n' + self.placeholder + 'result = f(2)\n')
        code.metadata['modular'] = {'splices': [{'placeholder': self.placeholder, 'path': 'src/helpers.py'}]}
        md = nbformat.v4.new_markdown_cell('## Section\n\n$\\rho$', attachments={'a.png': {'image/png': 'YWJj'}})
        boot = nbformat.v4.new_code_cell('raise RuntimeError("development only")', metadata={'modular': {'development_only': True}})
        nbformat.write(nbformat.v4.new_notebook(cells=[boot, md, code]), self.root / 'notebooks/01.ipynb')
        nbformat.write(nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('last = result')]), self.root / 'notebooks/02.ipynb')
        (self.root / 'src/helpers.py').write_text('def f(value):\n    return value + offset\n')
        manifest = {'version': 1, 'sections': [{'file': 'notebooks/01.ipynb'}, {'file': 'notebooks/02.ipynb'}], 'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}
        (self.root / 'config/build').mkdir(parents=True)
        (self.root / 'config/build/project.json').write_text(json.dumps(manifest))

    def test_order_attachments_and_late_bound_globals(self):
        nb = build_notebook(self.root)
        self.assertEqual(len(nb.cells), 3)
        self.assertEqual(nb.cells[0].attachments['a.png']['image/png'], 'YWJj')
        self.assertNotIn('modular', nb.cells[1].metadata)
        namespace = {}
        for c in nb.cells:
            if c.cell_type == 'code':
                exec(c.source, namespace)
        self.assertEqual(namespace['last'], 6)
        self.assertNotIn('development placeholder', nb.cells[1].source)

    def test_nested_notebook_includes_preserve_order(self):
        part = nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_code_cell("raise RuntimeError('include must expand')", metadata={'modular': {'include': 'notebooks/01.ipynb'}}),
            nbformat.v4.new_code_cell("raise RuntimeError('include must expand')", metadata={'modular': {'include': 'notebooks/02.ipynb'}}),
        ])
        nbformat.write(part, self.root / 'notebooks/root.ipynb')
        manifest_path = self.root / 'config/build/project.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['sections'] = [{'file': 'notebooks/root.ipynb'}]
        manifest_path.write_text(json.dumps(manifest))
        result = build_notebook(self.root)
        self.assertEqual(len(result.cells), 3)
        namespace = {}
        for cell in result.cells:
            if cell.cell_type == 'code':
                exec(cell.source, namespace)
        self.assertEqual(namespace['last'], 6)
        part.cells.append(nbformat.v4.new_code_cell('', metadata={'modular': {'include': 'notebooks/root.ipynb'}}))
        nbformat.write(part, self.root / 'notebooks/root.ipynb')
        with self.assertRaises(ValueError):
            build_notebook(self.root)

    def test_dev_only_notes_are_omitted_and_loaders_are_expanded(self):
        part = nbformat.read(self.root / 'notebooks/01.ipynb', as_version=4)
        part.cells.insert(0, nbformat.v4.new_markdown_cell(
            'Developer note that must not ship', metadata={'tags': ['dev-only']}))
        part.cells[-1].metadata['tags'] = ['dev-only', 'keep-this-tag']
        nbformat.write(part, self.root / 'notebooks/01.ipynb')
        parent = nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_code_cell("raise RuntimeError('loader must not ship')",
                metadata={'tags': ['dev-only'], 'modular': {'include': 'notebooks/01.ipynb'}}),
        ])
        nbformat.write(parent, self.root / 'notebooks/root.ipynb')
        manifest_path = self.root / 'config/build/project.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['sections'] = [{'file': 'notebooks/root.ipynb'}, {'file': 'notebooks/02.ipynb'}]
        manifest_path.write_text(json.dumps(manifest))
        result = build_notebook(self.root)
        self.assertEqual(len(result.cells), 3)
        namespace = {}
        for cell in result.cells:
            self.assertNotIn('dev-only', cell.metadata.get('tags', []))
            self.assertNotIn('Developer note', cell.source)
            self.assertNotIn('loader must not ship', cell.source)
            if cell.cell_type == 'code':
                exec(cell.source, namespace)
        self.assertEqual(namespace['last'], 6)
        self.assertIn('keep-this-tag', result.cells[1].metadata['tags'])

    def test_edited_module_is_used_in_next_build(self):
        (self.root / 'src/helpers.py').write_text('def f(value):\n    return value * offset\n')
        self.assertIn('return value * offset', build_notebook(self.root).cells[1].source)

    def test_refuses_to_overwrite_either_original(self):
        for name in ['solution.ipynb', 'solution.original.ipynb', 'notebooks/01.ipynb', 'config/build/project.json']:
            with self.assertRaises(ValueError):
                build_notebook(self.root, self.root / name)

    def test_output_cannot_replace_tooling_or_enter_source_data_directories(self):
        for name in ['scripts/build.py', 'README.md', 'data/credit_risk_dataset.csv',
                     'scripts/copy.ipynb', 'data/copy.ipynb', 'src/copy.ipynb',
                     'notebooks/copy.ipynb', 'dataset/copy.ipynb', 'tooling/copy.ipynb', 'config/copy.ipynb']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                build_notebook(self.root, self.root / name)

    def test_missing_module_and_ambiguous_splice_fail(self):
        (self.root / 'src/helpers.py').unlink()
        with self.assertRaises(FileNotFoundError):
            build_notebook(self.root)
        (self.root / 'src/helpers.py').write_text('def f(value):\n    return value\n')
        section = nbformat.read(self.root / 'notebooks/01.ipynb', as_version=4)
        section.cells[-1].source += self.placeholder
        nbformat.write(section, self.root / 'notebooks/01.ipynb')
        with self.assertRaises(ValueError):
            build_notebook(self.root)

    def test_duplicate_definition_and_local_import_fail(self):
        (self.root / 'src/helpers.py').write_text('def f(value):\n    return value\ndef f(value):\n    return value\n')
        with self.assertRaises(ValueError):
            build_notebook(self.root)
        (self.root / 'src/helpers.py').write_text('from src.other import f\n')
        with self.assertRaises(ValueError):
            build_notebook(self.root)


class ValidationTests(unittest.TestCase):
    def test_structure_preserves_markdown_and_parameter_order(self):
        original = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('## A\n$H$'), nbformat.v4.new_code_cell('x = 3\ny = x + 1')])
        equivalent = nbformat.v4.new_notebook(cells=[copy.deepcopy(original.cells[0]), nbformat.v4.new_code_cell('x=3'), nbformat.v4.new_code_cell('y=x+1')])
        self.assertEqual(compare_structure(original, equivalent), [])
        equivalent.cells[-1].source = 'y=x+2'
        self.assertTrue(compare_structure(original, equivalent))
        equivalent = copy.deepcopy(original)
        equivalent.cells[0].source = '## A\n$G$'
        self.assertTrue(compare_structure(original, equivalent))

    def test_integrity_failure_report_does_not_claim_unchanged_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runs = {name: {'status': 'unavailable', 'error': 'skipped'}
                    for name in ['original', 'generated', 'modular']}
            passed = write_report(root, {'sections': [], 'baseline_sha256': 'expected'},
                                  [], ['Original hash changed: solution.ipynb'],
                                  runs, [], True)
            self.assertFalse(passed)
            report = (root / 'tmp/reports/validation_report.md').read_text()
            self.assertNotIn('solution.original.ipynb сохранён без изменений', report)
            self.assertIn('Original hash changed', report)

    def test_capture_excludes_kernel_history_and_plot_handles(self):
        import pickle
        import matplotlib.pyplot as plt
        runtime = Path(__file__).resolve().parents[2] / 'tooling/execution/capture.py'
        namespace = {}
        show = plt.show
        try:
            exec(runtime.read_text(), namespace)
            namespace.update(In=['session-specific history'], Out={},
                             axes=np.array([object()], dtype=object),
                             labels=np.array(['a', 'b'], dtype=object),
                             result=np.array([1., 2.]))
            with tempfile.TemporaryDirectory() as directory:
                filename = Path(directory) / 'capture.pkl'
                namespace['__v_finish'](filename)
                snapshot = pickle.loads(filename.read_bytes())
            self.assertNotIn('In', snapshot['values'])
            self.assertNotIn('Out', snapshot['values'])
            self.assertNotIn('axes', snapshot['values'])
            self.assertIn('labels', snapshot['values'])
            self.assertIn('result', snapshot['values'])
        finally:
            plt.show = show

    def test_numerical_tolerance_tables_and_plot_data(self):
        x = {'table': pd.DataFrame({'v': [1., np.nan]}), 'figure': {'offsets': np.array([1., 2.])}}
        y = copy.deepcopy(x)
        y['table'].iloc[0, 0] += 1e-12
        self.assertEqual(compare_values(x, y), [])
        y['figure']['offsets'][1] = 4.
        self.assertTrue(compare_values(x, y))


if __name__ == '__main__':
    unittest.main()
