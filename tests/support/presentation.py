"""Explicitly project obsolete code-rendered descriptions out of legacy checks.

Descriptions now live in Markdown/HTML. All numerical analysis, semantic types,
and the remaining displayed results are still compared with the immutable baseline.
"""
import ast
import copy

DESCRIPTION_COLUMNS = {'Описание из источника', 'Описание'}
DESCRIPTION_VARIABLES = {'source_descriptions', 'interpretations'}


def remove_description_code(notebook):
    result = copy.deepcopy(notebook)
    for cell in result.cells:
        if cell.cell_type != 'code':
            continue
        tree = ast.parse(cell.source)
        retained = []
        for statement in tree.body:
            if isinstance(statement, ast.Assign):
                if any(isinstance(t, ast.Name) and t.id in DESCRIPTION_VARIABLES for t in statement.targets):
                    continue
                if any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                       and t.value.id == 'columns_info' and isinstance(t.slice, ast.Constant)
                       and t.slice.value in DESCRIPTION_COLUMNS for t in statement.targets):
                    continue
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                call = statement.value
                if isinstance(call.func, ast.Name) and call.func.id == 'display':
                    if any(isinstance(n, ast.Name) and n.id in DESCRIPTION_VARIABLES for n in ast.walk(call)):
                        continue
                    if (any(isinstance(n, ast.Name) and n.id == 'columns_info' for n in ast.walk(call))
                            and any(isinstance(n, ast.Constant) and n.value == 'Описание' for n in ast.walk(call))):
                        continue
            retained.append(statement)
        tree.body = retained
        cell.source = ast.unparse(tree)
    return result


def analytical_snapshot(snapshot):
    result = copy.deepcopy(snapshot)
    tables = []
    for table in result['tables']:
        columns = set(table.columns)
        if columns == {'Описание из источника'} or columns == {'Описание из источника', 'Описание', 'Фактический тип'}:
            continue
        tables.append(table.drop(columns=['Описание из источника'], errors='ignore'))
    result['tables'] = tables
    for name in DESCRIPTION_VARIABLES:
        result['values'].pop(name, None)
    if 'columns_info' in result['values']:
        result['values']['columns_info'] = result['values']['columns_info'].drop(columns=list(DESCRIPTION_COLUMNS), errors='ignore')
    return result
