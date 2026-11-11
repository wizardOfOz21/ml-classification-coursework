final_conclusions = pd.DataFrame([
    ('Модель', f'{selected_model_name}: обучена на train и выбрана по AP на validation ({validation_comparison.iloc[0]["AP"]:.4f})'),
    ('Входы', '9 признаков заявки. loan_grade и loan_percent_income исключены; процентная ставка должна быть известна до прогноза'),
    ('Обработка', 'Числовые пропуски заполняются медианами train с индикаторами пропусков, затем применяется RobustScaler. Категориальные пропуски заполняются модами train, категории кодируются one-hot'),
    ('Порог', f'{selected_threshold:.4f}, выбран по F2 на validation с приоритетом обнаружения дефолтов'),
    ('Качество на test', f'AP = {test_metrics.iloc[1]["AP"]:.4f}, ROC-AUC = {test_metrics.iloc[1]["ROC-AUC"]:.4f}, Precision = {test_metrics.iloc[1]["Precision"]:.4f}, Recall = {test_metrics.iloc[1]["Recall"]:.4f}, F2 = {test_metrics.iloc[1]["F2"]:.4f}. Пропущено дефолтов: {fn}; ложных тревог: {fp}'),
    ('Применение', 'Для каждой новой заявки модель выдаёт оценку риска и класс по выбранному порогу. Используем ту же обработку, что при обучении'),
    ('Ограничения', 'Качество оценено на одном разбиении. Перед практическим применением нужны проверка на новых данных и оценка стоимости ошибок'),
], columns=['Аспект', 'Вывод']).set_index('Аспект')
display(final_conclusions)
