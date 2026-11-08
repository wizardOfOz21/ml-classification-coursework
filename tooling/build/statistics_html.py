"""Compact, self-contained HTML presentation of notebook statistics."""
from html import escape


def format_size(byte_count):
    """Decimal units, with MB strictly above 0.1 MB and no raw byte counts."""
    if byte_count > 100_000:
        return f'{byte_count / 1_000_000:.2f}'.replace('.', ',') + ' МБ'
    return f'{byte_count / 1_000:.1f}'.rstrip('0').rstrip('.').replace('.', ',') + ' КБ'


def _number(value, decimals=0):
    return f'{value:,.{decimals}f}'.replace(',', '\u202f').replace('.', ',')


def _table(headers, rows):
    heading = ''.join(f'<th scope="col">{escape(str(item))}</th>' for item in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{escape(str(item))}</td>' for item in row) + '</tr>'
                   for row in rows)
    return f'<table><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table>'


def render_statistics(notebook_name, stats, file_size, fingerprint):
    functions = stats['functions']
    complexities = [function['complexity'] for function in functions]
    summary = _table(['Показатель', 'Значение'], [
        ('Размер ноутбука', format_size(file_size)),
        ('Ячейки', f"{stats['cells']} · текст {stats['markdown_cells']} · код {stats['code_cells']}"
         + (f" · прочие {stats['raw_cells']}" if stats['raw_cells'] else '')),
        ('Сохранённые выполнения', f"{stats['executed_cells']} из {stats['code_cells']} кодовых ячеек"),
        ('Изображения', stats['images'] + stats['attachments']),
        ('Ошибки в выводах', stats['error_outputs']),
    ])
    volume = _table(['Исходники', 'Размер', 'Доля по символам'], [
        ('Текст с разметкой', format_size(stats['markdown_bytes']), _number(stats['text_share'], 1) + '%'),
        ('Python', format_size(stats['code_bytes']), _number(stats['code_share'], 1) + '%'),
    ])
    ratio = stats['readable_text_to_code']
    ratio_text = _number(ratio, 2) + ' : 1' if ratio is not None else 'не определено — нет кода'
    complexity = _table(['Показатель', 'Значение'], [
        ('Непустые строки Python', _number(stats['code_nonblank_lines'])),
        ('Функции, включая lambda', len(functions)),
        ('Средняя / максимальная сложность функций',
         f"{_number(sum(complexities) / len(complexities) if complexities else 0, 1)} / {max(complexities, default=0)}"),
        ('Максимальная вложенность блоков', stats['max_nesting']),
    ])
    top = sorted(functions, key=lambda f: (-f['complexity'], -f['lines'], f['name']))[:5]
    function_table = _table(['Функция', 'Сложность', 'Строки', 'Ячейка'], [
        (function['name'], function['complexity'], function['lines'], function['cell']) for function in top
    ]) if top else '<p>Функций нет</p>'
    frequencies = stats['word_frequencies']
    total = stats['frequency_total_words']
    word_rows = ''.join(
        f'<tr{" hidden" if index >= 30 else ""}><td>{escape(row["word"])}</td>'
        f'<td>{_number(row["total"])}</td><td>{_number(100 * row["total"] / total, 2)}%</td></tr>'
        for index, row in enumerate(frequencies)
    )
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="notebook-sha256" content="{escape(fingerprint, quote=True)}">
<title>Статистика · {escape(notebook_name)}</title>
<style>
:root {{ color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: #233047; background: #f3f5f8; line-height: 1.5 }}
* {{ box-sizing: border-box }}
body {{ margin: 0; padding: 36px 24px }}
main {{ max-width: 1080px; margin: auto }}
h1 {{ font-size: 30px; letter-spacing: -.6px; margin: 0 }}
h2 {{ font-size: 19px; margin: 0 0 16px }}
p {{ margin: 12px 0; color: #536178; font-size: 14px }}
.filename {{ margin: 6px 0 26px; overflow-wrap: anywhere }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px }}
section {{ background: white; border: 1px solid #dfe5ed; border-radius: 12px; padding: 24px;
  margin-bottom: 20px; min-width: 0 }}
.wide {{ grid-column: 1 / -1 }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px }}
th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e9edf3;
  overflow-wrap: anywhere }}
