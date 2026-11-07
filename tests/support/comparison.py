"""Assertions shared by structural and regression tests."""
import ast
import numpy as np
import pandas as pd

def compare_structure(original, generated, compare_markdown=True):
    errors = []
    text_a = [(c.cell_type, c.source, dict(c.get('attachments', {}))) for c in original.cells if c.cell_type != 'code']
    text_b = [(c.cell_type, c.source, dict(c.get('attachments', {}))) for c in generated.cells if c.cell_type != 'code']
    if compare_markdown and text_a != text_b:
        errors.append('Markdown/raw cells, order or embedded attachments differ')
    def code_tree(notebook):
        statements = []
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                statements.extend(ast.parse(cell.source).body)
        return ast.dump(ast.Module(body=statements, type_ignores=[]), include_attributes=False)
    try:
        if code_tree(original) != code_tree(generated):
            errors.append('Ordered Python AST differs (operations, definitions or parameters)')
    except SyntaxError as error:
        errors.append(f'Cannot compare Python AST: {error}')
    if dict(original.metadata) != dict(generated.metadata):
        errors.append('Notebook metadata differs')
    return errors


def compare_values(left, right, path='result'):
    """Compare captured own-kernel data, including masks and figure geometry."""
    errors = []
    try:
        if isinstance(left, pd.DataFrame):
            pd.testing.assert_frame_equal(left, right, check_exact=False, rtol=1e-9, atol=1e-11)
        elif isinstance(left, pd.Series):
            pd.testing.assert_series_equal(left, right, check_exact=False, rtol=1e-9, atol=1e-11)
        elif isinstance(left, pd.Index):
            pd.testing.assert_index_equal(left, right)
        elif isinstance(left, np.ndarray):
            if not isinstance(right, np.ndarray):
                raise AssertionError('Array type differs')
            np.testing.assert_array_equal(np.ma.getmaskarray(left), np.ma.getmaskarray(right))
            a, b = np.asarray(left), np.asarray(right)
            if a.dtype.kind in 'biufc' and b.dtype.kind in 'biufc':
                np.testing.assert_allclose(a, b, rtol=1e-9, atol=1e-11, equal_nan=True)
            else:
                np.testing.assert_array_equal(a, b)
        elif isinstance(left, dict):
            if not isinstance(right, dict) or left.keys() != right.keys():
                raise AssertionError('Dictionary keys differ')
            for key in left:
                errors.extend(compare_values(left[key], right[key], f'{path}.{key}'))
        elif isinstance(left, (tuple, list)):
            if not isinstance(right, (tuple, list)) or len(left) != len(right):
                raise AssertionError('Sequence length/type differs')
            for i, (a, b) in enumerate(zip(left, right)):
                errors.extend(compare_values(a, b, f'{path}[{i}]'))
        elif isinstance(left, (float, int, np.number)) and not isinstance(left, (bool, np.bool_)):
            np.testing.assert_allclose(left, right, rtol=1e-9, atol=1e-11, equal_nan=True)
        elif left != right:
            raise AssertionError(f'{left!r} != {right!r}')
    except (AssertionError, TypeError, ValueError) as error:
        errors.append(f'{path}: {str(error)[:400]}')
    return errors
