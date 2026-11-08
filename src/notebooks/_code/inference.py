'Локальное применение готового решения, без fit и истинных меток новых заявок'

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
    'Оставили все 11 признаков Числовые пропуски заполнили медианами train и отметили отдельными столбцами, категориальные — самым частым значением; грейды закодировали по порядку A–G',
    'Применять ту же цепочку обработки к новым заявкам Редкие высокие доходы не удалять')
update_conclusion('model_selection',
    f'На validation из {len(validation_comparison)} заранее заданных кандидатов выбран {selected_model_name}; AP = {validation_comparison.iloc[0]["AP"]:.4f}',
    'Сравнили только эти варианты на одном разбиении Другие модели или настройки могут оказаться лучше')
update_conclusion('threshold',
    f'Порог {selected_threshold:.4f} выбран по F2 только на validation; на test Recall = {test_metrics.iloc[1]["Recall"]:.4f}, Precision = {test_metrics.iloc[1]["Precision"]:.4f}',
    'При выборе порога отдаём приоритет поиску дефолтов Для практики нужно учесть стоимость ошибок и проверить порог на новых данных')
update_conclusion('test_result',
    f'Test: AP = {test_metrics.iloc[1]["AP"]:.4f}, ROC-AUC = {test_metrics.iloc[1]["ROC-AUC"]:.4f}, F2 = {test_metrics.iloc[1]["F2"]:.4f}; пропусков дефолта {fn}, ложных тревог {fp}',
    'После этой оценки модель не меняем Разброс метрик показан в этапе 6')
update_conclusion('uncertainty',
    'Bootstrap показывает разброс метрик для готовой модели на этом test Новое обучение и данные другого банка он не учитывает',
    'Не знаем время заявок и повторы клиентов; проверки на внешних данных нет Работа в других условиях ещё не проверена')
update_conclusion('deployment',
    'Можно передать сразу несколько заявок и получить для каждой риск и класс Неверный набор полей вызывает ошибку; новая номинальная категория даёт нули в своих столбцах one-hot',
    'Перед применением нужно проверить доступность полей, калибровку и качество на новых данных и в разных группах Прогноз сам по себе не является решением об отказе')

# Консолидируем повторяющиеся решения: подробные факты остаются в EDA.
for _key in list(conclusions):
    _finding = conclusions[_key]['Выводы']
    if _key.startswith('eda_') and (
        _finding.startswith('В person_emp_length')
        or _finding.startswith('Числовые признаки имеют')
    ):
        del conclusions[_key]
conclusions['preprocessing']['Выводы'] += (
    ' В исходных данных пропуски стажа — 2,75%, ставки — 9,56%; масштабы числовых признаков различаются'
)
# Проверка нелинейной модели завершена; прошлое решение больше не оставляем будущим действием.
conclusions['income_amount']['Решения'] = (
    'Сравнили более гибкие модели на validation; выбрали бустинг '
    'По этому сравнению нельзя выделить отдельный вклад суммы или дохода и установить причину связи'
)
# Устаревшие решения заменены по ключам, закрытые гипотезы в финале не повторяются.
final_conclusions = pd.DataFrame(conclusions.values())
display(final_conclusions.style.set_properties(**{'text-align': 'left', 'white-space': 'normal'}).hide(axis='index'))
