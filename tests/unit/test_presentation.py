"""Static descriptions must not weaken checks of analytical results."""
import ast
import unittest
import nbformat
import pandas as pd
from tests.support.presentation import remove_description_code, analytical_snapshot


class PresentationProjectionTests(unittest.TestCase):
    def test_only_description_displays_are_removed(self):
        source = '''source_descriptions = {'x': 'source'}
interpretations = {'x': 'meaning'}
columns_info['Описание из источника'] = source_descriptions
columns_info['Описание'] = interpretations
columns_info['Фактический тип'] = types
value = 17
display(columns_info[['Описание', 'Фактический тип']])
display(other_analysis[['Описание']])
'''
        original = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(source)])
        projected = remove_description_code(original).cells[0].source
        self.assertIn('value = 17', projected)
        self.assertIn("columns_info['Фактический тип'] = types", projected)
        self.assertIn("display(other_analysis[['Описание']])", projected)
        self.assertNotIn('source_descriptions', projected)
        self.assertEqual(original.cells[0].source, source)

    def test_snapshot_keeps_numeric_tables_types_and_model_results(self):
        source = pd.DataFrame({'Описание из источника': ['Age']})
        domains = pd.DataFrame({'Описание из источника': ['Age'], 'Домен': ['[20, 94]']})
        meanings = pd.DataFrame({'Описание из источника': ['Age'], 'Описание': ['возраст'], 'Фактический тип': ['числовой']})
        numeric = pd.DataFrame({'AP': [.91]})
        old = {'tables': [source, domains, meanings, numeric], 'plots': ['unchanged'],
               'values': {'source_descriptions': {'x': 'Age'}, 'interpretations': {'x': 'возраст'},
                          'columns_info': meanings, 'AP': .91}}
        new = analytical_snapshot(old)
        self.assertEqual(len(new['tables']), 2)
        pd.testing.assert_frame_equal(new['tables'][0], domains[['Домен']])
        pd.testing.assert_frame_equal(new['tables'][1], numeric)
        pd.testing.assert_frame_equal(new['values']['columns_info'], meanings[['Фактический тип']])
        self.assertEqual(new['values']['AP'], .91)
        self.assertEqual(new['plots'], ['unchanged'])
        self.assertEqual(len(old['tables']), 4)
        self.assertIn('source_descriptions', old['values'])
