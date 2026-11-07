import matplotlib.pyplot as plt
import seaborn as sns

age = data['person_age']
q1, q3 = age.quantile([0.25, 0.75])
iqr = q3 - q1
lower_fence = q1 - 1.5 * iqr
upper_fence = q3 + 1.5 * iqr
age_outliers = (age < lower_fence) | (age > upper_fence)

age_stats = pd.concat([
    age.describe(),
    pd.Series({
        'Коэффициент асимметрии': age.skew(),
        'Верхняя граница по правилу 1,5 IQR': upper_fence,
        'Записей за границами 1,5 IQR': int(age_outliers.sum()),
        'Доля записей за границами, %': 100 * age_outliers.mean(),
    }),
]).to_frame('Значение')
display(age_stats)

fig, axes = plt.subplots(1, 2, figsize=(13, 4), constrained_layout=True)
sns.histplot(x=age, discrete=True, color='#3977a8', ax=axes[0])
axes[0].axvline(age.median(), color='#b34c32', linestyle='--',
               label=f'Медиана: {age.median():g}')
axes[0].set(title='Распределение возраста', xlabel='Возраст, лет', ylabel='Количество записей')
axes[0].legend()

sns.boxplot(x=age, color='#91bad7', ax=axes[1])
axes[1].set(title='Возраст — ящик с усами', xlabel='Возраст, лет')
plt.show()
