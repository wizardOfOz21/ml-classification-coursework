"""Одна таблица выводов для последовательных шагов анализа"""
import pandas as pd


def empty_findings():
    return pd.DataFrame(columns=['Выводы', 'Решения', 'Метка'], index=pd.Index([], name='id'), dtype=object)


def update_findings(table, additions=(), remove=()):
    """Записи: (id, вывод, решение) Метки new/removed действуют до следующего обновления"""
    result = table.loc[table['Метка'].ne('removed')].copy()
    result['Метка'] = ''
    for key in remove:
        if key in result.index:
            result.loc[key, 'Метка'] = 'removed'
    for key, finding, decision in additions:
        if key in result.index:
            old = result.loc[key]
            if old['Выводы'] != finding or old['Решения'] != decision:
                previous_key = f'{key}::previous'
                result = result.rename(index={key: previous_key})
                result.loc[previous_key, 'Метка'] = 'removed'
        result.loc[key] = [finding, decision, 'new']
    return result


def active_findings(table):
    """Актуальные строки без служебных меток и удаляемых версий"""
    return table.loc[table['Метка'].ne('removed'), ['Выводы', 'Решения']].copy()


def findings_view(table, only_new=False):
    """Полная таблица или только новые строки с прежними цветами и знаками"""
    selected = table.loc[table['Метка'].eq('new')] if only_new else table
    view = selected[['Выводы', 'Решения']].copy()
    signs = selected['Метка'].map({'new': '+ ', 'removed': '− ', '': ''}).fillna('')
    view['Выводы'] = signs + view['Выводы']
    colors = selected['Метка'].map({
        'new': 'background-color: #dcefe3; color: #172b20',
        'removed': 'background-color: #f9dddd; color: #7a2020',
        '': '',
    }).fillna('')
    return (view.style
            .apply(lambda frame: pd.DataFrame({column: colors for column in frame.columns}, index=frame.index), axis=None)
            .format(escape='html')
            .set_properties(**{'text-align': 'left', 'white-space': 'pre-wrap', 'vertical-align': 'top'})
            .hide(axis='index'))
