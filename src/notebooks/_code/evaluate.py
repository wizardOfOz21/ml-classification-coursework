"""Одна итоговая оценка зафиксированного решения на test."""
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix, roc_curve
from sklearn.calibration import calibration_curve

X_test = test.loc[:, FEATURES].copy()
y_test = test['loan_status'].astype(int).copy()
test_probability = selected_pipeline.predict_proba(X_test)[:, 1]
test_prediction = (test_probability >= selected_threshold).astype(int)
dummy_test_probability = trained_models['Dummy: prior'].predict_proba(X_test)[:, 1]
test_metrics = pd.DataFrame([
    {'Решение': 'Dummy, порог 0.5', **classification_metrics(y_test, dummy_test_probability)},
    {'Решение': f'{selected_model_name}, порог validation', **classification_metrics(y_test, test_probability, selected_threshold)},
]).set_index('Решение')
test_confusion = confusion_matrix(y_test, test_prediction, labels=[0, 1])
tn, fp, fn, tp = test_confusion.ravel().tolist()
display(test_metrics.round(4))
display(pd.DataFrame(test_confusion, index=['Факт: без дефолта', 'Факт: дефолт'], columns=['Прогноз: без дефолта', 'Прогноз: дефолт']))

# Стратифицированный bootstrap уже готовых прогнозов: модель/порог не меняются.
_bootstrap_rng = np.random.default_rng(42)
_bootstrap_y = y_test.to_numpy()
_negative_indices = np.flatnonzero(_bootstrap_y == 0)
_positive_indices = np.flatnonzero(_bootstrap_y == 1)
_bootstrap_metrics = []
for _ in range(300):
    _indices = np.concatenate([
        _bootstrap_rng.choice(_negative_indices, len(_negative_indices), replace=True),
        _bootstrap_rng.choice(_positive_indices, len(_positive_indices), replace=True),
    ])
    _bootstrap_metrics.append(classification_metrics(_bootstrap_y[_indices], test_probability[_indices], selected_threshold))
bootstrap_metrics = pd.DataFrame(_bootstrap_metrics)
metric_intervals = pd.DataFrame({
    'Оценка': test_metrics.iloc[1],
    'Нижняя 95%': bootstrap_metrics.quantile(.025),
    'Верхняя 95%': bootstrap_metrics.quantile(.975),
})
display(metric_intervals.round(4))

fig, axes = plt.subplots(2, 2, figsize=(13, 10))
_fpr, _tpr, _ = roc_curve(y_test, test_probability)
axes[0, 0].plot(_fpr, _tpr, label=f'ROC-AUC = {test_metrics.iloc[1]["ROC-AUC"]:.3f}')
axes[0, 0].plot([0, 1], [0, 1], '--', color='grey')
axes[0, 0].set(title='ROC: test', xlabel='False Positive Rate', ylabel='True Positive Rate')
axes[0, 0].legend()
_precision, _recall, _ = precision_recall_curve(y_test, test_probability)
axes[0, 1].plot(_recall, _precision, label=f'AP = {test_metrics.iloc[1]["AP"]:.3f}')
axes[0, 1].axhline(y_test.mean(), linestyle='--', color='grey', label='Доля дефолтов test')
axes[0, 1].set(title='Precision–Recall: test', xlabel='Recall', ylabel='Precision')
axes[0, 1].legend()
ConfusionMatrixDisplay(test_confusion, display_labels=['Без дефолта', 'Дефолт']).plot(ax=axes[1, 0], colorbar=False, cmap='Blues')
axes[1, 0].set(title='Матрица ошибок: выбранный порог', xlabel='Прогноз', ylabel='Факт')
_observed, _predicted = calibration_curve(y_test, test_probability, n_bins=8, strategy='quantile')
axes[1, 1].plot(_predicted, _observed, 'o-', label='Модель')
axes[1, 1].plot([0, 1], [0, 1], '--', color='grey', label='Идеальная калибровка')
axes[1, 1].set(title='Диагностика калибровки: test', xlabel='Средний прогноз', ylabel='Наблюдаемая доля дефолтов')
axes[1, 1].legend()
plt.tight_layout()
plt.show()

display(Markdown(
    f'На test ({len(test):,} записей) AP = **{test_metrics.iloc[1]["AP"]:.4f}**, '
    f'ROC-AUC = **{test_metrics.iloc[1]["ROC-AUC"]:.4f}**. '
    f'При зафиксированном пороге обнаружено **{tp} из {tp + fn}** дефолтов; '
    f'пропущено **{fn}**, ложных тревог — **{fp}** из {tn + fp} кредитов без дефолта. '
    'После просмотра test решение не перенастраиваем.'
))
