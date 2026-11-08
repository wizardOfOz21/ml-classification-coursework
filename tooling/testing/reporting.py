"""Render check results; expectations and comparison rules remain in tests/."""
import sys
from tooling.common import validation_settings


def write_report(root, manifest, structure, integrity, runs, differences, stored_outputs):
    passed = not structure and not integrity and not differences and all(r['status'] == 'passed' for r in runs.values())
    extended = 'legacy' in runs
    pairs = [('original', 'legacy'), ('generated', 'modular')] if extended else [('original', 'generated'), ('original', 'modular')]
    lines = ['# Проверка курсовой и модульной сборки', '', '## Итог', '',
             ('Все обязательные проверки выполнены.' if passed else 'Проверка не пройдена полностью; подробности ниже.'), '',
             ('Эталоны в tests/fixtures сохранены без изменения байтов.' if not integrity else
              'Контрольные суммы оригиналов изменились; см. ошибки.'), '',
             '## Область проверки', '',
             '- Исходный EDA: каждое origin_cell сохранено ровно один раз, текст — с явно разрешёнными редакторскими правками; вложения и сохранённые outputs не изменены.',
             '- Упорядоченный AST исходного EDA сравнивается с эталоном; нормализуется путь data → dataset и явно перенесённые в HTML описания столбцов.',
             '- Новый исполняемый анализ следует после исходных ячеек и не вклинивается в EDA.',
             '- Статические HTML-таблицы описаний не считаются вычисляемыми результатами. При сравнении original/legacy исключены только прежние словари описаний и текстовые столбцы; численные таблицы и типы признаков сравниваются.',
             '- Новые методы обучения намеренно не сравниваются со старым notebook, в котором их не было.',
             '- Полная автономная сборка сравнивается с текущими модульными исходниками: таблицы, численные значения и данные графиков.',
             '- Проверяются контракты разделения данных, симметрии матрицы, выбора по validation и итоговых test-метрик.', '',
             '## Этапы', '']
    lines += [f"- `{s['file']}` — {s['title']}" for s in manifest.get('stages', manifest['sections'])]
    lines += ['', '## Выполненные проверки', '']
    if not integrity:
        lines.append('- SHA-256 обоих неизменяемых эталонов совпал с манифестом.')
    if not structure:
        lines.append('- Структура и сохранность исходного EDA подтверждены; свежая сборка соответствует исходникам.')
    if stored_outputs:
        lines.append('- Сохранённые outputs совпадают с ожидаемыми: устаревшие таблицы описаний в трёх изменённых ячейках очищены, остальные сохранены.' if manifest.get('static_description_tables') else '- Старые сохранённые outputs ячеек EDA не изменены.')
    for label, run in runs.items():
        if run['status'] == 'passed':
            lines.append(f"- `{label}`: чистый kernel, таблиц {run['counts']['tables']}, фигур {run['counts']['plots']}, объектов данных {run['counts']['values']}.")
    for left, right in pairs:
        if all(runs[name]['status'] == 'passed' for name in [left, right]) and not any(d.startswith(f'{left}/{right}:') for d in differences):
            lines.append(f'- `{left}` / `{right}`: численные результаты совпадают (rtol=1e-9, atol=1e-11).')
    if runs['generated']['status'] == 'passed':
        lines.append('- Автономная сборка выполнена в изолированном каталоге с dataset/, без исходников проекта и PYTHONPATH.')
    lines += ['', '## Ошибки', '']
    issues = integrity + structure + differences
    issues += [f"{label}: {run['error']}" for label, run in runs.items() if run['status'] == 'failed']
    lines += ['- ' + issue for issue in issues] if issues else ['Нет.']
    lines += ['', '## Недоступные проверки', '']
    unavailable = [f"{label}: {run['error']}" for label, run in runs.items() if run['status'] == 'unavailable']
    lines += ['- ' + issue for issue in unavailable] if unavailable else ['Нет.']
    lines += ['', '## Границы', '',
              '- Исходный data.sample() выполняется с seed=42 в одинаковом тестовом harness; код EDA не менялся.',
              '- История IPython, Axes и случайные UUID Styler не сравниваются; табличные данные и геометрия графиков сравниваются.',
              '- Проверка не является доказательством корректности на любых будущих входах или качества в другом банке.',
              '- Ядра Jupyter требуют локальных портов. Ошибки среды не выдаются за успешную проверку.', '',
              '## Окружение', '', f'- Python: `{sys.version.split()[0]}`',
              f'- Интерпретатор: `{sys.executable}`',
              f"- SHA-256 эталона: `{manifest['baseline_sha256']}`", '',
              'Подробности: `tmp/reports/validation/` (выполненные notebooks, снимки, environment.json, status.json).', '']
    settings = validation_settings(root) if (root / 'config/testing/validation.json').exists() else {'report': 'tmp/reports/validation_report.md'}
    report_path = root / settings['report']
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    return passed
