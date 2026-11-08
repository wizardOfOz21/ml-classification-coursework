"""Scientific contracts independent of which candidate wins."""
import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, fbeta_score


def check_modeling_results(values):
    errors = []
    try:
        train, val, test = (values[k] for k in ['train', 'validation', 'test'])
        assert not set(train.index) & set(val.index)
        assert not set(train.index) & set(test.index)
        assert not set(val.index) & set(test.index)
        assert len(train) + len(val) + len(test) == 32411
        assert 'loan_status' not in values['X_train'].columns
        matrix = values['association_matrix'].to_numpy()
        np.testing.assert_allclose(matrix, matrix.T, equal_nan=True)
        assert np.isfinite(matrix).all()
        np.testing.assert_allclose(np.diag(matrix), 1)
        assert values['validation_comparison'].shape[0] == 8
        assert values['selected_model_name'] == values['validation_comparison']['AP'].idxmax()
        assert values['frozen_decision']['fit_sample'] == 'train only'
        threshold = values['selected_threshold']
        curve = values['threshold_curve']
        row = curve.loc[curve['Порог'].eq(threshold)].iloc[0]
        assert np.isclose(row['F2'], curve['F2'].max())
        y, probability = values['y_test'], values['test_probability']
        assert len(probability) == len(test)
        assert np.isfinite(probability).all() and ((0 <= probability) & (probability <= 1)).all()
        prediction = (probability >= threshold).astype(int)
        np.testing.assert_array_equal(prediction, values['test_prediction'])
        np.testing.assert_array_equal(confusion_matrix(y, prediction), values['test_confusion'])
        metrics = values['test_metrics'].iloc[1]
        assert np.isclose(metrics['AP'], average_precision_score(y, probability))
        assert np.isclose(metrics['F2'], fbeta_score(y, prediction, beta=2))
        assert values['bootstrap_metrics'].shape[0] == 300
        assert values['example_predictions'].shape == (3, 2)
        assert values['final_conclusions'].shape[1] == 2
    except (AssertionError, KeyError, IndexError, ValueError) as error:
        errors.append(f'Modeling output contract failed: {type(error).__name__}: {error}')
    return errors
