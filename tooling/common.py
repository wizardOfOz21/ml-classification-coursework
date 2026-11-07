import json
from . import ROOT
MANIFEST = 'config/build/project.json'

def load_manifest(root=ROOT):
    return json.loads((root / MANIFEST).read_text())

def validation_settings(root=ROOT):
    return json.loads((root / 'config/testing/validation.json').read_text())
