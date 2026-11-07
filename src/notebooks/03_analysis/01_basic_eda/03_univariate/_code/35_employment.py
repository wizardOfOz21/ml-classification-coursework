employment = data['person_emp_length'].dropna()
employment_q1, employment_q3 = employment.quantile([0.25, 0.75])
employment_iqr = employment_q3 - employment_q1
employment_lower = employment_q1 - 1.5 * employment_iqr
employment_upper = employment_q3 + 1.5 * employment_iqr
employment_outliers = (employment < employment_lower) | (employment > employment_upper)

employment_stats = pd.concat([
    employment.describe(),
    pd.Series({
        'Пропусков': data['person_emp_length'].isna().sum(),
        'Коэффициент асимметрии': employment.skew(),
        'Верхняя граница по правилу 1,5 IQR': employment_upper,
        'Записей за границами 1,5 IQR': int(employment_outliers.sum()),
        'Доля записей за границами среди заполненных, %': 100 * employment_outliers.mean(),
    }),
]).to_frame('Значение')
display(employment_stats)

fig, axes = plt.subplots(1, 2, figsize=(13, 4), constrained_layout=True)
sns.histplot(x=employment, discrete=True, color='#3977a8', ax=axes[0])
axes[0].axvline(employment.median(), color='#b34c32', linestyle='--',
               label=f'Медиана: {employment.median():g}')
axes[0].set(title='Распределение стажа', xlabel='Стаж, лет', ylabel='Количество записей')
axes[0].legend()
sns.boxplot(x=employment, color='#91bad7', ax=axes[1])
axes[1].set(title='Стаж — ящик с усами', xlabel='Стаж, лет')
plt.show()
