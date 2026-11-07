ownership_counts = data['person_home_ownership'].value_counts()
ownership_table = pd.DataFrame({
    'Количество': ownership_counts,
    'Доля, %': 100 * ownership_counts / len(data),
})
display(ownership_table)

fig, axes = plt.subplots(1, 2, figsize=(14, 4.5), constrained_layout=True)
colors = ['#3977a8', '#e6a34a', '#66a68b', '#b578a5']
bars = axes[0].bar(ownership_table.index, ownership_table['Доля, %'], color=colors)
axes[0].bar_label(bars, labels=[
    f'{count:,} ({share:.2f} %)'.replace(',', ' ')
    for count, share in zip(ownership_table['Количество'], ownership_table['Доля, %'])
], padding=5, fontsize=9)
axes[0].set(title='Распределение по типу жилья', xlabel='Тип жилья', ylabel='Доля записей, %')
axes[0].set_ylim(0, ownership_table['Доля, %'].max() * 1.18)

wedges, _, _ = axes[1].pie(
    ownership_counts, colors=colors, startangle=90,
    autopct=lambda share: f'{share:.2f} %' if share >= 1 else '',
    pctdistance=0.72, wedgeprops={'edgecolor': 'white'},
)
axes[1].legend(wedges, [
    f'{category} — {share:.2f} %'
    for category, share in ownership_table['Доля, %'].items()
], loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)
axes[1].set_title('Доли категорий жилья')
plt.show()
