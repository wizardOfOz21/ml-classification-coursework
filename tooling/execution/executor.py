"""Execute notebooks and capture observations; no pass/fail expectations live here."""
import copy, os, pickle, shutil, sys, tempfile, traceback
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

def modular_notebook(root, manifest):
    result = nbformat.v4.new_notebook(metadata=copy.deepcopy(manifest['metadata']))
    for section in manifest['sections']:
        result.cells.extend(nbformat.read(root / section['file'], as_version=4).cells)
    return result


def execute(notebook, label, root, artifacts, isolated=True, timeout=180):
    """Each run gets a new kernel and a different working directory."""
    runtime_root = root / 'tmp/runs'
    runtime_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'notebook-{label}-', dir=runtime_root) as directory:
        temp = Path(directory)
        working = temp if isolated else root
        if isolated:
            shutil.copytree(root / 'dataset', temp / 'dataset')
            # Compatibility for immutable pre-layout reference notebooks only
            (temp / 'data').symlink_to('dataset', target_is_directory=True)
            nbformat.write(notebook, temp / 'notebook.ipynb')
            assert all(not (temp / name).exists() for name in ['src', 'tooling', 'tests', 'config', 'notebooks', 'scripts'])
        for suffix in ['snapshot.pkl', 'error.txt']:
            (artifacts / f'{label}.{suffix}').unlink(missing_ok=True)
        snapshot = temp / 'snapshot.pkl'
        runtime = (root / 'tooling/execution/capture.py').read_text()
        runtime = "get_ipython().run_line_magic('matplotlib', 'inline')\n" + runtime
        instrumented = copy.deepcopy(notebook)
        instrumented.cells.insert(0, nbformat.v4.new_code_cell(runtime))
        instrumented.cells.append(nbformat.v4.new_code_cell(f'__v_finish({str(snapshot)!r})'))
        km = KernelManager(kernel_name='python3')
        km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        env.update(IPYTHONDIR=str(temp / 'ipython'), JUPYTER_RUNTIME_DIR=str(temp / 'runtime'),
                   MPLCONFIGDIR=str(temp / 'matplotlib'), PYTHONPYCACHEPREFIX=str(temp / 'python-cache'), PYTHONHASHSEED='0', MPLBACKEND='module://matplotlib_inline.backend_inline')
        result = {'status': 'passed', 'isolated': isolated, 'cwd_has_only_data': isolated}
        client = None
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
            if km.has_kernel:
                if client is not None and client.kc is not None:
                    client.kc.stop_channels()
                km.shutdown_kernel(now=True)
            nbformat.write(instrumented, artifacts / f'{label}.executed.ipynb')
        return result
