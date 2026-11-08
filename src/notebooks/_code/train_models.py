"""Небольшая фиксированная сетка; test здесь не используется."""
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

model_candidates = {
    'Dummy: prior': DummyClassifier(strategy='prior'),
    'Logistic: C=0.1': LogisticRegression(C=.1, max_iter=2000, random_state=42),
    'Logistic: C=1': LogisticRegression(C=1, max_iter=2000, random_state=42),
    'Logistic: balanced': LogisticRegression(C=1, class_weight='balanced', max_iter=2000, random_state=42),
    'Forest: leaf=2': RandomForestClassifier(n_estimators=200, min_samples_leaf=2, max_features='sqrt', n_jobs=1, random_state=42),
    'Forest: leaf=5 balanced': RandomForestClassifier(n_estimators=200, min_samples_leaf=5, max_features='sqrt', class_weight='balanced', n_jobs=1, random_state=42),
    'Boosting: leaves=15': HistGradientBoostingClassifier(max_iter=200, max_leaf_nodes=15, learning_rate=.1, l2_regularization=1, early_stopping=False, random_state=42),
    'Boosting: leaves=31': HistGradientBoostingClassifier(max_iter=200, max_leaf_nodes=31, learning_rate=.1, l2_regularization=1, early_stopping=False, random_state=42),
}
trained_models = {}
validation_probabilities = {}
comparison_records = []
for _name, _estimator in model_candidates.items():
    _pipeline = Pipeline([('preprocess', clone(preprocessor_template)), ('model', _estimator)])
    _pipeline.fit(X_train, y_train)
    _probability = _pipeline.predict_proba(X_validation)[:, 1]
    trained_models[_name] = _pipeline
    validation_probabilities[_name] = _probability
    comparison_records.append({'Модель': _name, **classification_metrics(y_validation, _probability)})

validation_comparison = pd.DataFrame(comparison_records).set_index('Модель').sort_values('AP', ascending=False, kind='stable')
selected_model_name = str(validation_comparison.index[0])
selected_pipeline = trained_models[selected_model_name]
selected_validation_probability = validation_probabilities[selected_model_name]
selected_threshold, threshold_curve = select_f2_threshold(y_validation, selected_validation_probability)
validation_threshold_comparison = pd.DataFrame([
    {'Правило': 'Порог 0.5', 'Порог': .5, **classification_metrics(y_validation, selected_validation_probability, .5)},
    {'Правило': 'Максимум F2 на validation', 'Порог': selected_threshold, **classification_metrics(y_validation, selected_validation_probability, selected_threshold)},
]).set_index('Правило')
# Зафиксированное решение. После этого fit больше не вызывается.
frozen_decision = {
    'model': selected_model_name, 'threshold': selected_threshold, 'selection_metric': 'validation AP',
    'fit_sample': 'train only', 'seed': 42, 'positive_class': 1,
}
display(validation_comparison.round(4))
display(validation_threshold_comparison.round(4))
display(Markdown(f'Выбрана **{selected_model_name}**; AP на validation = **{validation_comparison.iloc[0]["AP"]:.4f}**. Зафиксирован порог **{selected_threshold:.4f}**.'))

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
validation_comparison['AP'].sort_values().plot.barh(ax=axes[0], color='#4682a9')
axes[0].set(title='Выбор модели: только validation', xlabel='Average Precision', ylabel='')
axes[1].plot(threshold_curve['Порог'], threshold_curve['F2'], label='F2')
axes[1].plot(threshold_curve['Порог'], threshold_curve['Recall'], label='Полнота (Recall)', alpha=.7)
axes[1].plot(threshold_curve['Порог'], threshold_curve['Precision'], label='Точность (Precision)', alpha=.7)
axes[1].axvline(selected_threshold, color='black', linestyle='--', label='Выбранный порог')
axes[1].set(title='Выбор порога: только validation', xlabel='Порог', ylabel='Метрика', ylim=(0, 1.02))
axes[1].legend()
plt.tight_layout()
plt.show()
