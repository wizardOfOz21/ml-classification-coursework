from itertools import combinations_with_replacement
from scipy.stats import chi2_contingency, kruskal
from sklearn.feature_selection import mutual_info_classif


def cramers_v(left, right):
    paired = pd.concat([left, right], axis=1).dropna()
    if paired.empty:
        return np.nan
    table = pd.crosstab(paired.iloc[:, 0], paired.iloc[:, 1])
    # Удаляем ненаблюдаемые категории, если столбцы имеют dtype category
    table = table.loc[table.sum(axis=1).gt(0), table.sum(axis=0).gt(0)]
    k, m = table.shape
    if min(k, m) < 2:
        return np.nan
    chi2 = chi2_contingency(table, correction=False)[0]
    return np.sqrt(chi2 / (table.to_numpy().sum() * min(k - 1, m - 1)))


def numerical_nominal_nmi(numerical, nominal):
    paired = pd.DataFrame({'x': numerical, 'y': nominal}).dropna()
    if paired.empty:
        return np.nan, np.nan, np.nan
    labels, _ = pd.factorize(paired['y'], sort=False)
    counts = np.bincount(labels)
    probabilities = counts / counts.sum()
    entropy = float(-(probabilities * np.log(probabilities)).sum())
    if entropy <= 0:
        return np.nan, entropy, np.nan
    if paired['x'].nunique() <= 1:
        return 0.0, entropy, 0.0
    if counts.min() < 2:
        return np.nan, entropy, np.nan
    mi = mutual_info_classif(
        paired[['x']], labels, discrete_features=False,
        n_neighbors=3, random_state=42,
    )[0]
    ratio = mi / entropy
    return float(mi), entropy, float(np.clip(ratio, 0.0, 1.0))


def ordinal_nominal_kruskal(ordinal, nominal, order):
    paired = pd.DataFrame({'ordinal': ordinal, 'nominal': nominal}).dropna()
    if not paired['ordinal'].isin(order).all():
        raise ValueError('Неизвестные категории порядкового признака')
    paired['rank_code'] = paired['ordinal'].map(
        {category: rank for rank, category in enumerate(order)}
    )
    groups = [
        group['rank_code'].to_numpy(dtype=float)
        for _, group in paired.groupby('nominal', observed=True, sort=False)
        if not group.empty
    ]
    k, n = len(groups), len(paired)
    if k < 2 or n <= k or paired['rank_code'].nunique() < 2:
        return np.nan, k, n, np.nan
    try:
        h = float(kruskal(*groups).statistic)
    except ValueError:
        return np.nan, k, n, np.nan
    if not np.isfinite(h):
        return np.nan, k, n, np.nan
    effect = (h - k + 1) / (n - k)
    return h, k, n, float(effect)


# Общая матрица: инициализируем один раз перед последовательными этапами
association_columns = train.columns
association_matrix = pd.DataFrame(
    np.nan, index=association_columns, columns=association_columns, dtype=float,
)

# Используем смысловые типы из раздела 0.3, а не dtype столбцов
association_types = columns_info['Фактический тип'].reindex(association_columns)
numerical_columns = association_types.index[association_types.eq('числовой')].tolist()

# Числовые пары
pearson_matrix = train[numerical_columns].corr(method='pearson', min_periods=2)
association_matrix.loc[numerical_columns, numerical_columns] = pearson_matrix

nominal_columns = association_types.index[
    association_types.isin(['номинальный', 'бинарный'])
].tolist()

# Номинальные пары, включая бинарные
for left, right in combinations_with_replacement(nominal_columns, 2):
    value = cramers_v(train[left], train[right])
    association_matrix.loc[left, right] = value
    association_matrix.loc[right, left] = value

# Явный порядок категорий, без изменения исходного train
ordinal_orders = {'loan_grade': ['A', 'B', 'C', 'D', 'E', 'F', 'G']}
ordinal_columns = association_types.index[association_types.eq('порядковый')].tolist()

for ordinal in ordinal_columns:
    order = ordinal_orders[ordinal]
    observed = train[ordinal].dropna()
    if not observed.isin(order).all():
        raise ValueError(f'Неизвестные категории в {ordinal}')
    ordinal_values = train[ordinal].map({grade: rank for rank, grade in enumerate(order)})
    # Самокорреляция определена только при наличии разных наблюдаемых грейдов
    association_matrix.loc[ordinal, ordinal] = (
        1.0 if ordinal_values.nunique() > 1 else np.nan
    )
    for numerical in numerical_columns:
        paired = pd.DataFrame({
            'numerical': train[numerical],
            'ordinal': ordinal_values,
        }).dropna()
        value = np.nan
        if len(paired) >= 2 and paired.nunique().gt(1).all():
            value = paired.corr(method='spearman', min_periods=2).loc['numerical', 'ordinal']
        association_matrix.loc[numerical, ordinal] = value
        association_matrix.loc[ordinal, numerical] = value

# Пары порядковых переменных, включая диагональ
ordinal_data = pd.DataFrame({
    column: train[column].map({value: rank for rank, value in enumerate(ordinal_orders[column])})
    for column in ordinal_columns
}, index=train.index)
association_matrix.loc[ordinal_columns, ordinal_columns] = ordinal_data.corr(
    method='spearman', min_periods=2,
)


# Числовые × номинальные
nmi_records = []
for numerical in numerical_columns:
    for nominal in nominal_columns:
        mi, entropy, value = numerical_nominal_nmi(train[numerical], train[nominal])
        association_matrix.loc[numerical, nominal] = value
        association_matrix.loc[nominal, numerical] = value
        nmi_records.append({
            'Numerical': numerical, 'Nominal': nominal,
            'MI estimate': mi, 'H(Y)': entropy,
            'MI / H(Y)': mi / entropy if entropy > 0 else np.nan,
            'NMI': value,
        })

nmi_estimates = pd.DataFrame(nmi_records).set_index(['Numerical', 'Nominal'])

# Порядковые × номинальные
kruskal_records = []
for ordinal in ordinal_columns:
    for nominal in nominal_columns:
        h, k, n, effect = ordinal_nominal_kruskal(
            train[ordinal], train[nominal], ordinal_orders[ordinal],
        )
        association_matrix.loc[ordinal, nominal] = effect
        association_matrix.loc[nominal, ordinal] = effect
        kruskal_records.append({
            'Ordinal': ordinal, 'Nominal': nominal,
            'H': h, 'k': k, 'n': n, 'epsilon_squared': effect,
        })

kruskal_effects = pd.DataFrame(kruskal_records).set_index(['Ordinal', 'Nominal'])
