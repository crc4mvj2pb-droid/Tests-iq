import unittest
from sbml_sweeps import sweep_sbml
from sbml_engine import SBMLSimulationError

class SBMLSweepTests(unittest.TestCase):
    def test_sweep_runs_multiple_parameter_values(self):
        out = sweep_sbml("sbml_601a5142c62cd150", 5, 0.01, "k", [0.1, 0.2, 0.4])
        self.assertEqual(out["comparison"]["run_count"], 3)
        b_values = [r["B"] for r in out["comparison"]["rows"]]
        self.assertEqual(b_values, sorted(b_values))
    def test_rejects_duplicate_values(self):
        with self.assertRaises(SBMLSimulationError):
            sweep_sbml("sbml_601a5142c62cd150", 5, 0.01, "k", [0.1, 0.1])
    def test_rejects_unknown_parameter(self):
        with self.assertRaises(SBMLSimulationError):
            sweep_sbml("sbml_601a5142c62cd150", 5, 0.01, "nope", [0.1, 0.2])
    def test_bounds_number_of_values(self):
        with self.assertRaises(SBMLSimulationError):
            sweep_sbml("sbml_601a5142c62cd150", 5, 0.01, "k", [0.1])

if __name__ == "__main__":
    unittest.main()
