def plot_association_matrix(matrix, title):
    # Разные палитры обозначают разные меры, без общей цветовой шкалы
    pearson_mask = pd.DataFrame(True, index=matrix.index, columns=matrix.columns)
    pearson_mask.loc[numerical_columns, numerical_columns] = False
    ordinal = association_types.index[association_types.eq('порядковый')]
    pearson_mask.loc[numerical_columns, ordinal] = False
    pearson_mask.loc[ordinal, numerical_columns] = False
    pearson_mask.loc[ordinal, ordinal] = False
    # Скрываем верхний треугольник только при отображении
    upper_mask = np.triu(np.ones(matrix.shape, dtype=bool), k=1)
    fig, ax = plt.subplots(figsize=(14, 12), constrained_layout=True)
    sns.heatmap(
        matrix, mask=matrix.isna() | pearson_mask | upper_mask,
        cmap='RdBu_r', center=0, vmin=-1, vmax=1,
        annot=True, fmt='.2f', square=True, cbar=False,
        linewidths=0, ax=ax,
    )
    nominal_mask = pd.DataFrame(True, index=matrix.index, columns=matrix.columns)
    nominal = association_types.index[association_types.isin(['номинальный', 'бинарный'])]
    nominal_mask.loc[nominal, nominal] = False
    if (matrix.notna() & ~nominal_mask).any().any():
        sns.heatmap(
            matrix, mask=matrix.isna() | nominal_mask | upper_mask,
            cmap='Purples', vmin=0, vmax=1,
            annot=True, fmt='.2f', square=True, cbar=False,
            linewidths=0, ax=ax,
        )
    nmi_mask = pd.DataFrame(True, index=matrix.index, columns=matrix.columns)
    nmi_mask.loc[numerical_columns, nominal] = False
    nmi_mask.loc[nominal, numerical_columns] = False
    if (matrix.notna() & ~nmi_mask).any().any():
        sns.heatmap(
            matrix, mask=matrix.isna() | nmi_mask | upper_mask,
            cmap='Greens', vmin=0, vmax=1,
            annot=True, fmt='.2f', square=True, cbar=False,
            linewidths=0, ax=ax,
        )
    kw_mask = pd.DataFrame(True, index=matrix.index, columns=matrix.columns)
    kw_mask.loc[ordinal, nominal] = False
    kw_mask.loc[nominal, ordinal] = False
    if (matrix.notna() & ~kw_mask).any().any():
        sns.heatmap(
            matrix.clip(lower=0, upper=1),
            mask=matrix.isna() | kw_mask | upper_mask,
            cmap='Oranges', vmin=0, vmax=1,
            annot=matrix, fmt='.2f', square=True, cbar=False,
            linewidths=0, ax=ax,
        )
    ax.xaxis.tick_bottom()
    ax.tick_params(axis='x', labeltop=False, labelbottom=True)
    plt.setp(ax.get_xticklabels(), rotation=60, ha='right', rotation_mode='anchor')
    plt.setp(ax.get_yticklabels(), rotation=0)
    ax.set_title(title, pad=15)
    ax.set_xlabel(
        'Pearson / Spearman: синий (−), красный (+), интенсивность по |r| / |ρ|\n'
        "Cramér’s V: фиолетовый, интенсивность по V; NMI: зелёный, интенсивность по NMI\nKruskal–Wallis: оранжевый, интенсивность по ε² (в пределах [0, 1])\nПустые ячейки — NaN",
        labelpad=15,
    )
    plt.show()


plot_association_matrix(
    association_matrix,
    'Матрица попарных ассоциаций, train',
)
