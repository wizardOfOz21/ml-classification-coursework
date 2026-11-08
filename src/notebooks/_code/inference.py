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

_final_updates = [
    ('preprocessing', 'Оставили все 11 признаков Числовые пропуски заполнили медианами train и отметили отдельными столбцами, категориальные — самым частым значением; грейды закодировали по порядку A–G' + ' В исходных данных пропуски стажа — 2,75%, ставки — 9,56%; масштабы числовых признаков различаются', 'Применять ту же цепочку обработки к новым заявкам Редкие высокие доходы не удалять'),
    ('model_selection', f"На validation из {len(validation_comparison)} заранее заданных кандидатов выбран {selected_model_name}; AP = {validation_comparison.iloc[0]['AP']:.4f}", 'Сравнили только эти варианты на одном разбиении Другие модели или настройки могут оказаться лучше'),
    ('threshold', f"Порог {selected_threshold:.4f} выбран по F2 только на validation; на test Recall = {test_metrics.iloc[1]['Recall']:.4f}, Precision = {test_metrics.iloc[1]['Precision']:.4f}", 'При выборе порога отдаём приоритет поиску дефолтов Для практики нужно учесть стоимость ошибок и проверить порог на новых данных'),
    ('test_result', f"Test: AP = {test_metrics.iloc[1]['AP']:.4f}, ROC-AUC = {test_metrics.iloc[1]['ROC-AUC']:.4f}, F2 = {test_metrics.iloc[1]['F2']:.4f}; пропусков дефолта {fn}, ложных тревог {fp}", 'После этой оценки модель не меняем Разброс метрик показан в этапе 6'),
    ('uncertainty', 'Bootstrap показывает разброс метрик для готовой модели на этом test Новое обучение и данные другого банка он не учитывает', 'Не знаем время заявок и повторы клиентов; проверки на внешних данных нет Работа в других условиях ещё не проверена'),
    ('deployment', 'Можно передать сразу несколько заявок и получить для каждой риск и класс Неверный набор полей вызывает ошибку; новая номинальная категория даёт нули в своих столбцах one-hot', 'Перед применением нужно проверить доступность полей, калибровку и качество на новых данных и в разных группах Прогноз сам по себе не является решением об отказе'),
]
_final_updates.extend([
    ('f01', f'Исходно {len(data_raw)} записей, 11 признаков и loan_status После удаления повторов и недопустимого возраста — {len(data)} записей',
     'Сохраняем правила очистки и разбиение 70/15/15'),
    ('f33', conclusions.loc['f33', 'Выводы'],
     'Сравнили более гибкие модели на validation; выбрали бустинг По этому сравнению нельзя выделить отдельный вклад суммы или дохода и установить причину связи'),
])
conclusions = update_findings(conclusions, _final_updates, remove=['f03', 'f06', 'f26'])
# Для итоговой таблицы оставляем только актуальные версии без подсветки изменений
conclusions = update_findings(conclusions)
final_conclusions = active_findings(conclusions)
display(findings_view(conclusions))
