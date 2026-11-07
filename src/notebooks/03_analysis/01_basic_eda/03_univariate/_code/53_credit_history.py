credit_history = data['cb_person_cred_hist_length'].dropna()
credit_history_q1, credit_history_q3 = credit_history.quantile([0.25, 0.75])
credit_history_iqr = credit_history_q3 - credit_history_q1
credit_history_lower = credit_history_q1 - 1.5 * credit_history_iqr
credit_history_upper = credit_history_q3 + 1.5 * credit_history_iqr
credit_history_outliers = (credit_history < credit_history_lower) | (credit_history > credit_history_upper)

credit_history_stats = pd.concat([
    credit_history.describe(),
    pd.Series({
        'Коэффициент асимметрии': credit_history.skew(),
        'Верхняя граница по правилу 1,5 IQR': credit_history_upper,
        'Записей за границами 1,5 IQR': int(credit_history_outliers.sum()),
        'Доля записей за границами, %': 100 * credit_history_outliers.mean(),
    }),
]).to_frame('Значение')
display(credit_history_stats)

fig, axes = plt.subplots(1, 2, figsize=(13, 4), constrained_layout=True)
sns.histplot(x=credit_history, discrete=True, color='#3977a8', ax=axes[0])
axes[0].axvline(credit_history.median(), color='#b34c32', linestyle='--',
               label=f'Медиана: {credit_history.median():g}')
axes[0].set(title='Распределение — длина кредитной истории', xlabel='Длина кредитной истории, лет', ylabel='Количество записей')
axes[0].legend()
sns.boxplot(x=credit_history, color='#91bad7', ax=axes[1])
axes[1].set(title='Длина кредитной истории — ящик с усами', xlabel='Длина кредитной истории, лет')
plt.show()
