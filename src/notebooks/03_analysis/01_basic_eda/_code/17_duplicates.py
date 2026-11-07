duplicate_extra = data.duplicated()
duplicate_all = data.duplicated(keep=False)
feature_columns = data.columns.drop('loan_status')
conflicting_groups = (
    data.groupby(list(feature_columns), dropna=False)['loan_status']
        .nunique().gt(1)
)

duplicate_summary = pd.DataFrame({
    'Количество': [
        int(duplicate_extra.sum()),
        int(duplicate_all.sum()),
        len(data.loc[duplicate_all].drop_duplicates()),
        int(conflicting_groups.sum()),
    ]
}, index=[
    'Повторные экземпляры сверх первого',
    'Все строки в повторяющихся группах',
    'Группы полностью одинаковых строк',
    'Группы одинаковых признаков с разными loan_status',
])
display(duplicate_summary)
display(data.loc[duplicate_all].sort_values(list(data.columns)).head(10))
