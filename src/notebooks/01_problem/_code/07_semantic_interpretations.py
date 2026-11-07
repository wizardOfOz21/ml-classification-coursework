# порядок категорий из данных не выводится — задаём вручную
ORDINAL_COLUMNS = {'loan_grade'}

def semantic_type(column):
    if not is_categorical(column):
        return 'числовой'
    if data[column].nunique() == 2:
        return 'бинарный'
    if column in ORDINAL_COLUMNS:
        return 'порядковый'
    return 'номинальный'


# уточнённые описания: единицы измерения, расшифровка значений
interpretations = {
    'person_age': 'возраст заёмщика, лет',
    'person_income': 'годовой доход',
    'person_home_ownership': 'жильё:\n'
                             '• RENT — снимает\n'
                             '• OWN — своё\n'
                             '• MORTGAGE — в ипотеке\n'
                             '• OTHER — другое',
    'person_emp_length': 'стаж на текущей работе, лет',
    'loan_intent': 'цель кредита:\n'
                   '• PERSONAL — личные нужды\n'
                   '• EDUCATION — образование\n'
                   '• MEDICAL — лечение\n'
                   '• VENTURE — бизнес\n'
                   '• HOMEIMPROVEMENT — ремонт жилья\n'
                   '• DEBTCONSOLIDATION — рефинансирование других долгов',
    'loan_grade': 'грейд займа от A (надёжный) до G (рискованный)',
    'loan_amnt': 'сумма кредита',
    'loan_int_rate': 'процентная ставка, % годовых',
    'loan_status': 'статус кредита:\n'
                   '• 0 — платит\n'
                   '• 1 — дефолт',
    'loan_percent_income': 'доля кредита от годового дохода',
    'cb_person_default_on_file': 'были ли дефолты раньше (по данным кредитного бюро):\n'
                                 '• Y — были\n'
                                 '• N — не было',
    'cb_person_cred_hist_length': 'длина кредитной истории, лет',
}

columns_info['Фактический тип'] = columns_info.index.map(semantic_type)
columns_info['Описание'] = columns_info.index.map(interpretations)
display(columns_info[['Описание из источника', 'Описание', 'Фактический тип']]
        .style.set_properties(**{'white-space': 'pre-line', 'text-align': 'left'}))