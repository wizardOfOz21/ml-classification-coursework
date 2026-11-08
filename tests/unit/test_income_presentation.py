"""The logarithmic view must follow an observation from the ordinary plot."""
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import nbformat
import pandas as pd
import seaborn as sns

from tooling.common import ROOT


class IncomePresentationTests(unittest.TestCase):
    def test_ordinary_plot_precedes_explanation_and_logarithmic_plot(self):
        notebook = nbformat.read(
            ROOT / 'src/notebooks/03_analysis/01_basic_eda/03_univariate/03_income.ipynb',
            as_version=4)
        data = pd.DataFrame({'person_income': [40_000] * 50 + [60_000] * 40 + [2_000_000]})
        events = []

        def display(value):
            events.append(('explanation', value.data) if type(value).__name__ == 'Markdown'
                          else ('table', value))

        def show():
            events.append(('plot', [ax.get_xscale() for ax in plt.gcf().axes]))
            plt.close('all')

        namespace = {'data': data, 'pd': pd, 'sns': sns, 'plt': plt, 'display': display}
        try:
            with patch.object(plt, 'show', side_effect=show):
                for cell in notebook.cells:
                    if cell.cell_type == 'code' and cell.metadata.get('origin_cell') == 29:
                        exec(cell.source, namespace)
                    elif cell.cell_type == 'markdown' and events and events[-1][0] == 'plot':
                        if 'логарифмическ' in cell.source:
                            events.append(('explanation', cell.source))
        finally:
            plt.close('all')
        self.assertEqual([event[0] for event in events], ['table', 'plot', 'explanation', 'plot'])
        self.assertEqual(events[1][1], ['linear', 'linear'])
        self.assertIn('логарифмическ', events[2][1])
        self.assertEqual(events[3][1], ['log'])
        pd.testing.assert_series_equal(namespace['income'], data['person_income'])
        self.assertEqual(namespace['income_stats'].loc['50%', 'Значение'], 40_000)
