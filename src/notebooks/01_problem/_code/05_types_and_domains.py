# столбец считаем категориальным, если он нечисловой или у него мало различных значений
MAX_CATEGORIES = 10

def is_categorical(column):
    values = data[column]
    return not pd.api.types.is_numeric_dtype(values) or values.nunique() <= MAX_CATEGORIES


def domain(column):
    values = data[column].dropna()
    if is_categorical(column):
        return '{' + ', '.join(str(v) for v in sorted(values.unique())) + '}'
    return f'[{fmt_number(values.min())}, {fmt_number(values.max())}]'


columns_info = pd.DataFrame(index=data.columns)
columns_info['Тип в данных'] = data.dtypes.astype(str)
columns_info['Домен'] = columns_info.index.map(domain)

categorical = columns_info.index.map(is_categorical)
display(columns_info[~categorical].style.set_caption('Числовые столбцы'))
display(columns_info[categorical].style.set_caption('Категориальные столбцы'))