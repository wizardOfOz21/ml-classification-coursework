def prepare_applications(applications):
    'Проверка новых заявок; строки не удаляем, целевую переменную не принимаем'
    if not isinstance(applications, pd.DataFrame):
        raise TypeError('Ожидается DataFrame с признаками заявок')
    if not applications.columns.is_unique or set(applications.columns) != set(FEATURES):
        raise ValueError('Неверный набор столбцов: нужны ровно 11 признаков без loan_status')
    result = applications.loc[:, FEATURES].copy()
    for column in NUMERICAL_FEATURES:
        result[column] = pd.to_numeric(result[column], errors='raise').astype(float)
        if np.isinf(result[column]).any():
            raise ValueError(f'Бесконечное значение: {column}')
    if not result['loan_grade'].dropna().isin(GRADE_ORDER).all():
        raise ValueError('Неизвестная категория loan_grade: допустимы A–G или пропуск')
    # То же правило очистки стажа, что до разбиения; на инференсе не теряем строки.
    employment = result['person_emp_length']
    result.loc[(employment < 0) | (employment > 86), 'person_emp_length'] = np.nan
    invalid = (
        (result['person_age'] < 18) | (result['person_age'] > 100)
        | (result['person_income'] <= 0) | (result['loan_amnt'] <= 0)
        | (result['loan_int_rate'] <= 0)
        | (result['loan_percent_income'] < 0) | (result['loan_percent_income'] > 1)
        | (result['cb_person_cred_hist_length'] < 0)
    )
    if invalid.any():
        raise ValueError('Недопустимые числовые значения: исправьте заявку до прогноза')
    for column in NOMINAL_FEATURES + ORDINAL_FEATURES:
        result[column] = result[column].astype(object).where(result[column].notna(), np.nan)
    return result
