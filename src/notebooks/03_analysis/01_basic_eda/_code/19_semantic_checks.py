ratio_expected = data['loan_amnt'] / data['person_income']
ratio_difference = (data['loan_percent_income'] - ratio_expected).abs()

checks = {
    'Целочисленность возраста': (
        ['person_age'], data['person_age'] % 1 != 0),
    'Целочисленность стажа': (
        ['person_emp_length'], data['person_emp_length'] % 1 != 0),
    'Целочисленность кредитной истории': (
        ['cb_person_cred_hist_length'], data['cb_person_cred_hist_length'] % 1 != 0),
    'Возраст ≤ 100': (
        ['person_age'], data['person_age'] > 100),
    'Стаж ≤ 86': (
        ['person_emp_length'], data['person_emp_length'] > 86),
    'Стаж ≤ возраст − 14': (
        ['person_age', 'person_emp_length'],
        data['person_emp_length'] > data['person_age'] - 14),
    'Кредитная история ≤ возраст − 16': (
        ['person_age', 'cb_person_cred_hist_length'],
        data['cb_person_cred_hist_length'] > data['person_age'] - 16),
    'Доля кредита соответствует сумме / доходу (погрешность ≤ 0,005)': (
        ['loan_percent_income', 'loan_amnt', 'person_income'],
        ratio_difference > 0.005 + 1e-9),
}

constraint_results = []
constraint_violations = pd.DataFrame(index=data.index)
for name, (columns, violation) in checks.items():
    available = data[columns].notna().all(axis=1)
    # Согласованность проверяем только при допустимом абсолютном стаже.
    if name == 'Стаж ≤ возраст − 14':
        available &= data['person_emp_length'] <= 86
    if 'person_income' in columns:
        available &= data['person_income'] > 0
    constraint_violations[name] = available & violation
    constraint_results.append({
        'Проверка': name,
        'Проверено': int(available.sum()),
        'Не проверено': int((~available).sum()),
        'Нарушений': int(constraint_violations[name].sum()),
    })

display(pd.DataFrame(constraint_results).set_index('Проверка').rename_axis(None))
