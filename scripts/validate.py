#!/usr/bin/env python3
"""Validate structure, fresh-kernel results and a data-only standalone execution."""
import argparse
import ast
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import re
import shutil
import sys
import tempfile
import traceback
import warnings

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
import numpy as np
import pandas as pd

from build import ROOT, build_notebook

warnings.filterwarnings('ignore', category=nbformat.warnings.MissingIDFieldWarning)


def compare_structure(original, generated):
    errors = []
    text_a = [(c.cell_type, c.source, dict(c.get('attachments', {}))) for c in original.cells if c.cell_type != 'code']
    text_b = [(c.cell_type, c.source, dict(c.get('attachments', {}))) for c in generated.cells if c.cell_type != 'code']
    if text_a != text_b:
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


def modular_notebook(root, manifest):
    result = nbformat.v4.new_notebook(metadata=copy.deepcopy(manifest['metadata']))
    for section in manifest['sections']:
        result.cells.extend(nbformat.read(root / section['file'], as_version=4).cells)
    return result


def execute(notebook, label, root, artifacts, isolated=True, timeout=180):
    """Each run gets a new kernel and a different working directory."""
    with tempfile.TemporaryDirectory(prefix=f'notebook-{label}-') as directory:
        temp = Path(directory)
        working = temp if isolated else root
        if isolated:
            shutil.copytree(root / 'data', temp / 'data')
            nbformat.write(notebook, temp / 'notebook.ipynb')
            assert all(not (temp / name).exists() for name in ['src', 'notebooks', 'scripts'])
        for suffix in ['snapshot.pkl', 'error.txt']:
            (artifacts / f'{label}.{suffix}').unlink(missing_ok=True)
        snapshot = temp / 'snapshot.pkl'
        runtime = (root / 'scripts/capture_runtime.py').read_text()
        runtime = "get_ipython().run_line_magic('matplotlib', 'inline')\n" + runtime
        instrumented = copy.deepcopy(notebook)
        instrumented.cells.insert(0, nbformat.v4.new_code_cell(runtime))
        instrumented.cells.append(nbformat.v4.new_code_cell(f'__v_finish({str(snapshot)!r})'))
        km = KernelManager(kernel_name='python3')
        km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        env.update(IPYTHONDIR=str(temp / 'ipython'), JUPYTER_RUNTIME_DIR=str(temp / 'runtime'),
                   MPLCONFIGDIR=str(temp / 'matplotlib'), PYTHONHASHSEED='0', MPLBACKEND='module://matplotlib_inline.backend_inline')
        result = {'status': 'passed', 'isolated': isolated, 'cwd_has_only_data': isolated}
        try:
            client = NotebookClient(instrumented, km=km, timeout=timeout,
                                    resources={'metadata': {'path': str(working)}})
            client.execute(cwd=str(working), env=env)
            if not snapshot.exists():
                raise RuntimeError('Kernel did not produce a result snapshot')
            with snapshot.open('rb') as handle:
                result['snapshot'] = pickle.load(handle)
            result['counts'] = {key: len(value) for key, value in result['snapshot'].items()}
            (artifacts / f'{label}.snapshot.pkl').write_bytes(snapshot.read_bytes())
        except Exception as error:
            result['status'] = 'unavailable' if isinstance(error, (PermissionError, OSError)) else 'failed'
            result['error'] = f'{type(error).__name__}: {error}'
            (artifacts / f'{label}.error.txt').write_text(traceback.format_exc())
        finally:
            nbformat.write(instrumented, artifacts / f'{label}.executed.ipynb')
        return result


