"""Static statistics for the actual serialized notebook artifact, without dependencies."""
import ast
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import tokenize

import nbformat


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.ignored += 1
        if tag == 'img' and not self.ignored:
            self.parts.append(dict(attrs).get('alt', ''))

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def readable_text(source):
    """Approximate prose volume, not a full Markdown/LaTeX renderer."""
    parser = _Text()
    parser.feed(source)
    parser.close()
    text = ' '.join(parser.parts)
    text = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'(?m)^\s{0,3}#{1,6}\s+', '', text)
    text = re.sub(r'(?m)^\s*(?:[-+*>]|\d+[.)])\s+', '', text)
    text = re.sub(r'(?m)^\s*\|?\s*:?-{3,}.*$', '', text)
    text = re.sub(r'[`*_~|]', '', text)
    return ' '.join(text.split())


class _Decisions(ast.NodeVisitor):
    """One scope: nested def/lambda bodies are measured independently."""
    def __init__(self):
        self.decisions = 0
        self.depth = 0
        self.max_depth = 0

    def visit_FunctionDef(self, node):
        pass

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

    def _body(self, nodes):
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        for node in nodes:
            self.visit(node)
        self.depth -= 1

    def visit_If(self, node):
        self.decisions += 1
        self.visit(node.test)
        self._body(node.body)
        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            self.visit(node.orelse[0])  # elif is not an extra nested block
        elif node.orelse:
            self._body(node.orelse)

    def visit_IfExp(self, node):
        self.decisions += 1
        self.generic_visit(node)

    def _loop(self, node):
        self.decisions += 1
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        self.generic_visit(node)
        self.depth -= 1

    visit_For = _loop
    visit_AsyncFor = _loop
    visit_While = _loop

    def visit_BoolOp(self, node):
        self.decisions += len(node.values) - 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.decisions += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.decisions += 1
        self._body(node.body)
        if node.type is not None:
            self.visit(node.type)

    def visit_comprehension(self, node):
        self.decisions += 1 + len(node.ifs)
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        self.generic_visit(node)
        self.depth -= 1

    def visit_Match(self, node):
        self.visit(node.subject)
        for case in node.cases:
            default = isinstance(case.pattern, ast.MatchAs) and case.pattern.pattern is None
            self.decisions += int(not default) + int(case.guard is not None)
            if case.guard is not None:
                self.visit(case.guard)
            self._body(case.body)

    def _block(self, node):
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        self.generic_visit(node)
        self.depth -= 1

    visit_Try = _block
    visit_TryStar = _block
    visit_With = _block
    visit_AsyncWith = _block


class _Functions(ast.NodeVisitor):
    def __init__(self, cell):
        self.cell = cell
        self.scope = []
        self.items = []

    def _function(self, node):
        name = node.name if not isinstance(node, ast.Lambda) else f'<lambda:{node.lineno}:{node.col_offset}>'
        visitor = _Decisions()
        body = node.body if not isinstance(node, ast.Lambda) else [node.body]
        for statement in body:
            visitor.visit(statement)
        self.items.append({
            'name': '.'.join([*self.scope, name]), 'cell': self.cell, 'line': node.lineno,
            'lines': node.end_lineno - node.lineno + 1,
            'complexity': 1 + visitor.decisions, 'nesting': visitor.max_depth,
            'lambda': isinstance(node, ast.Lambda),
        })
        self.scope.append(name)
        self.generic_visit(node)
        self.scope.pop()

    visit_FunctionDef = _function
    visit_AsyncFunctionDef = _function
    visit_Lambda = _function

    def visit_ClassDef(self, node):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()


