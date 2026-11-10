import json
from . import ROOT


def load_config(root=ROOT):
    return json.loads((root / 'project.json').read_text())
