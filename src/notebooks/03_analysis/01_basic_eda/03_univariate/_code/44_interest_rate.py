rate = data['loan_int_rate'].dropna()
rate_q1, rate_q3 = rate.quantile([0.25, 0.75])
rate_iqr = rate_q3 - rate_q1
rate_lower = rate_q1 - 1.5 * rate_iqr
rate_upper = rate_q3 + 1.5 * rate_iqr
rate_outliers = (rate < rate_lower) | (rate > rate_upper)

rate_stats = pd.concat([
    rate.describe(),
    pd.Series({
        'Пропусков': data['loan_int_rate'].isna().sum(),
        'Коэффициент асимметрии': rate.skew(),
        'Верхняя граница по правилу 1,5 IQR': rate_upper,
        'Записей за границами 1,5 IQR': int(rate_outliers.sum()),
        'Доля записей за границами среди заполненных, %': 100 * rate_outliers.mean(),
    }),
]).to_frame('Значение')
display(rate_stats)

fig, axes = plt.subplots(1, 2, figsize=(13, 4), constrained_layout=True)
sns.histplot(x=rate, binwidth=0.25, color='#3977a8', ax=axes[0])
axes[0].axvline(rate.median(), color='#b34c32', linestyle='--',
               label=f'Медиана: {rate.median():g}')
axes[0].set(title='Распределение — процентная ставка', xlabel='Процентная ставка, % годовых', ylabel='Количество записей')
axes[0].legend()
sns.boxplot(x=rate, color='#91bad7', ax=axes[1])
axes[1].set(title='Процентная ставка — ящик с усами', xlabel='Процентная ставка, % годовых')
plt.show()
