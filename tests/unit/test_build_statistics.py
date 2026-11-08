"""Metrics must describe the artifact and keep independent function scopes."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import nbformat

from tooling.common import ROOT


class BuildStatisticsTests(unittest.TestCase):
    def helpers(self):
        path = ROOT / 'tooling/build/statistics.py'
        self.assertTrue(path.exists(), 'Build statistics have not been implemented')
        spec = importlib.util.spec_from_file_location('build_statistics', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_source_ratio_uses_characters_and_keeps_html_separate(self):
        module = self.helpers()
        markdown = '# Обзор\n\n<table><tr><td>Пример</td></tr></table>'
        code = 'x = 1\n'
        notebook = nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_markdown_cell(markdown), nbformat.v4.new_code_cell(code)])
        result = module.notebook_statistics(notebook)
        self.assertEqual(result['markdown_characters'], len(markdown))
        self.assertEqual(result['code_characters'], len(code))
        self.assertEqual(result['readable_text_characters'], len('Обзор Пример'))
        self.assertAlmostEqual(result['source_text_to_code'], len(markdown) / len(code))
        self.assertLess(result['readable_text_characters'], result['markdown_characters'])
        empty = module.notebook_statistics(nbformat.v4.new_notebook())
        self.assertIsNone(empty['source_text_to_code'])
        self.assertEqual(empty['module_complexity'], 0)

    def test_complexity_counts_decisions_but_not_nested_function_bodies_twice(self):
        module = self.helpers()
        code = '''def choose(values, enabled):
    if enabled and values:
        return [x for x in values if x > 0]
    return []

def outer():
    def inner(x):
        if x:
            return 1
        return 0
    return inner

if ready:
    choose([], True)
'''
        notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(code)])
        result = module.notebook_statistics(notebook)
        complexities = {f['name']: f['complexity'] for f in result['functions']}
        self.assertEqual(complexities['choose'], 5)
        self.assertEqual(complexities['outer'], 1)
        self.assertEqual(complexities['outer.inner'], 2)
        self.assertEqual(result['module_complexity'], 2)

    def test_report_uses_exact_file_size_and_is_refreshed_after_outputs_change(self):
        module = self.helpers()
        notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('print(1)')])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'custom.ipynb'
            nbformat.write(notebook, path)
            report = module.write_statistics(path)
            self.assertEqual(report.name, 'custom.stats.txt')
            before = report.read_text()
            self.assertIn(str(path.stat().st_size), before)
            notebook.cells[0].outputs = [nbformat.v4.new_output('stream', name='stdout', text='x' * 4000)]
            notebook.cells[0].execution_count = 1
            nbformat.write(notebook, path)
            module.write_statistics(path)
            after = report.read_text()
            self.assertNotEqual(before, after)
            self.assertIn(str(path.stat().st_size), after)
            self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), after)
            self.assertIn('Цикломатическая', after)