def write_report(root, manifest, structure, integrity, runs, differences, stored_outputs):
    passed = not structure and not integrity and not differences and all(r['status'] == 'passed' for r in runs.values())
    lines = ['# Проверка модульной сборки solution.ipynb', '',
             '## Итог', '',
             ('Все обязательные проверки выполнены, эквивалентность подтверждена в проверенном окружении и на текущем датасете.' if passed else
              'Эквивалентность не подтверждена полностью: ниже разделены расхождения и недоступные проверки.'), '',
             ('Рабочий solution.ipynb не заменялся, solution.original.ipynb сохранён без изменений.' if not integrity else
              'Контрольные суммы оригиналов изменились относительно эталона; подробности указаны в расхождениях.'), '',
             '## Выделенные разделы', '']
    lines += [f"- `{s['file']}` — {s['title']}" for s in manifest['sections']]
    lines += ['', '## Вынесенные определения и сборка', '',
              '- `src/associations.py`: cramers_v, numerical_nominal_nmi, ordinal_nominal_kruskal',
              '- `src/visualization.py`: plot_association_matrix',
              '- Классов в исходнике нет; ранние небольшие функции оставлены в ячейках из-за зависимости от изменяемых notebook globals',
              '- Манифест задаёт порядок разделов, метаданные и контрольную сумму исходника',
              '- Вспомогательные определения встраиваются на место объявленных загрузчиков; служебные bootstrap-ячейки исключаются',
              '- Структура кода проверяется по полному упорядоченному AST, а не по числу ячеек',
              '- Существующие выводы ячеек при сборке сохраняются; результаты проверочных запусков записываются отдельно', '',
              '## Успешные проверки', '']
    if not integrity:
        lines.append('- SHA-256 резервной копии и рабочего оригинала совпадает с зафиксированным исходником')
    if not structure:
        lines.append('- Порядок и полный текст Markdown/raw, формулы, вложенные изображения и notebook metadata сохранены; упорядоченный AST кода совпадает')
    if stored_outputs:
        lines.append('- Сохранённые до запуска выводы всех исходных ячеек перенесены без изменения')
    for label, run in runs.items():
        if run['status'] == 'passed':
            lines.append(f"- `{label}`: новый Jupyter kernel, все ячейки выполнены; таблиц {run['counts']['tables']}, графиков {run['counts']['plots']}, объектов данных {run['counts']['values']}")
    for left, right in [('original', 'generated'), ('original', 'modular')]:
        if all(runs[name]['status'] == 'passed' for name in [left, right]) and not any(d.startswith(f'{left}/{right}:') for d in differences):
            lines.append(f'- `{left}` / `{right}`: совпали отображённые таблицы, численные объекты и данные графиков; rtol=1e-9, atol=1e-11')
    if runs['generated']['status'] == 'passed':
        lines.append('- Автономность: generated выполнен в отдельном временном каталоге с данными, без src/, notebooks/, scripts/ и без PYTHONPATH проекта')
    lines += ['', '## Расхождения и ошибки', '']
    issues = integrity + structure + differences
    issues += [f"{label}: {run['error']}" for label, run in runs.items() if run['status'] == 'failed']
    lines += ['- ' + issue for issue in issues] if issues else ['Не обнаружены']
    lines += ['', '## Проверки, которые не удалось выполнить', '']
    unavailable = [f"{label}: {run['error']}" for label, run in runs.items() if run['status'] == 'unavailable']
    lines += ['- ' + issue for issue in unavailable] if unavailable else ['Нет']
    lines += ['', '## Технические изменения и границы проверки', '',
              '- Сборка и проверка не редактируют исходный notebook; идентификаторы старых ячеек нормализованы только в модульных файлах и сборке',
              '- При разработке определения исполняются в общем notebook namespace, сохраняя позднее разрешение глобальных зависимостей; сборка содержит обычные def',
              '- Проверочный harness для обоих notebook одинаково устанавливает seed=42 (NumPy/Python) и PYTHONHASHSEED=0: исходный data.sample() не имеет random_state. Сам анализ и его параметры не менялись',
              '- Первоначально sandbox блокировал открытие локальных портов Jupyter; результаты повторных запусков с разрешением на локальные ядра указаны выше',
              '- История команд IPython и ссылки на объекты Axes исключены из снимков: они зависят от сессии, данные графиков сравниваются отдельно',
              '- Случайные UUID HTML Styler не сравниваются; сравниваются исходные отображённые таблицы',
              '- Для графиков сравниваются массивы, линии, геометрия, цвета, подписи, шкалы и пределы осей; побайтовое совпадение PNG не требуется',
              '- Сравнение охватывает итоговые DataFrame/Series/Index/массивы, простые структуры данных и скаляры; в том числе association_matrix, nmi_estimates, kruskal_effects и train/validation/test',
              '- Моделей и метрик обучения в текущем исходнике нет',
              '- Это воспроизводимая проверка данной работы, не формальное доказательство эквивалентности на произвольных будущих данных', '',
              '## Окружение', '', f'- Python: `{sys.version.split()[0]}`',
              f'- Интерпретатор: `{sys.executable}`',
              f"- SHA-256 исходника: `{manifest['baseline_sha256']}`", '',
              'Подробные выполненные ноутбуки, снимки результатов и JSON-статус: `validation_artifacts/`', '']
    (root / 'validation_report.md').write_text('\n'.join(lines), encoding='utf-8')
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=int, default=180, help='Timeout per code cell in seconds')
    args = parser.parse_args()
    root = ROOT
    artifacts = root / 'validation_artifacts'
    artifacts.mkdir(exist_ok=True)
    manifest = json.loads((root / 'notebook_manifest.json').read_text())
    packages = ['pandas', 'numpy', 'scipy', 'scikit-learn', 'matplotlib', 'seaborn', 'ipython', 'nbformat', 'nbclient', 'ipykernel', 'jupyter-client']
    environment = {'python': sys.version, 'executable': sys.executable, 'packages': {p: importlib.metadata.version(p) for p in packages}}
    (artifacts / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    integrity = []
    for name in ['solution.original.ipynb', 'solution.ipynb']:
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != manifest['baseline_sha256']:
            integrity.append(f'Original hash changed: {name}')
    original = nbformat.read(root / manifest['baseline'], as_version=4)
    generated = nbformat.read(root / 'solution.generated.ipynb', as_version=4)
    rebuilt = build_notebook(root)
    structure = compare_structure(original, generated)
    # Compare to current development files too, so a stale generated file fails validation
    structure += [f'Current sources: {s}' for s in compare_structure(rebuilt, generated)]
    stored_outputs = [c.get('outputs') for c in original.cells] == [c.get('outputs') for c in generated.cells]
    if not stored_outputs:
        structure.append('Stored cell outputs differ from the original')
    runs = {}
    if integrity or structure:
        runs = {name: {'status': 'unavailable', 'error': 'Execution skipped after structural/integrity failure'} for name in ['original', 'generated', 'modular']}
    else:
        for label, notebook, isolated in [('original', original, True), ('generated', generated, True), ('modular', modular_notebook(root, manifest), False)]:
            print(f'Executing {label} in a fresh kernel ({"data-only" if isolated else "shared modular namespace"})...', flush=True)
            runs[label] = execute(notebook, label, root, artifacts, isolated, args.timeout)
            print(f"{label}: {runs[label]['status']} {runs[label].get('counts', {})}", flush=True)
    differences = []
    for left, right in [('original', 'generated'), ('original', 'modular')]:
        if all(runs[name]['status'] == 'passed' for name in [left, right]):
            differences.extend(f'{left}/{right}: {s}' for s in compare_values(runs[left]['snapshot'], runs[right]['snapshot']))
    passed = write_report(root, manifest, structure, integrity, runs, differences, stored_outputs)
    status = {'passed': passed, 'integrity_errors': integrity, 'structural_errors': structure,
              'differences': differences, 'runs': {k: {a: b for a, b in v.items() if a != 'snapshot'} for k, v in runs.items()}}
    (artifacts / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
    print(f'{"PASS" if passed else "NOT VERIFIED"}: {root / "validation_report.md"}')
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
