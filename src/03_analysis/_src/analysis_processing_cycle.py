"""Исходник схемы для этапа 3: создаёт PNG/SVG и обновляет вложение notebook"""
from pathlib import Path
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import nbformat


def draw_box(ax, x, y, width, height, text, color):
    ax.add_patch(FancyBboxPatch((x, y), width, height,
                              boxstyle='round,pad=0.03,rounding_size=0.10',
                              facecolor=color, edgecolor='#64748b', linewidth=1.2))
    ax.text(x + width / 2, y + height / 2, text, ha='center', va='center',
            fontsize=12, color='#172b40')


def draw_arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>',
                                mutation_scale=17, linewidth=1.6, color='#475569'))


def render():
    directory = Path(__file__).resolve().parent
    notebook_path = directory.parent / '_index.ipynb'
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none',
                         'svg.hashsalt': 'analysis-processing-cycle'})
    fig, ax = plt.subplots(figsize=(10, 3.2))
    fig.patch.set_facecolor('white')
    ax.set(xlim=(0, 10), ylim=(0, 3.2))
    ax.axis('off')
    draw_box(ax, .3, 2.0, 3.0, .8, 'Анализ данных', '#e1edf8')
    draw_box(ax, 6.2, 2.0, 3.4, .8, 'Решение об обработке', '#fff1d6')
    draw_box(ax, 6.2, .3, 3.4, .8, 'Преобразование данных', '#e1f0e7')
    draw_arrow(ax, (3.35, 2.4), (6.15, 2.4))
    ax.text(4.75, 2.63, 'выбираем действие', ha='center', fontsize=10, color='#475569')
    draw_arrow(ax, (7.9, 1.96), (7.9, 1.14))
    ax.text(8.06, 1.53, 'применяем', ha='left', fontsize=10, color='#475569')
    ax.plot([6.15, 1.8, 1.8], [.7, .7, 1.52], color='#475569', linewidth=1.6)
    draw_arrow(ax, (1.8, 1.5), (1.8, 1.96))
    ax.text(3.9, .92, 'повторяем анализ', ha='center', fontsize=10, color='#475569')
    fig.subplots_adjust(left=.01, right=.99, top=.99, bottom=.01)
    png_path = directory / 'analysis_processing_cycle.png'
    svg_path = directory / 'analysis_processing_cycle.svg'
    fig.savefig(png_path, dpi=150, facecolor='white')
    fig.savefig(svg_path, facecolor='white', metadata={'Date': None})
    plt.close(fig)
    notebook = nbformat.read(notebook_path, as_version=4)
    notebook.cells[0].setdefault('attachments', {})['analysis-processing-cycle.png'] = {
        'image/png': base64.b64encode(png_path.read_bytes()).decode('ascii'),
    }
    nbformat.write(notebook, notebook_path)
    return png_path


if __name__ == '__main__':
    print(render())
