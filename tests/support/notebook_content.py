"""Check legacy cells and explicitly approved narrative edits."""
import json
from collections import Counter


def compare_legacy_content(original, generated, root, manifest):
    edits = json.loads((root / manifest['documentation_edits']).read_text())
    errors = []
    indexed = {}
    counts = Counter()
    for cell in generated.cells:
        if 'origin_cell' in cell.metadata:
            index = cell.metadata['origin_cell']
            indexed[index] = cell
            counts[index] += 1
    expected = set(range(len(original.cells)))
    if set(indexed) != expected or any(v != 1 for v in counts.values()):
        errors.append('Legacy cells lost or duplicated in the nested outline')
    stored_outputs = True
    for index, original_cell in enumerate(original.cells):
        cell = indexed.get(index)
        if cell is None:
            stored_outputs = False
            continue
        if cell.cell_type != original_cell.cell_type:
            errors.append(f'Cell type changed: {index}')
        if cell.get('outputs') != original_cell.get('outputs'):
            stored_outputs = False
        if original_cell.cell_type == 'markdown':
            text = original_cell.source
            for edit in edits:
                if isinstance(edit, list):
                    before, after = edit
                    text = text.replace(before, after)
                elif edit['origin_cell'] == index:
                    if text != edit['before']:
                        errors.append(f'Narrative edit baseline mismatch: legacy cell {index}')
                    text = edit['after']
            if cell.source != text:
                errors.append(f'Unapproved narrative change: legacy cell {index}')
            if cell.get('attachments', {}) != original_cell.get('attachments', {}):
                errors.append(f'Attachment changed: legacy cell {index}')
    return errors, stored_outputs


def legacy_notebook(notebook):
    """Only the original cells, in execution order; new analysis follows them."""
    import copy
    import nbformat
    result = nbformat.v4.new_notebook(metadata=copy.deepcopy(notebook.metadata))
    result.cells = [copy.deepcopy(cell) for cell in notebook.cells if 'origin_cell' in cell.metadata]
    return result


def extension_order_errors(notebook):
    positions = [i for i, cell in enumerate(notebook.cells) if 'origin_cell' in cell.metadata]
    if not positions:
        return ['No legacy cells']
    return ['New executable code interleaves the immutable EDA'] if any(
        cell.cell_type == 'code' and 'origin_cell' not in cell.metadata
        for cell in notebook.cells[:max(positions)]
    ) else []
