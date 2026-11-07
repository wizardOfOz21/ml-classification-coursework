import numpy as np
from matplotlib.ticker import FuncFormatter

income = data['person_income']
income_q1, income_q3 = income.quantile([0.25, 0.75])
income_iqr = income_q3 - income_q1
income_lower = income_q1 - 1.5 * income_iqr
income_upper = income_q3 + 1.5 * income_iqr
income_outliers = (income < income_lower) | (income > income_upper)

income_stats = pd.concat([
    income.describe(),
    pd.Series({
        'Коэффициент асимметрии': income.skew(),
        'Верхняя граница по правилу 1,5 IQR': income_upper,
        'Записей за границами 1,5 IQR': int(income_outliers.sum()),
        'Доля записей за границами, %': 100 * income_outliers.mean(),
    }),
]).to_frame('Значение')
display(income_stats)

money_format = FuncFormatter(lambda value, _: f'{value:,.0f}'.replace(',', ' '))
fig = plt.figure(figsize=(13, 7), constrained_layout=True)
grid = fig.add_gridspec(2, 2, height_ratios=[3, 1])
income_axes = [fig.add_subplot(grid[0, 0]),
               fig.add_subplot(grid[0, 1]),
               fig.add_subplot(grid[1, :])]

sns.histplot(x=income, bins=50, color='#3977a8', ax=income_axes[0])
income_axes[0].set(title='Распределение годового дохода',
                   xlabel='Годовой доход', ylabel='Количество записей')
income_axes[0].xaxis.set_major_formatter(money_format)
income_axes[0].tick_params(axis='x', labelrotation=20)

log_bins = np.geomspace(income.min(), income.max(), 40)
sns.histplot(x=income, bins=log_bins, color='#3977a8', ax=income_axes[1])
income_axes[1].set_xscale('log')
income_axes[1].axvline(income.median(), color='#b34c32', linestyle='--',
                      label=f'Медиана: {income.median():,.0f}'.replace(',', ' '))
income_axes[1].set(title='Доход — логарифмическая шкала',
                   xlabel='Годовой доход, логарифмическая шкала', ylabel='Количество записей')
income_axes[1].xaxis.set_major_formatter(money_format)
income_axes[1].legend()

sns.boxplot(x=income, color='#91bad7', ax=income_axes[2])
income_axes[2].set(title='Доход — ящик с усами', xlabel='Годовой доход')
income_axes[2].xaxis.set_major_formatter(money_format)
plt.show()
