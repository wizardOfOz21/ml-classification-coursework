"""Assemble notebooks using relative # include: directives in code cells."""
import argparse
from pathlib import Path
import re
import shutil
from uuid import uuid4

import nbformat

from tooling.common import ROOT, load_config
from tooling.build.statistics import write_statistics


def copy_dataset(root, directory):
    source = root / load_config(root)['dataset']
    destination = Path(directory) / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)


def expand_notebook(path, stack=()):
    path = Path(path).resolve()
    if path in stack:
        chain = ' -> '.join(str(item) for item in (*stack, path))
        raise ValueError(f'Circular include: {chain}')
    notebook = nbformat.read(path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            directive = re.fullmatch(r'# include:[ \t]*(.+)', cell.source.strip())
            if directive:
                relative = Path(directive.group(1).strip())
                if relative.is_absolute():
                    raise ValueError(f'Include must be relative to {path}: {relative}')
                included = path.parent / relative
                if included.suffix == '.ipynb':
                    yield from expand_notebook(included, (*stack, path))
                elif included.suffix == '.py':
                    yield nbformat.v4.new_code_cell(included.read_text(encoding='utf-8'))
                else:
                    raise ValueError(f'Include must be .ipynb or .py: {included}')
                continue
            if any(line.lstrip().startswith('# include:') for line in cell.source.splitlines()):
                raise ValueError(f'Include must occupy its own code cell: {path}')
        cell.id = uuid4().hex[:8]
        yield cell


def build_notebook(root=ROOT, output=None):
    root = Path(root).resolve()
    entry = root / load_config(root)['entry']
    notebook = nbformat.read(entry, as_version=4)
    notebook.cells = list(expand_notebook(entry))
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            cell.outputs = []
            cell.execution_count = None
    nbformat.validate(notebook)
    if output is not None:
        output = Path(output).resolve()
        if output.suffix != '.ipynb' or output.is_relative_to(root / 'src'):
            raise ValueError('Output must be an .ipynb file outside src/')
        copy_dataset(root, output.parent)
        nbformat.write(notebook, output)
    return notebook


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or ROOT / load_config()['output']
    unexecuted = output.with_suffix('.unexecuted.ipynb')
    notebook = build_notebook(output=unexecuted)
    write_statistics(output)
    print(f'Built {unexecuted}: {len(notebook.cells)} cells')


if __name__ == '__main__':
    main()
