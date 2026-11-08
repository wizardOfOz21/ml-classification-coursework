import unittest
from tests.regression.checks import run_equivalence

class EquivalenceTests(unittest.TestCase):
    def test_legacy_is_preserved_and_full_sources_match(self):
        status = run_equivalence()
        self.assertTrue(status['passed'], status)
