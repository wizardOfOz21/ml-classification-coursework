"""Описательные проверки оставшихся гипотез — исключительно train."""
from IPython.display import Markdown

analysis_train = train.copy()
analysis_train['grade_ordered'] = pd.Categorical(analysis_train['loan_grade'], categories=list('ABCDEFG'), ordered=True)
analysis_train['income_quartile'] = pd.qcut(analysis_train['person_income'], 4, duplicates='drop')
analysis_train['amount_quartile'] = pd.qcut(analysis_train['loan_amnt'], 4, duplicates='drop')
analysis_train['age_band'] = pd.cut(analysis_train['person_age'], [18, 25, 35, 50, 100], include_lowest=True)
analysis_train['history_band'] = pd.cut(analysis_train['cb_person_cred_hist_length'], [0, 5, 10, 15, 20, 40], include_lowest=True)
analysis_train['file_block'] = pd.cut(analysis_train.index, [0, 8000, 16000, 24000, len(data_raw)], include_lowest=True)


def default_summary(frame, groups):
    return frame.groupby(groups, observed=True)['loan_status'].agg(n='size', defaults='sum', default_rate='mean')


grade_summary = analysis_train.groupby('grade_ordered', observed=True).agg(
    n=('loan_status', 'size'), default_rate=('loan_status', 'mean'),
    rate_n=('loan_int_rate', 'count'), rate_median=('loan_int_rate', 'median'),
    rate_q25=('loan_int_rate', lambda s: s.quantile(.25)),
    rate_q75=('loan_int_rate', lambda s: s.quantile(.75)),
)
ratio_error = (analysis_train['loan_percent_income'] - analysis_train['loan_amnt'] / analysis_train['person_income']).abs()
ratio_summary = pd.DataFrame({
    'Наблюдений': [len(analysis_train)],
    'Расхождений > 0,005': [int((ratio_error > .005 + 1e-9).sum())],
    'Медиана абсолютного расхождения': [ratio_error.median()],
    'Максимальное расхождение': [ratio_error.max()],
})
interaction_summary = default_summary(analysis_train, ['grade_ordered', 'cb_person_default_on_file'])
amount_income_summary = default_summary(analysis_train, ['income_quartile', 'amount_quartile'])
age_history_summary = default_summary(analysis_train, ['age_band', 'history_band'])
age_grade_history_summary = default_summary(analysis_train, ['age_band', 'grade_ordered', 'history_band'])
conditional_history_checks = (age_grade_history_summary.loc[age_grade_history_summary['n'] >= 30]
    .groupby(['age_band', 'grade_ordered'], observed=True)
    .agg(history_groups=('n', 'size'), min_cell_n=('n', 'min'),
         min_default_rate=('default_rate', 'min'), max_default_rate=('default_rate', 'max')))
# Внутри каждого грейда — свои терцили ставки: масштабы между грейдами не смешиваем.
analysis_train['rate_within_grade'] = analysis_train.groupby('grade_ordered', observed=True)['loan_int_rate'].transform(
    lambda s: pd.qcut(s, 3, labels=False, duplicates='drop')
)
within_grade_rate_summary = default_summary(analysis_train.dropna(subset=['rate_within_grade']), ['grade_ordered', 'rate_within_grade'])
income_95 = float(analysis_train['person_income'].quantile(.95))
high_income_summary = default_summary(analysis_train.assign(high_income=analysis_train['person_income'] > income_95), ['high_income'])
file_summary = analysis_train.groupby('file_block', observed=True).agg(
    n=('loan_status', 'size'), age_median=('person_age', 'median'),
    history_median=('cb_person_cred_hist_length', 'median'), income_median=('person_income', 'median'),
    grade_A_share=('loan_grade', lambda s: s.eq('A').mean()),
    rate_missing=('loan_int_rate', lambda s: s.isna().mean()),
)

for _title, _table in [
    ('Грейд, распределение ставки и частота дефолта на train', grade_summary),
    ('Проверка формулы доли кредита на train', ratio_summary),
    ('Прошлый дефолт внутри грейдов: сколько записей и какая доля дефолтов', interaction_summary),
    ('Сумма и доход: сравнение четырёх групп', amount_income_summary),
    ('Кредитная история внутри возрастных диапазонов', age_history_summary),
    ('История при похожем возрасте и грейде: группы от 30 записей', conditional_history_checks),
    ('Ставка внутри грейда: три группы от низкой к высокой', within_grade_rate_summary),
    (f'Высокие доходы: граница 95-го процентиля train = {income_95:,.0f}', high_income_summary),
    ('Исходный порядок строк: последовательные блоки файла, только записи train', file_summary),
]:
    display(Markdown('##### ' + _title))
    display(_table.round(4).rename(columns={
        'n': 'Записей', 'defaults': 'Дефолтов', 'default_rate': 'Доля дефолтов',
        'rate_n': 'Известных ставок', 'rate_median': 'Медиана ставки',
        'rate_q25': 'Ставка: 25%', 'rate_q75': 'Ставка: 75%',
        'history_groups': 'Групп по длине истории', 'min_cell_n': 'Минимум записей в группе',
        'min_default_rate': 'Наименьшая доля дефолтов', 'max_default_rate': 'Наибольшая доля дефолтов',
        'age_median': 'Медиана возраста', 'history_median': 'Медиана длины истории',
        'income_median': 'Медиана дохода', 'grade_A_share': 'Доля грейда A',
        'rate_missing': 'Доля пропусков ставки',
    }))

fig, axes = plt.subplots(1, 2, figsize=(15, 5))
sns.boxplot(data=analysis_train, x='grade_ordered', y='loan_int_rate', ax=axes[0], color='#78a6c8', showfliers=False)
axes[0].set(title='Ставка по грейду (train)', xlabel='Грейд A–G', ylabel='Процентная ставка, %')
age_history_counts = pd.crosstab(analysis_train['cb_person_cred_hist_length'], analysis_train['person_age'])
sns.heatmap(np.log1p(age_history_counts), cmap='Blues', ax=axes[1], cbar_kws={'label': 'log(1 + число наблюдений)'})
axes[1].set(title='Возраст и кредитная история (train)', xlabel='Возраст', ylabel='Длина кредитной истории')
plt.tight_layout()
plt.show()
