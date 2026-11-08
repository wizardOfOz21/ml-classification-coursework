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
            notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("raise ValueError('bad notebook')")])
            manifest = {'targets': {'submission': {'output': str(target.relative_to(root))}}}
            with patch.object(runner, 'ROOT', root), patch.object(runner, 'load_manifest', return_value=manifest), \
                 patch.object(runner, 'build_notebook', return_value=notebook), \
                 patch.object(runner.NotebookClient, 'execute', side_effect=RuntimeError('execution failed')):
                with self.assertRaisesRegex(RuntimeError, 'execution failed'):
                    runner.run()
            self.assertEqual(target.read_bytes(), b'previous successful submission')
