"""Preserve legacy content while permitting the explicitly requested new outline."""
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
            for before, after in edits:
                text = text.replace(before, after)
            if cell.source != text:
                errors.append(f'Unapproved narrative change: legacy cell {index}')
            if cell.get('attachments', {}) != original_cell.get('attachments', {}):
                errors.append(f'Attachment changed: legacy cell {index}')
    return errors, stored_outputs
