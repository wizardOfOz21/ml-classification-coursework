#!/usr/bin/env python3
"""Assemble development notebooks, expanding declared helpers in execution order."""
import argparse
import ast
import copy
import json
from pathlib import Path
import sys

from tooling.common import ROOT, MANIFEST, load_manifest
from tooling.build.statistics import write_statistics

import nbformat


def project_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes project: {relative}')
    return path


def check_code(cells):
    """Reject accidental duplicate definitions or remaining project imports."""
    definitions = set()
    for cell in cells:
        if cell.cell_type != 'code':
            continue
        tree = ast.parse(cell.source)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name in definitions:
                    raise ValueError(f'Duplicate definition: {node.name}')
                definitions.add(node.name)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = [node.module or '']
                if node.level:
                    raise ValueError('Relative import remains in generated notebook')
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                continue
            if any(name.split('.')[0] in {'src', 'notebooks', 'scripts', 'tooling', 'tests', 'config'} for name in names):
                raise ValueError(f'Project import remains: {names}')


def build_notebook(root=ROOT, output=None):
    root = Path(root).resolve()
    if output is not None:
        output = Path(output).resolve()
        if output in {root / 'solution.ipynb', root / 'solution.original.ipynb'}:
            raise ValueError('Refusing to overwrite either original notebook')
        if output.suffix.lower() != '.ipynb':
            raise ValueError('Build output must be an .ipynb file')
        if any(output.is_relative_to(root / name) for name in
               ['src', 'tooling', 'config', 'dataset', 'scripts', 'notebooks', 'data', 'tests', 'docs']):
            raise ValueError('Build output cannot be placed inside source or data directories')
    manifest = json.loads((root / MANIFEST).read_text())
    if output is not None:
        protected = {project_path(root, s['file']) for s in manifest['sections']}
        protected.update(project_path(root, name) for name in manifest.get('modules', []))
        protected.add(root / MANIFEST)
        if output in protected:
            raise ValueError('Refusing to overwrite modular sources')
    if manifest['version'] != 1:
        raise ValueError('Unsupported manifest version')
    notebook = nbformat.v4.new_notebook(metadata=copy.deepcopy(manifest['metadata']))
    notebook.nbformat_minor = manifest['nbformat_minor']
    seen_sections, seen_modules = set(), set()
    def append_section(relative):
        path = project_path(root, relative)
        if path in seen_sections:
            raise ValueError(f'Duplicate section: {path}')
        seen_sections.add(path)
        part = nbformat.read(path, as_version=4)
        nbformat.validate(part)
        for original in part.cells:
            cell = copy.deepcopy(original)
            transport = cell.metadata.pop('modular', {})
            if transport.get('development_only'):
                continue
            if 'include' in transport:
                if transport.get('splices'):
                    raise ValueError('A cell cannot include a notebook and splice Python together')
                append_section(transport['include'])
                continue
            if 'dev-only' in cell.metadata.get('tags', []) and not transport.get('splices'):
                continue
            for splice in transport.get('splices', []):
                module = project_path(root, splice['path'])
                if module in seen_modules:
                    raise ValueError(f'Module would be inlined twice: {module}')
                if cell.cell_type != 'code' or cell.source.count(splice['placeholder']) != 1:
                    raise ValueError(f'Missing or ambiguous placeholder for {module}')
                cell.source = cell.source.replace(splice['placeholder'], module.read_text(encoding='utf-8'))
                seen_modules.add(module)
            if 'dev-only' in cell.metadata.get('tags', []):
                tags = [tag for tag in cell.metadata['tags'] if tag != 'dev-only']
                if tags:
                    cell.metadata['tags'] = tags
                else:
                    cell.metadata.pop('tags')
            notebook.cells.append(cell)
    for section in manifest['sections']:
        append_section(section['file'])
    check_code(notebook.cells)
    nbformat.validate(notebook)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        nbformat.write(notebook, output)
        write_statistics(output)
    return notebook



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=['submission', 'validation'], default='submission')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or ROOT / load_manifest()['targets'][args.target]['output']
    result = build_notebook(output=output)
    print(f'Built {output}: {len(result.cells)} cells')

if __name__ == '__main__':
    main()
