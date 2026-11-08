"""A failed execution must not destroy the last usable submission."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import nbformat
from tooling.execution import runner


class SubmissionExecutionTests(unittest.TestCase):
    def test_execution_failure_keeps_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'tmp/build/submission/solution.ipynb'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'previous successful submission')
            statistics = target.with_suffix('.stats.txt')
            statistics.write_text('previous statistics')
            notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("raise ValueError('bad notebook')")])
            manifest = {'targets': {'submission': {'output': str(target.relative_to(root))}}}
            with patch.object(runner, 'ROOT', root), patch.object(runner, 'load_manifest', return_value=manifest), \
                 patch.object(runner, 'build_notebook', return_value=notebook), \
                 patch.object(runner.NotebookClient, 'execute', side_effect=RuntimeError('execution failed')):
                with self.assertRaisesRegex(RuntimeError, 'execution failed'):
                    runner.run()
            self.assertEqual(target.read_bytes(), b'previous successful submission')
            self.assertEqual(statistics.read_text(), 'previous statistics')

    def test_successful_execution_writes_statistics_for_final_file(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'tmp/build/submission/solution.ipynb'
            notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('print(1)')])
            manifest = {'targets': {'submission': {'output': str(target.relative_to(root))}}}
            def executed(**kwargs):
                notebook.cells[0].execution_count = 1
                notebook.cells[0].outputs = [nbformat.v4.new_output('stream', name='stdout', text='1' * 2000)]
            with patch.object(runner, 'ROOT', root), patch.object(runner, 'load_manifest', return_value=manifest), \
                 patch.object(runner, 'build_notebook', return_value=notebook), \
                 patch.object(runner.NotebookClient, 'execute', side_effect=executed):
                runner.run()
            report = target.with_suffix('.stats.txt')
            self.assertTrue(report.is_file())
            text = report.read_text()
            self.assertIn(str(target.stat().st_size), text)
            self.assertIn(hashlib.sha256(target.read_bytes()).hexdigest(), text)
            self.assertIn('Кодовых ячеек с номером выполнения: 1 из 1', text)
