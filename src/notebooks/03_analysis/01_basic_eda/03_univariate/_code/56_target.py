target_counts = data['loan_status'].value_counts().reindex([0, 1], fill_value=0)
target_table = pd.DataFrame({
    'Количество': target_counts,
    'Доля, %': 100 * target_counts / len(data),
})
display(target_table)

fig, axes = plt.subplots(1, 2, figsize=(13, 4), constrained_layout=True)
target_labels = ['0 — без дефолта', '1 — дефолт']
target_colors = ['#3977a8', '#e6a34a']
bars = axes[0].bar(target_labels, target_table['Доля, %'], color=target_colors)
axes[0].bar_label(bars, labels=[
    f'{count:,} ({share:.2f} %)'.replace(',', ' ')
    for count, share in zip(target_table['Количество'], target_table['Доля, %'])
], padding=5)
axes[0].set(title='Баланс классов loan_status', xlabel='Исход кредита', ylabel='Доля записей, %')
axes[0].set_ylim(0, 100)
axes[1].pie(target_counts, labels=target_labels, colors=target_colors,
            startangle=90, autopct=lambda share: f'{share:.2f} %',
            wedgeprops={'edgecolor': 'white'})
axes[1].set_title('Доли исходов кредита')
plt.show()
