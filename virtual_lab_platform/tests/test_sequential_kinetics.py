import unittest
from chemical_kinetics import simulate_reaction_network


class SequentialKineticsUITargetTests(unittest.TestCase):
    def test_sequential_a_to_b_to_c_conserves_total_concentration(self):
        request = {
            "species": [
                {"id": "A", "initial_concentration": 1.0, "atoms": {"X": 1}},
                {"id": "B", "initial_concentration": 0.0, "atoms": {"X": 1}},
                {"id": "C", "initial_concentration": 0.0, "atoms": {"X": 1}},
            ],
            "reactions": [
                {"id": "A_to_B", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.4},
                {"id": "B_to_C", "reactants": {"B": 1}, "products": {"C": 1}, "rate_constant": 0.2},
            ],
            "duration": 5.0, "dt": 0.01, "temperature_k": 298.15,
        }
        result = simulate_reaction_network(request)
        final = result["summary"]["final_concentrations"]
        self.assertEqual(set(final), {"A", "B", "C"})
        self.assertAlmostEqual(sum(final.values()), 1.0, places=7)
        self.assertTrue(all(result["summary"]["atom_balance_by_reaction"].values()))
        self.assertGreater(final["C"], 0.0)
        self.assertLess(final["A"], final["B"] + final["C"])


if __name__ == "__main__":
    unittest.main()
