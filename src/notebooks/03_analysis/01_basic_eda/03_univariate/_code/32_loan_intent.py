intent_counts = data['loan_intent'].value_counts()
intent_table = pd.DataFrame({
    'Количество': intent_counts,
    'Доля, %': 100 * intent_counts / len(data),
})
display(intent_table)

intent_labels = {
    'EDUCATION': 'Образование',
    'MEDICAL': 'Лечение',
    'VENTURE': 'Бизнес',
    'PERSONAL': 'Личные нужды',
    'DEBTCONSOLIDATION': 'Рефинансирование долгов',
    'HOMEIMPROVEMENT': 'Ремонт жилья',
}
intent_names = [intent_labels[category] for category in intent_table.index]
intent_colors = sns.color_palette('Set2', len(intent_table))
fig, axes = plt.subplots(1, 2, figsize=(15, 5), constrained_layout=True)
bars = axes[0].barh(intent_names, intent_table['Доля, %'], color=intent_colors)
axes[0].invert_yaxis()
axes[0].bar_label(bars, labels=[
    f'{count:,} ({share:.2f} %)'.replace(',', ' ')
    for count, share in zip(intent_table['Количество'], intent_table['Доля, %'])
], padding=5, fontsize=9)
axes[0].set(title='Распределение по цели кредита',
            xlabel='Доля записей, %', ylabel='Цель кредита')
axes[0].set_xlim(0, intent_table['Доля, %'].max() * 1.45)

wedges, _, _ = axes[1].pie(intent_counts, colors=intent_colors, startangle=90,
                          autopct=lambda share: f'{share:.2f} %',
                          pctdistance=0.72, wedgeprops={'edgecolor': 'white'})
axes[1].legend(wedges, intent_names, loc='center left',
               bbox_to_anchor=(1, 0.5), frameon=False)
axes[1].set_title('Доли целей кредита')
plt.show()
