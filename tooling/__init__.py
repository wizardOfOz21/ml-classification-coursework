"""Project infrastructure, separate from the analytical source code."""
from pathlib import Path
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.pycache_prefix = str(ROOT / 'tmp/cache/python')
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'tmp/cache/matplotlib'))
