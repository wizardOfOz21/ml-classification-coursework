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


columns_info['Фактический тип'] = columns_info.index.map(semantic_type)
