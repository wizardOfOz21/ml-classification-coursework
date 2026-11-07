import pandas as pd

# убираем незначащие нули
pd.set_option('display.float_format',
              lambda x: f'{x:.6f}'.rstrip('0').rstrip('.'))
# не обрезаем длинный текст в ячейках таблиц
pd.set_option('display.max_colwidth', None)


def fmt_number(x):
    return f'{x:.6f}'.rstrip('0').rstrip('.')


# описания столбцов от автора датасета
source_descriptions = {
    'person_age': 'Age',
    'person_income': 'Annual Income',
    'person_home_ownership': 'Home ownership',
    'person_emp_length': 'Employment length (in years)',
    'loan_intent': 'Loan intent',
    'loan_grade': 'Loan grade',
    'loan_amnt': 'Loan amount',
    'loan_int_rate': 'Interest rate',
    'loan_status': 'Loan status (0 is non default 1 is default)',
    'loan_percent_income': 'Percent income',
    'cb_person_default_on_file': 'Historical default',
    'cb_person_cred_hist_length': 'Credit history length',
}

data_raw = pd.read_csv('./dataset/credit_risk_dataset.csv')
data = data_raw.copy()

display(pd.Series(source_descriptions, name='Описание из источника').to_frame())