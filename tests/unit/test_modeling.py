"""Analytical behavior that would fail with leakage, lost order or a test-tuned threshold."""
import runpy
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from tooling.common import ROOT


def load_helpers(name):
    path = ROOT / 'src/notebooks/_code' / name
    return runpy.run_path(str(path)) if path.exists() else {}


class ModelingTests(unittest.TestCase):
    def setUp(self):
        self.prep = load_helpers('preprocessing.py')
        self.select = load_helpers('selection.py')

    def test_preprocessing_is_train_fitted_and_grade_order_is_preserved(self):
        self.assertIn('make_preprocessor', self.prep, 'Train-only preprocessing is not implemented')
        factory = self.prep['make_preprocessor']
        frame = pd.read_csv(ROOT / 'dataset/credit_risk_dataset.csv').head(40).drop(columns='loan_status')
        frame.loc[frame.index[:2], 'person_emp_length'] = np.nan
        transformer = factory().fit(frame)
        median = frame['person_emp_length'].median()
        imputer = transformer.named_transformers_['numerical'].named_steps['impute']
        position = self.prep['NUMERICAL_FEATURES'].index('person_emp_length')
        self.assertEqual(imputer.statistics_[position], median)
        other = frame.iloc[:7].copy()
        other['loan_grade'] = list('ABCDEFG')
        other['person_emp_length'] = 9999
        other['loan_intent'] = 'NEW_CATEGORY'
        transformed = transformer.transform(other)
        self.assertTrue(np.isfinite(transformed).all())
        self.assertEqual(imputer.statistics_[position], median)
        ordinal = transformer.named_transformers_['ordinal'].transform(other[['loan_grade']])
        np.testing.assert_array_equal(ordinal.ravel(), np.arange(7))
        # Target must never enter a transformed feature name.
        self.assertFalse(any('loan_status' in s for s in transformer.get_feature_names_out()))

    def test_f2_threshold_uses_validation_probabilities_and_is_reproducible(self):
        self.assertIn('select_f2_threshold', self.select, 'Validation threshold selection is not implemented')
        y = np.array([0, 1, 0, 1, 0, 1])
        probabilities = np.array([.05, .4, .2, .8, .3, .6])
        threshold, scores = self.select['select_f2_threshold'](y, probabilities)
        self.assertEqual(threshold, .4)
        self.assertAlmostEqual(scores['F2'].max(), 1.0)
        self.assertEqual(threshold, self.select['select_f2_threshold'](y, probabilities)[0])

    def test_inference_rejects_missing_features_and_unknown_grade(self):
        self.assertIn('prepare_applications', self.prep, 'Inference contract is not implemented')
        prepare = self.prep['prepare_applications']
        frame = pd.read_csv(ROOT / 'dataset/credit_risk_dataset.csv').head(2).drop(columns='loan_status')
        with self.assertRaisesRegex(ValueError, 'столбц'):
            prepare(frame.drop(columns='person_income'))
        frame['loan_grade'] = 'Z'
        with self.assertRaisesRegex(ValueError, 'loan_grade'):
            prepare(frame)

    def test_inference_keeps_rows_and_matches_employment_cleaning(self):
        self.assertIn('prepare_applications', self.prep, 'Inference contract is not implemented')
        frame = pd.read_csv(ROOT / 'dataset/credit_risk_dataset.csv').head(2).drop(columns='loan_status')
        frame['person_emp_length'] = [123, -1]
        frame['loan_intent'] = ['NEW_CATEGORY', None]
        prepared = self.prep['prepare_applications'](frame)
        self.assertEqual(len(prepared), 2)
        self.assertTrue(prepared['person_emp_length'].isna().all())
        self.assertEqual(prepared.iloc[0]['loan_intent'], 'NEW_CATEGORY')

    def test_f2_tie_prefers_larger_threshold(self):
        # Correct F2 is equal at one true positive / one prediction and at 2 / 10.
        y = np.array([1] + [0] * 8 + [1])
        probabilities = np.linspace(1, .1, 10)
        threshold, table = self.select['select_f2_threshold'](y, probabilities)
        self.assertEqual(np.isclose(table['F2'], table['F2'].max()).sum(), 2)
        self.assertEqual(threshold, 1.0)

    def test_every_candidate_imputer_fits_only_train(self):
        # Fitting on validation or concatenated splits would change all medians.
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.pipeline import Pipeline
        from threadpoolctl import threadpool_limits
        source = ROOT / 'src/notebooks/_code/train_models.py'
        frame = pd.read_csv(ROOT / 'dataset/credit_risk_dataset.csv').head(80)
        x = frame.drop(columns='loan_status')
        y = frame['loan_status'].astype(int)
        other = x.copy()
        other.loc[:, self.prep['NUMERICAL_FEATURES']] = 100000
        namespace = {
            **self.select, 'Pipeline': Pipeline, 'preprocessor_template': self.prep['make_preprocessor'](),
            'X_train': x, 'y_train': y, 'X_validation': other, 'y_validation': y,
            'display': lambda *args: None, 'Markdown': lambda text: text, 'plt': plt,
        }
        from unittest.mock import patch
        with threadpool_limits(limits=1), patch.object(plt, "show"):
            result = runpy.run_path(str(source), init_globals=namespace)
        plt.close('all')
        expected = x[self.prep['NUMERICAL_FEATURES']].median().to_numpy()
        for name, pipeline in result['trained_models'].items():
            with self.subTest(model=name):
                actual = pipeline.named_steps['preprocess'].named_transformers_['numerical'].named_steps['impute'].statistics_
                np.testing.assert_allclose(actual, expected)
