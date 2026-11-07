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
