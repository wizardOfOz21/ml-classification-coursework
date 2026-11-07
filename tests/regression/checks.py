import copy, hashlib, importlib.metadata, json, sys, warnings
from pathlib import Path
import nbformat
from tooling.common import ROOT, load_manifest, validation_settings
from tooling.build.builder import build_notebook
from tooling.execution.executor import execute, modular_notebook
from tooling.testing.reporting import write_report
from tests.support.comparison import compare_structure, compare_values
warnings.filterwarnings('ignore', category=nbformat.warnings.MissingIDFieldWarning)

def layout_baseline(notebook):
    adjusted = copy.deepcopy(notebook)
    for cell in adjusted.cells:
        if cell.cell_type == 'code':
            cell.source = cell.source.replace('./data/credit_risk_dataset.csv', './dataset/credit_risk_dataset.csv')
    return adjusted

def run_equivalence(root=ROOT, timeout=None):
    settings = validation_settings(root)
    timeout = timeout or settings['timeout']
    artifacts = root / settings['artifacts']
    artifacts.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(root)
    packages = ['pandas', 'numpy', 'scipy', 'scikit-learn', 'matplotlib', 'seaborn', 'ipython', 'nbformat', 'nbclient', 'ipykernel', 'jupyter-client']
    environment = {'python': sys.version, 'executable': sys.executable, 'packages': {p: importlib.metadata.version(p) for p in packages}}
    (artifacts / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    integrity = []
    for name, expected in [(manifest['baseline'], manifest['baseline_sha256']), (manifest['archived_working'], manifest['archived_working_sha256'])]:
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            integrity.append(f'Original hash changed: {name}')
    # Validation always checks a freshly assembled candidate
    build_notebook(root, root / settings['generated'])
    original = nbformat.read(root / manifest['baseline'], as_version=4)
    generated = nbformat.read(root / settings['generated'], as_version=4)
    rebuilt = build_notebook(root)
    structure = compare_structure(layout_baseline(original), generated)
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
            runs[label] = execute(notebook, label, root, artifacts, isolated, timeout)
            print(f"{label}: {runs[label]['status']} {runs[label].get('counts', {})}", flush=True)
    differences = []
    for left, right in [('original', 'generated'), ('original', 'modular')]:
        if all(runs[name]['status'] == 'passed' for name in [left, right]):
            differences.extend(f'{left}/{right}: {s}' for s in compare_values(runs[left]['snapshot'], runs[right]['snapshot']))
    passed = write_report(root, manifest, structure, integrity, runs, differences, stored_outputs)
    status = {'passed': passed, 'integrity_errors': integrity, 'structural_errors': structure,
              'differences': differences, 'runs': {k: {a: b for a, b in v.items() if a != 'snapshot'} for k, v in runs.items()}}
    (artifacts / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
    print(f'{"PASS" if passed else "NOT VERIFIED"}: {root / settings["report"]}')
    return status