th {{ color: #536178; background: #f6f8fb; font-size: 12px; font-weight: 600 }}
td:not(:first-child), th:not(:first-child) {{ text-align: right }}
tbody tr:last-child td {{ border-bottom: 0 }}
details {{ margin-top: 16px; font-size: 14px }}
summary {{ cursor: pointer; color: #315eb2; padding: 6px 0 }}
details table {{ margin-top: 10px }}
.controls {{ display: flex; align-items: end; flex-wrap: wrap; gap: 16px; margin: 18px 0 12px }}
label {{ display: grid; gap: 5px; font-size: 13px; color: #536178 }}
input, select {{ font: inherit; color: #233047; border: 1px solid #bdc8d7; border-radius: 6px;
  background: white; padding: 8px 10px }}
input {{ width: 240px; max-width: 100% }}
.scroll {{ max-height: 440px; overflow: auto }}
.scroll th {{ position: sticky; top: 0 }}
[hidden] {{ display: none !important }}
@media (max-width: 740px) {{ .grid {{ grid-template-columns: 1fr }} body {{ padding: 20px 12px }}
  section {{ padding: 18px }} h1 {{ font-size: 26px }} th, td {{ padding: 8px }} }}
@media print {{ body {{ background: white; padding: 0 }} .controls {{ display: none }}
  .scroll {{ max-height: none; overflow: visible }} section {{ break-inside: avoid }} }}
</style>
</head>
<body><main>
<h1>Статистика сборки</h1>
<p class="filename">{escape(notebook_name)}</p>
<div class="grid">
<section><h2>Сборка</h2>{summary}
<p>Выполнения и ошибки — по сохранённым результатам ячеек</p></section>
<section><h2>Текст и код</h2>{volume}
<p>Очищенный текст / код по символам: <strong>{ratio_text}</strong></p>
<p>Без результатов вычислений и изображений</p></section>
<section class="wide"><h2>Сложность кода</h2>{complexity}
<details><summary>Пять самых сложных функций и способ подсчёта</summary>{function_table}
<p>Сложность — 1 плюс число развилок, включая условия, циклы и логические операторы.
Вложенные функции считаются отдельно.
Это оценка структуры кода, а не качества анализа</p>
<p>Ячейки пронумерованы с 1 по всему ноутбуку</p></details></section>
<section class="wide"><h2>Частотность слов</h2>
<p>{_number(total)} употреблений · {_number(len(frequencies))} разных слов и обозначений</p>
<div class="controls">
<label>Поиск слова<input id="word-search" type="search" placeholder="Например, модель"></label>
<label>Показывать<select id="word-limit"><option value="30">Первые 30</option>
<option value="100">Первые 100</option><option value="0">Все слова</option></select></label>
</div>
<p id="word-count" aria-live="polite">Показано {min(30, len(frequencies))} из {len(frequencies)}</p>
<div class="scroll"><table id="words"><thead><tr><th scope="col">Слово</th>
<th scope="col">Употребления</th><th scope="col">Доля</th></tr></thead><tbody>{word_rows}</tbody></table></div>
<details><summary>Что учитывается</summary>
<p>Текст Markdown и сохранённых выводов ячеек, без кода, формул, адресов и чисел.
Регистр не учитывается, формы слов считаются отдельно.
Повторные показы таблиц учитываются каждый раз</p>
<p>Доля — от всех употреблений, независимо от фильтра.
Для каждого вывода берётся один текстовый формат</p></details>
<noscript><p>Для поиска и просмотра слов за пределами первых 30 включите JavaScript</p></noscript>
</section></div>
</main>
<script>
const search = document.getElementById('word-search');
const limit = document.getElementById('word-limit');
const rows = Array.from(document.querySelectorAll('#words tbody tr'));
function filterWords() {{
  const query = search.value.trim().toLocaleLowerCase('ru');
  const maximum = Number(limit.value);
  let matched = 0;
  let shown = 0;
  rows.forEach(row => {{
    const matches = row.cells[0].textContent.toLocaleLowerCase('ru').includes(query);
    if (matches) matched++;
    row.hidden = !matches || (maximum > 0 && shown >= maximum);
    if (!row.hidden) shown++;
  }});
  document.getElementById('word-count').textContent = `Показано ${{shown}} из ${{matched}}`;
}}
search.addEventListener('input', filterWords);
limit.addEventListener('change', filterWords);
</script>
</body></html>
'''
