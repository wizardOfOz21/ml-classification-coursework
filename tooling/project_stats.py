"""Print five project metrics, respecting Git's ignore rules."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    result = subprocess.run(
        ['git', '-C', str(ROOT), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        check=True, capture_output=True,
    )
    files = sorted({ROOT / name.decode('utf-8', errors='surrogateescape')
                    for name in result.stdout.split(b'\0') if name})
    files = [path for path in files if path.is_file() and not path.is_symlink()]
    size = code_lines = text_lines = notebooks = 0
    for path in files:
        size += path.stat().st_size
        if path.suffix == '.ipynb':
            notebooks += 1
            notebook = json.loads(path.read_text(encoding='utf-8'))
            for cell in notebook['cells']:
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)
                count = len(source.splitlines())
                if cell['cell_type'] == 'code':
                    code_lines += count
                elif cell['cell_type'] in {'markdown', 'raw'}:
                    text_lines += count
        elif path.suffix == '.py':
            code_lines += len(path.read_text(encoding='utf-8').splitlines())
        elif path.suffix in {'.md', '.txt'}:
            text_lines += len(path.read_text(encoding='utf-8').splitlines())
    print(f'Размер файлов: {size / 1024**2:.2f} МиБ')
    print(f'Файлов: {len(files)}')
    print(f'Notebooks: {notebooks}')
    print(f'Строк кода: {code_lines}')
    print(f'Строк текста: {text_lines}')


if __name__ == '__main__':
    main()
