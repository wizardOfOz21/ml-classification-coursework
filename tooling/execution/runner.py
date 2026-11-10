"""Build and execute a submission notebook, retaining clean outputs."""
import argparse
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from tooling.common import ROOT, load_config
from tooling.build.builder import build_notebook, copy_dataset
from tooling.build.statistics import write_statistics


def run(timeout=300):
    output = ROOT / load_config()['output']
    notebook = build_notebook()
    copy_dataset(ROOT, output.parent)
    runs = ROOT / 'tmp/runs'
    runs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='submission-', dir=runs) as directory:
        temp = Path(directory)
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        env.update(IPYTHONDIR=str(temp / 'ipython'), JUPYTER_RUNTIME_DIR=str(temp / 'runtime'),
                   MPLBACKEND='module://matplotlib_inline.backend_inline', PYTHONHASHSEED='0')
        km = KernelManager(kernel_name='python3')
        km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
        client = NotebookClient(notebook, km=km, timeout=timeout,
                                resources={'metadata': {'path': str(output.parent)}})
        try:
            client.execute(cwd=str(output.parent), env=env)
        finally:
            if km.has_kernel:
                if client.kc is not None:
                    client.kc.stop_channels()
                km.shutdown_kernel(now=True)
    # No instrumentation, local source loaders or execution-only setup cells.
    nbformat.validate(notebook)
    output.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, output)
    write_statistics(output)
    print(f'Executed {output}: {len(notebook.cells)} cells')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    run(timeout=args.timeout)


if __name__ == '__main__':
    main()
