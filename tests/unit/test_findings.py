"""The shared findings table must retain history for one update, without duplicates."""
import runpy
import unittest
from pathlib import Path
import pandas as pd
from tooling.common import ROOT


class FindingsTests(unittest.TestCase):
    def helpers(self):
        path = ROOT / 'src/notebooks/03_analysis/_code/findings.py'
        self.assertTrue(path.exists(), 'The shared findings table is not implemented')
        return runpy.run_path(str(path))

    def test_empty_initial_state_and_new_only_view(self):
        h = self.helpers()
        initial = h['empty_findings']()
        self.assertTrue(initial.empty)
        table = h['update_findings'](initial, [('age', 'Возраст проверен', '—')])
        self.assertTrue(initial.empty)
        self.assertEqual(table.loc['age', 'Метка'], 'new')
        shown = h['findings_view'](table, only_new=True)
        self.assertEqual(shown.data['Выводы'].tolist(), ['+ Возраст проверен'])
        self.assertIn('#dcefe3', shown.to_html())

    def test_removed_rows_show_once_then_disappear(self):
        h = self.helpers()
        table = h['update_findings'](h['empty_findings'](), [('a', 'Старая гипотеза', 'Проверить')])
        table = h['update_findings'](table, [('b', 'Результат', 'Учесть')], remove=['a'])
        self.assertEqual(table.loc['a', 'Метка'], 'removed')
        whole = h['findings_view'](table)
        self.assertIn('− Старая гипотеза', whole.data['Выводы'].tolist())
        self.assertIn('#f9dddd', whole.to_html())
        self.assertEqual(h['findings_view'](table, only_new=True).data['Выводы'].tolist(), ['+ Результат'])
        next_table = h['update_findings'](table, [('c', 'Ещё вывод', '—')])
        self.assertNotIn('a', next_table.index)
        self.assertEqual(next_table.loc['b', 'Метка'], '')

    def test_replacement_and_repeat_do_not_duplicate_active_findings(self):
        h = self.helpers()
        table = h['update_findings'](h['empty_findings'](), [('a', 'Предположение', 'Проверить')])
        table = h['update_findings'](table, [('a', 'Уточнённый результат', 'Сохранить')])
        self.assertEqual((table['Метка'] == 'removed').sum(), 1)
        self.assertEqual(table.loc['a', 'Метка'], 'new')
        table = h['update_findings'](table, [('a', 'Уточнённый результат', 'Сохранить')])
        self.assertEqual(len(table), 1)
        self.assertEqual(h['active_findings'](table).shape, (1, 2))
        with self.assertRaises(ValueError):
            h['update_findings'](table, [('x', 'one', '—'), ('x', 'two', '—')])
