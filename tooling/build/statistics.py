"""Write both notebook sizes and shared content statistics."""
from pathlib import Path
import re

import nbformat


def notebook_statistics(notebook_path):
    path = Path(notebook_path)
    notebook = nbformat.read(path, as_version=4)
    code = [cell.source for cell in notebook.cells if cell.cell_type == 'code']
    text = [cell.source for cell in notebook.cells if cell.cell_type in {'markdown', 'raw'}]
    prose = re.sub(r'<[^>]*>', ' ', '\n'.join(text))
    words = len(re.findall(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*", prose))
    cell_lines = [len(source.splitlines()) for source in code]
    lines = [
        f'Ячеек: {len(notebook.cells)}',
        f'Строк кода: {sum(len(source.splitlines()) for source in code)}',
        f'Строк текста: {sum(len(source.splitlines()) for source in text)}',
        f'Слов в тексте: {words}',
        f'Минимум строк в ячейке кода: {min(cell_lines, default=0)}',
        f'Максимум строк в ячейке кода: {max(cell_lines, default=0)}',
    ]
    return lines


def write_statistics(notebook_path):
    path = Path(notebook_path)
    unexecuted = path.with_suffix('.unexecuted.ipynb')
    lines = [f'Размер неисполненной версии: {unexecuted.stat().st_size / 1024**2:.2f} МиБ']
    if path.is_file():
        lines.append(f'Размер исполненной версии: {path.stat().st_size / 1024**2:.2f} МиБ')
    lines.extend(notebook_statistics(unexecuted))
    report = path.with_suffix('.stats.txt')
    report.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


def main():
    from tooling.common import ROOT, load_config
    write_statistics(ROOT / load_config()['output'])


if __name__ == '__main__':
    main()
