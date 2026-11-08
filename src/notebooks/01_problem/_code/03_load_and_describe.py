import pandas as pd

# убираем незначащие нули
pd.set_option('display.float_format',
              lambda x: f'{x:.6f}'.rstrip('0').rstrip('.'))
# не обрезаем длинный текст в ячейках таблиц
pd.set_option('display.max_colwidth', None)


def fmt_number(x):
    return f'{x:.6f}'.rstrip('0').rstrip('.')


data_raw = pd.read_csv('./dataset/credit_risk_dataset.csv')
data = data_raw.copy()
