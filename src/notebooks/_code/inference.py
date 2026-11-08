"""Локальное применение готового решения, без fit и истинных меток новых заявок."""

def predict_applications(applications, pipeline, threshold):
    prepared = prepare_applications(applications)
    scores = pipeline.predict_proba(prepared)[:, 1]
    return pd.DataFrame({
        'Оценка риска дефолта': scores,
        'Класс при выбранном пороге': (scores >= threshold).astype(int),
    }, index=applications.index)


new_applications = pd.DataFrame([
    [28, 65000, 4, 9000, 10.8, .14, 6, 'RENT', 'EDUCATION', 'N', 'B'],
    [42, 38000, 8, 16000, 17.5, .42, 12, 'MORTGAGE', 'DEBTCONSOLIDATION', 'Y', 'E'],
    [31, 92000, np.nan, 5000, np.nan, .05, 8, 'OWN', 'PERSONAL', 'N', 'A'],
], columns=FEATURES, index=['Заявка 1', 'Заявка 2', 'Заявка 3'])
example_predictions = predict_applications(new_applications, selected_pipeline, selected_threshold)
display(new_applications)
display(example_predictions.round(4))

monitoring_reference = pd.DataFrame({
    'Доля пропусков train': X_train.isna().mean(),
    'Доля пропусков примера': new_applications.isna().mean(),
})
display(monitoring_reference.round(4))

def update_conclusion(key, finding, decision):
    conclusions[key] = {'Выводы': finding, 'Решения': decision}


update_conclusion('preprocessing',
    'Все 11 признаков сохранены; числовые пропуски заполнены медианами train с индикаторами, номинальные — модой, грейд — порядком A–G.',
    'Использовать единый Pipeline; RobustScaler для числовых и one-hot для номинальных. Верхние доходы не обрезать.')
update_conclusion('model_selection',
    f'На validation из {len(validation_comparison)} заранее заданных кандидатов выбран {selected_model_name}; AP = {validation_comparison.iloc[0]["AP"]:.4f}.',
    'Выбор ограничен этой сеткой и одним разбиением; он не доказывает глобальную оптимальность модели.')
update_conclusion('threshold',
    f'Порог {selected_threshold:.4f} выбран по F2 только на validation; на test Recall = {test_metrics.iloc[1]["Recall"]:.4f}, Precision = {test_metrics.iloc[1]["Precision"]:.4f}.',
    'Учебное предпочтение полноты. Для практики нужны стоимости ошибок и пересмотр порога на новых validation-данных.')
update_conclusion('test_result',
    f'Test: AP = {test_metrics.iloc[1]["AP"]:.4f}, ROC-AUC = {test_metrics.iloc[1]["ROC-AUC"]:.4f}, F2 = {test_metrics.iloc[1]["F2"]:.4f}; пропусков дефолта {fn}, ложных тревог {fp}.',
    'Итоговая оценка зафиксирована; не использовать test для нового подбора. Интервалы приведены в этапе 6.')
update_conclusion('uncertainty',
    'Bootstrap оценивает вариацию метрик фиксированной модели на этом test, а не разброс переобучения и не перенос на другой банк.',
    'Нет временных меток, идентификаторов клиентов и внешнего набора: независимость клиентов и переносимость не установлены.')
update_conclusion('deployment',
    'Локальный пакетный прогноз реализован; неполные/неверные схемы отклоняются, новые номинальные категории кодируются нулями.',
    'Перед реальной эксплуатацией: проверка доступности полей, калибровки, стабильности и качества по группам. Это не автоматический кредитный отказ.')

# Консолидируем повторяющиеся решения: подробные факты остаются в EDA.
for _key in list(conclusions):
    _finding = conclusions[_key]['Выводы']
    if _key.startswith('eda_') and (
        _finding.startswith('В person_emp_length')
        or _finding.startswith('Числовые признаки имеют')
    ):
        del conclusions[_key]
conclusions['preprocessing']['Выводы'] += (
    ' В исходных данных пропуски стажа — 2,75%, ставки — 9,56%; масштабы числовых признаков различаются.'
)
# Проверка нелинейной модели завершена; прошлое решение больше не оставляем будущим действием.
conclusions['income_amount']['Решения'] = (
    'Нелинейные модели сравнены на validation; победил бустинг. '
    'Это не выделяет отдельный эффект суммы/дохода и не доказывает причинность.'
)
# Устаревшие решения заменены по ключам, закрытые гипотезы в финале не повторяются.
final_conclusions = pd.DataFrame(conclusions.values())
display(final_conclusions.style.set_properties(**{'text-align': 'left', 'white-space': 'normal'}).hide(axis='index'))
