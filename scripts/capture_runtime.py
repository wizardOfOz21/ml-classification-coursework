"""Validation-only instrumentation injected into fresh kernels, never into the build."""
import copy as __v_copy
import pickle as __v_pickle
import random as __v_random
import sys as __v_sys
from pathlib import Path as __v_Path
import numpy as __v_np
import pandas as __v_pd
import matplotlib.pyplot as __v_plt
from IPython.display import display as __v_original_display

__v_np.random.seed(42)
__v_random.seed(42)
__v_displays = []
__v_plots = []


def __v_display(*objects, **kwargs):
    for obj in objects:
        if isinstance(obj, (__v_pd.DataFrame, __v_pd.Series)):
            __v_displays.append(obj.copy(deep=True))
        elif type(obj).__name__ == 'Styler' and isinstance(obj.data, __v_pd.DataFrame):
            __v_displays.append(obj.data.copy(deep=True))
    return __v_original_display(*objects, **kwargs)


display = __v_display
__v_original_show = __v_plt.show


def __v_show(*args, **kwargs):
    for num in __v_plt.get_fignums():
        fig = __v_plt.figure(num)
        axes = []
        for ax in fig.axes:
            axes.append({
                'title': ax.get_title(), 'xlabel': ax.get_xlabel(), 'ylabel': ax.get_ylabel(),
                'xlim': ax.get_xlim(), 'ylim': ax.get_ylim(),
                'xscale': ax.get_xscale(), 'yscale': ax.get_yscale(),
                'lines': [{'xy': line.get_xydata().copy(), 'color': line.get_color(),
                           'style': line.get_linestyle()} for line in ax.lines],
                'collections': [{'array': __v_copy.deepcopy(col.get_array()),
                                 'offsets': __v_copy.deepcopy(col.get_offsets()),
                                 'paths': [path.vertices.copy() for path in col.get_paths()],
                                 'facecolors': col.get_facecolors().copy()}
                                for col in ax.collections],
                'patches': [{'vertices': patch.get_path().vertices.copy(),
                             'transform': patch.get_patch_transform().get_matrix().copy(),
                             'facecolor': patch.get_facecolor()} for patch in ax.patches],
                'images': [__v_copy.deepcopy(image.get_array()) for image in ax.images],
                'texts': [(text.get_text(), text.get_position()) for text in ax.texts],
                'xticks': [t.get_text() for t in ax.get_xticklabels()],
                'yticks': [t.get_text() for t in ax.get_yticklabels()],
            })
        __v_plots.append({'size': fig.get_size_inches().copy(), 'axes': axes})
    return __v_original_show(*args, **kwargs)


__v_plt.show = __v_show


def __v_capture(value, depth=0):
    if depth > 8:
        raise TypeError('Not a data result')
    if isinstance(value, (__v_pd.DataFrame, __v_pd.Series, __v_pd.Index)):
        return __v_copy.deepcopy(value)
    if isinstance(value, __v_np.ndarray):
        if value.dtype.hasobject:
            # Preserve actual object data (e.g. category labels), not UI handles
            for item in value.flat:
                __v_capture(item, depth + 1)
        return __v_copy.deepcopy(value)
    if value is None or isinstance(value, (str, int, float, bool, __v_np.generic)):
        return value
    if isinstance(value, dict):
        return {key: __v_capture(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        items = sorted(value) if isinstance(value, set) else value
        return [__v_capture(item, depth + 1) for item in items]
    raise TypeError('Not a data result')


def __v_finish(filename):
    values = {}
    for name, value in list(globals().items()):
        if name.startswith('_') or name in {'In', 'Out'}:
            continue
        try:
            values[name] = __v_capture(value)
        except (TypeError, ValueError):
            pass
    with open(filename, 'wb') as handle:
        __v_pickle.dump({'tables': __v_displays, 'plots': __v_plots, 'values': values}, handle)
