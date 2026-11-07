income_share = data['loan_percent_income'].dropna()
income_share_q1, income_share_q3 = income_share.quantile([0.25, 0.75])
income_share_iqr = income_share_q3 - income_share_q1
income_share_lower = income_share_q1 - 1.5 * income_share_iqr
income_share_upper = income_share_q3 + 1.5 * income_share_iqr
income_share_outliers = (income_share < income_share_lower) | (income_share > income_share_upper)

income_share_stats = pd.concat([
    income_share.describe(),
    pd.Series({
        'Коэффициент асимметрии': income_share.skew(),
        'Верхняя граница по правилу 1,5 IQR': income_share_upper,
        'Записей за границами 1,5 IQR': int(income_share_outliers.sum()),
        'Доля записей за границами, %': 100 * income_share_outliers.mean(),
    }),
]).to_frame('Значение')
display(income_share_stats)

fig, axes = plt.subplots(1, 2, figsize=(13, 4), constrained_layout=True)
sns.histplot(x=income_share, binwidth=0.01, color='#3977a8', ax=axes[0])
axes[0].axvline(income_share.median(), color='#b34c32', linestyle='--',
               label=f'Медиана: {income_share.median():g}')
axes[0].set(title='Распределение — доля суммы кредита от дохода', xlabel='Доля суммы кредита от годового дохода, %', ylabel='Количество записей')
axes[0].legend()
sns.boxplot(x=income_share, color='#91bad7', ax=axes[1])
axes[1].set(title='Доля суммы кредита от дохода — ящик с усами', xlabel='Доля суммы кредита от годового дохода, %')
from matplotlib.ticker import PercentFormatter
for ax in axes:
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1))
plt.show()
