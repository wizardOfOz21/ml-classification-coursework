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

    def test_word_frequencies_include_prose_and_one_text_representation_per_output(self):
        module = self.helpers()
        fence = chr(96) * 3
        inline = chr(96)
        markdown = (
            '# Анализ\nДефолт дефолт, ДЕФОЛТЫ и AP F2\n'
            + inline + 'hidden_code' + inline + ' $TP$ https://example.com/ignored\n'
            + fence + "python\nprint('исключить')\n" + fence + '\n'
            + fence + 'text\nУсловие задания 12345\n' + fence
        )
        output = nbformat.v4.new_output('display_data', data={
            'text/html': '<style>.css_words {color:red}</style><table><tr><td>ДЕФОЛТ</td><td>риск</td><td>loan_status</td></tr></table>',
            'text/plain': 'дубликат',
        })
        image = nbformat.v4.new_output('display_data', data={'image/png': 'AAAA', 'text/plain': 'картинка'})
        rendered = nbformat.v4.new_output('display_data', data={'text/markdown': '**Риск** риск', 'text/plain': 'дубликат'})
        notebook = nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_markdown_cell(markdown),
            nbformat.v4.new_code_cell("print('исключить')", outputs=[output, image, rendered]),
        ])
        result = module.notebook_statistics(notebook)
        self.assertIn('word_frequencies', result, 'Word frequencies have not been implemented')
        words = {row['word']: row for row in result['word_frequencies']}
        self.assertEqual(words['дефолт'], {'word': 'дефолт', 'markdown': 2, 'outputs': 1, 'total': 3})
        self.assertEqual(words['дефолты']['total'], 1)
        self.assertEqual(words['риск']['total'], 3)
        self.assertIn('f2', words)
        self.assertIn('условие', words)
        self.assertIn('задания', words)
        for excluded in ['исключить', 'hidden', 'code', 'tp', 'example', 'ignored', 'дубликат', 'картинка', 'css', 'loan', 'status']:
            self.assertNotIn(excluded, words)
        self.assertEqual(result['frequency_total_words'], sum(row['total'] for row in words.values()))
        self.assertEqual(result['word_frequencies'], sorted(words.values(), key=lambda row: (-row['total'], row['word'])))

    def test_word_frequency_report_contains_all_rows_and_handles_empty_text(self):
        module = self.helpers()
        notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('Кредит кредит риск')])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'words.ipynb'
            nbformat.write(notebook, path)
            report = module.write_statistics(path).read_text()
            self.assertIn('Частотность слов', report)
            self.assertIn('кредит', report)
            self.assertIn('риск', report)
        empty = module.notebook_statistics(nbformat.v4.new_notebook())
        self.assertEqual(empty['word_frequencies'], [])
        self.assertEqual(empty['frequency_total_words'], 0)