def notebook_statistics(notebook):
    markdown = [cell.source for cell in notebook.cells if cell.cell_type == 'markdown']
    code = [cell.source for cell in notebook.cells if cell.cell_type == 'code']
    prose = [readable_text(source) for source in markdown]
    functions = []
    top = _Decisions()
    statements = classes = imports = calls = comments = 0
    for number, cell in enumerate(notebook.cells, 1):
        if cell.cell_type != 'code':
            continue
        tree = ast.parse(cell.source)
        collector = _Functions(number)
        collector.visit(tree)
        functions.extend(collector.items)
        top.visit(tree)
        statements += sum(isinstance(node, ast.stmt) for node in ast.walk(tree))
        classes += sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
        imports += sum(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
        calls += sum(isinstance(node, ast.Call) for node in ast.walk(tree))
        comments += len({token.start[0] for token in tokenize.generate_tokens(io.StringIO(cell.source).readline)
                         if token.type == tokenize.COMMENT})
    text_chars = sum(map(len, markdown))
    code_chars = sum(map(len, code))
    clean_chars = sum(map(len, prose))
    output_cells = [cell for cell in notebook.cells if cell.cell_type == 'code']
    output_blocks = [output for cell in output_cells for output in cell.get('outputs', [])]
    return {
        'cells': len(notebook.cells), 'markdown_cells': len(markdown), 'code_cells': len(code),
        'raw_cells': sum(cell.cell_type == 'raw' for cell in notebook.cells),
        'markdown_characters': text_chars, 'code_characters': code_chars,
        'readable_text_characters': clean_chars,
        'markdown_bytes': sum(len(s.encode('utf-8')) for s in markdown),
        'code_bytes': sum(len(s.encode('utf-8')) for s in code),
        'source_text_to_code': text_chars / code_chars if code_chars else None,
        'readable_text_to_code': clean_chars / code_chars if code_chars else None,
        'text_share': 100 * text_chars / (text_chars + code_chars) if text_chars + code_chars else 0,
        'code_share': 100 * code_chars / (text_chars + code_chars) if text_chars + code_chars else 0,
        'text_words': sum(len(re.findall(r'[^\W\d_]+(?:[-’\'][^\W\d_]+)*', text)) for text in prose),
        'markdown_lines': sum(len(s.splitlines()) for s in markdown),
        'code_lines': sum(len(s.splitlines()) for s in code),
        'code_nonblank_lines': sum(bool(line.strip()) for s in code for line in s.splitlines()),
        'comment_lines': comments, 'statements': statements, 'classes': classes,
        'imports': imports, 'calls': calls, 'functions': functions,
        'module_complexity': 1 + top.decisions if statements else 0,
        'max_nesting': max([top.max_depth, *(f['nesting'] for f in functions)]),
        'executed_cells': sum(cell.get('execution_count') is not None for cell in output_cells),
        'output_blocks': len(output_blocks),
        'error_outputs': sum(o.output_type == 'error' for o in output_blocks),
        'images': sum(any(mime.startswith('image/') for mime in o.get('data', {})) for o in output_blocks),
        'attachments': sum(len(cell.get('attachments', {})) for cell in notebook.cells),
        'outputs_bytes': len(json.dumps(output_blocks, ensure_ascii=False, separators=(',', ':')).encode('utf-8')),
    }


def write_statistics(notebook_path):
    path = Path(notebook_path)
    notebook = nbformat.read(path, as_version=4)
    data = path.read_bytes()
    stats = notebook_statistics(notebook)
    functions = stats['functions']
    complexities = [f['complexity'] for f in functions]
    ratio = lambda value: f'{value:.2f}:1' if value is not None else 'не определено — нет кода'
    size = lambda value: f'{value} байт ({value / 1024:.2f} КиБ)'
    lines = [
        f'Статистика сборки {path.name}', '',
        f'Размер файла: {size(len(data))}',
        f'SHA-256: {hashlib.sha256(data).hexdigest()}', '',
        'Ячейки и сохранённые результаты',
        f"Всего ячеек: {stats['cells']}",
        f"Markdown / код / raw: {stats['markdown_cells']} / {stats['code_cells']} / {stats['raw_cells']}",
        f"Кодовых ячеек с номером выполнения: {stats['executed_cells']} из {stats['code_cells']}",
        f"Блоков вывода: {stats['output_blocks']}; ошибок: {stats['error_outputs']}",
        f"Изображений в выводах: {stats['images']}; вложений в ячейки: {stats['attachments']}",
        f"Объём результатов в компактном JSON: {size(stats['outputs_bytes'])}",
        'Данные о выполнении взяты из сохранённого состояния ячеек', '',
        'Объём текста и кода',
        f"Markdown: {stats['markdown_characters']} символов, {stats['markdown_lines']} строк, {size(stats['markdown_bytes'])}",
        f"Код: {stats['code_characters']} символов, {stats['code_lines']} строк, {size(stats['code_bytes'])}",
        f"Доли исходников по символам: текст {stats['text_share']:.1f}%, код {stats['code_share']:.1f}%",
        f"Соотношение Markdown/код по символам: {ratio(stats['source_text_to_code'])}",
        f"Текст после очистки разметки, приблизительно: {stats['readable_text_characters']} символов, {stats['text_words']} слов",
        f"Соотношение очищенного текста/кода: {ratio(stats['readable_text_to_code'])}",
        'Первое соотношение включает HTML-разметку Markdown-ячеек',
        'Во втором убраны HTML-теги и основная Markdown-разметка; формулы считаются по их записи',
        'Строковые литералы и комментарии Python входят в объём кода',
        'Выводы ячеек, картинки и вложения в соотношении текста и кода не участвуют', '',
        'Структура и сложность Python-кода',
        f"Непустых строк кода: {stats['code_nonblank_lines']}; строк с комментариями: {stats['comment_lines']}",
        f"Инструкций AST: {stats['statements']}; вызовов: {stats['calls']}; импортов: {stats['imports']}",
        f"Функций def: {sum(not f['lambda'] for f in functions)}; lambda: {sum(f['lambda'] for f in functions)}; классов: {stats['classes']}",
        f"Цикломатическая сложность верхнего уровня: {stats['module_complexity']}",
        f"Средняя сложность функций и lambda: {sum(complexities) / len(complexities) if complexities else 0:.2f}",
        f"Максимальная сложность функции: {max(complexities, default=0)}",
        f"Максимальная вложенность управляющих блоков по AST: {stats['max_nesting']}", '',
        'Наиболее сложные функции',
    ]
    for function in sorted(functions, key=lambda f: (-f['complexity'], -f['lines'], f['name']))[:10]:
        lines.append(f"{function['name']}: сложность {function['complexity']}, строк {function['lines']}, вложенность {function['nesting']}; ячейка {function['cell']}, строка {function['line']}")
    if not functions:
        lines.append('Функций нет')
    lines += ['', 'Номера ячеек указаны по порядку в notebook, начиная с 1; строки — внутри соответствующей ячейки', '', 'Как считается сложность',
              'Оценочная цикломатическая сложность = 1 + число развилок в отдельной функции',
              'Учитываются if и условные выражения, циклы, except, assert, and/or, генераторы и ветви match',
              'Вложенные def/lambda считаются отдельно, без повторного включения в сложность внешней функции',
              'Верхний уровень измеряется как одна последовательность всех кодовых ячеек',
              'AST — синтаксическое дерево Python; глубина отражает вложенность управляющих блоков',
              'Это статические показатели структуры кода, а не оценка качества анализа или скорости выполнения', '']
    report = path.with_suffix('.stats.txt')
    report.write_text('\n'.join(lines), encoding='utf-8')
    return report
