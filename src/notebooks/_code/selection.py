"""Метрики и порог: без доступа к test и без переобучения моделей."""
import numpy as np
import pandas as pd
from sklearn.metrics import (

    accuracy_score, average_precision_score, balanced_accuracy_score,
    brier_score_loss, f1_score, fbeta_score, precision_recall_curve,
    precision_score, recall_score, roc_auc_score,
)


def classification_metrics(y_true, probabilities, threshold=0.5):
    predictions = np.asarray(probabilities) >= threshold
    return {
        'AP': average_precision_score(y_true, probabilities),
        'ROC-AUC': roc_auc_score(y_true, probabilities),
        'Precision': precision_score(y_true, predictions, zero_division=0),
        'Recall': recall_score(y_true, predictions, zero_division=0),
        'F1': f1_score(y_true, predictions, zero_division=0),
        'F2': fbeta_score(y_true, predictions, beta=2, zero_division=0),
        'Accuracy': accuracy_score(y_true, predictions),
        'Balanced accuracy': balanced_accuracy_score(y_true, predictions),
        'Brier': brier_score_loss(y_true, probabilities),
    }


def select_f2_threshold(y_true, probabilities):
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    p, r = precision[:-1], recall[:-1]
    scores = np.divide(5 * p * r, 4 * p + r, out=np.zeros_like(p), where=(4 * p + r) > 0)
    # При равном F2 выбираем больший порог. Все входы — исключительно validation.
    positions = np.flatnonzero(np.isclose(scores, scores.max(), rtol=0, atol=1e-12))
    best = positions[-1]
    table = pd.DataFrame({'Порог': thresholds, 'Precision': p, 'Recall': r, 'F2': scores})
    return float(thresholds[best]), table
