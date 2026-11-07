amount = data['loan_amnt'].dropna()
amount_q1, amount_q3 = amount.quantile([0.25, 0.75])
amount_iqr = amount_q3 - amount_q1
amount_lower = amount_q1 - 1.5 * amount_iqr
amount_upper = amount_q3 + 1.5 * amount_iqr
amount_outliers = (amount < amount_lower) | (amount > amount_upper)

amount_stats = pd.concat([
    amount.describe(),
    pd.Series({
        'Пропусков': data['loan_amnt'].isna().sum(),
        'Коэффициент асимметрии': amount.skew(),
        'Верхняя граница по правилу 1,5 IQR': amount_upper,
        'Записей за границами 1,5 IQR': int(amount_outliers.sum()),
        'Доля записей за границами среди заполненных, %': 100 * amount_outliers.mean(),
    }),
]).to_frame('Значение')
display(amount_stats)

fig, axes = plt.subplots(1, 2, figsize=(13, 4), constrained_layout=True)
sns.histplot(x=amount, binwidth=500, color='#3977a8', ax=axes[0])
axes[0].axvline(amount.median(), color='#b34c32', linestyle='--',
               label=f'Медиана: {amount.median():g}')
axes[0].set(title='Распределение — сумма кредита', xlabel='Сумма кредита', ylabel='Количество записей')
axes[0].legend()
sns.boxplot(x=amount, color='#91bad7', ax=axes[1])
axes[1].set(title='Сумма кредита — ящик с усами', xlabel='Сумма кредита')
for ax in axes:
    ax.xaxis.set_major_formatter(money_format)
plt.show()
