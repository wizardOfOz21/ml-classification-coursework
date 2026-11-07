"""Select and run unittest suites; assertions live in tests/."""
import argparse
import unittest
from tooling import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=['unit', 'integration', 'regression', 'full'], default='unit')
    args = parser.parse_args()
    categories = ['unit', 'integration', 'regression'] if args.suite == 'full' else [args.suite]
    suite = unittest.TestSuite()
    for name in categories:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / 'tests' / name), top_level_dir=str(ROOT)))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__ == '__main__':
    main()
