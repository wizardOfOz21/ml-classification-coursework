"""Render collected check results; definitions of checks belong to tests/."""
import sys
from tooling.common import validation_settings

def write_report(root, manifest, structure, integrity, runs, differences, stored_outputs):
    passed = not structure and not integrity and not differences and all(r['status'] == 'passed' for r in runs.values())
    lines = ['# Проверка модульной сборки solution.ipynb', '',
             '## Итог', '',
             ('Все обязательные проверки выполнены: расчёты и результаты совпадают с эталоном; новая структура текста проверена отдельно.' if passed else
              'Эквивалентность не подтверждена полностью: ниже разделены расхождения и недоступные проверки.'), '',
             ('Оба исходных notebook сохранены без изменения байтов в tests/fixtures; рабочие исходники находятся в src/.' if not integrity else
              'Контрольные суммы оригиналов изменились относительно эталона; подробности указаны в расхождениях.'), '',
             '## Выделенные разделы', '']
    lines += [f"- `{s['file']}` — {s['title']}" for s in manifest.get('stages', manifest['sections'])]
    lines += ['', '## Вынесенные определения и сборка', '',
              '- Крупные кодовые ячейки хранятся в соседних с notebook подпапках `_code/`, исходные глобальные зависимости сохранены',
              '- Файлы `index.ipynb` включают этапы и подэтапы по порядку, сборщик рекурсивно раскрывает их',
              '- Манифест задаёт порядок разделов, метаданные и контрольную сумму исходника',
              '- Вспомогательные определения встраиваются на место объявленных загрузчиков; служебные bootstrap-ячейки исключаются',
              '- Структура кода проверяется по полному упорядоченному AST, а не по числу ячеек',
              '- Существующие выводы ячеек при сборке сохраняются; результаты проверочных запусков записываются отдельно', '',
              '## Успешные проверки', '']
    if not integrity:
        lines.append('- SHA-256 резервной копии и рабочего оригинала совпадает с зафиксированным исходником')
    if not structure:
        lines.append('- Все исходные ячейки представлены ровно один раз, их текст сохранён с явно заданной перенумерацией; вложенные изображения и outputs сохранены; упорядоченный AST вычислений совпадает')
    if stored_outputs:
        lines.append('- Сохранённые до запуска выводы всех исходных ячеек перенесены без изменения')
    for label, run in runs.items():
        if run['status'] == 'passed':
            lines.append(f"- `{label}`: новый Jupyter kernel, все ячейки выполнены; таблиц {run['counts']['tables']}, графиков {run['counts']['plots']}, объектов данных {run['counts']['values']}")
    for left, right in [('original', 'generated'), ('original', 'modular')]:
        if all(runs[name]['status'] == 'passed' for name in [left, right]) and not any(d.startswith(f'{left}/{right}:') for d in differences):
            lines.append(f'- `{left}` / `{right}`: совпали отображённые таблицы, численные объекты и данные графиков; rtol=1e-9, atol=1e-11')
    if runs['generated']['status'] == 'passed':
        lines.append('- Автономность: generated выполнен в отдельном временном каталоге с данными, без src/, tooling/, tests/ и config/ и без PYTHONPATH проекта')
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
              '- Ядра Jupyter используют локальные порты; недоступные запуски отдельно отмечаются выше',
              '- При сравнении AST явно нормализован единственный разрешённый путь ./data/credit_risk_dataset.csv → ./dataset/credit_risk_dataset.csv; эталонный файл не изменён',
              '- История команд IPython и ссылки на объекты Axes исключены из снимков: они зависят от сессии, данные графиков сравниваются отдельно',
              '- Случайные UUID HTML Styler не сравниваются; сравниваются исходные отображённые таблицы',
              '- Для графиков сравниваются массивы, линии, геометрия, цвета, подписи, шкалы и пределы осей; побайтовое совпадение PNG не требуется',
              '- Сравнение охватывает итоговые DataFrame/Series/Index/массивы, простые структуры данных и скаляры; в том числе association_matrix, nmi_estimates, kruskal_effects и train/validation/test',
              '- Выбор модели и этапы 4–7 содержат контракты, но не реализацию; моделей и метрик обучения пока нет',
              '- Перенумерация текста задана в config/build/documentation-edits.json; новые вводные блоки, оглавление и копия assignment.txt проверяются отдельно',
              '- Это воспроизводимая проверка данной работы, не формальное доказательство эквивалентности на произвольных будущих данных', '',
              '## Окружение', '', f'- Python: `{sys.version.split()[0]}`',
              f'- Интерпретатор: `{sys.executable}`',
              f"- SHA-256 исходника: `{manifest['baseline_sha256']}`", '',
              'Подробные выполненные ноутбуки, снимки результатов и JSON-статус: `tmp/reports/validation/`', '']
    settings = validation_settings(root) if (root / 'config/testing/validation.json').exists() else {'report': 'tmp/reports/validation_report.md'}
    report_path = root / settings['report']
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    return passed
