import json
from . import ROOT
MANIFEST = 'project.json'

def load_manifest(root=ROOT):
    return json.loads((root / MANIFEST).read_text())
