grade_counts = data['loan_grade'].value_counts().reindex(list('ABCDEFG'), fill_value=0)
grade_table = pd.DataFrame({
    'Количество': grade_counts,
    'Доля, %': 100 * grade_counts / len(data),
})
display(grade_table)

fig, axes = plt.subplots(1, 2, figsize=(14, 4.5), constrained_layout=True)
grade_colors = sns.color_palette('viridis', len(grade_table))
bars = axes[0].bar(grade_table.index, grade_table['Доля, %'], color=grade_colors)
axes[0].bar_label(bars, labels=[f'{share:.2f} %' for share in grade_table['Доля, %']],
                  padding=5, fontsize=9)
axes[0].set(title='Распределение грейдов', xlabel='Грейд займа', ylabel='Доля записей, %')
axes[0].set_ylim(0, grade_table['Доля, %'].max() * 1.18)

wedges, _, _ = axes[1].pie(
    grade_counts, colors=grade_colors, startangle=90,
    autopct=lambda share: f'{share:.2f} %' if share >= 2 else '',
    pctdistance=0.72, wedgeprops={'edgecolor': 'white'},
)
axes[1].legend(wedges, [
    f'{grade} — {share:.2f} %' for grade, share in grade_table['Доля, %'].items()
], loc='center left', bbox_to_anchor=(1, 0.5), frameon=False)
axes[1].set_title('Доли грейдов')
plt.show()
