import unittest
from tests.regression.checks import run_equivalence

class EquivalenceTests(unittest.TestCase):
    def test_original_generated_and_modular_results_match(self):
        status = run_equivalence()
        self.assertTrue(status['passed'], status)
