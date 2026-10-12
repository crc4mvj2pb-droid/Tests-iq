import unittest
import math
from chemical_kinetics import simulate_reaction_network, ChemicalKineticsError

class ChemicalKineticsTests(unittest.TestCase):
    def request(self):
        return {"species":[{"id":"A","initial_concentration":1.0,"atoms":{"X":1}},{"id":"B","initial_concentration":0.0,"atoms":{"X":1}}],"reactions":[{"id":"convert","reactants":{"A":1},"products":{"B":1},"rate_constant":0.4}],"duration":5.0,"dt":0.01,"temperature_k":298.15}
    def test_first_order_matches_analytical_solution_and_conserves_amount(self):
        result=simulate_reaction_network(self.request()); final=result["summary"]["final_concentrations"]
        self.assertAlmostEqual(final["A"],math.exp(-2),delta=2e-8); self.assertAlmostEqual(final["A"]+final["B"],1.0,places=8)
        self.assertTrue(result["summary"]["atom_balance_by_reaction"]["convert"])
    def test_arrhenius_temperature_increases_rate(self):
        base=self.request(); base["reactions"][0].update({"activation_energy_j_mol":45000,"reference_temperature_k":298.15})
        cold=simulate_reaction_network({**base,"temperature_k":280}); warm=simulate_reaction_network({**base,"temperature_k":330})
        self.assertLess(warm["summary"]["final_concentrations"]["A"],cold["summary"]["final_concentrations"]["A"])
    def test_rejects_unknown_species(self):
        req=self.request(); req["reactions"][0]["products"]={"C":1}
        with self.assertRaisesRegex(ChemicalKineticsError,"unknown species"): simulate_reaction_network(req)
    def test_flags_unbalanced_atom_stoichiometry(self):
        req=self.request(); req["species"][1]["atoms"]={"X":2}
        # v4.6: an unbalanced reaction is refused by default; it is simulated and flagged only on explicit request.
        with self.assertRaisesRegex(ChemicalKineticsError,"not atom-balanced"): simulate_reaction_network(req)
        req["allow_unbalanced"]=True
        result=simulate_reaction_network(req); self.assertFalse(result["summary"]["atom_balance_by_reaction"]["convert"])
        self.assertEqual(result["warnings"][0]["code"],"unbalanced_reaction")
    def test_rejects_unstable_timestep(self):
        req=self.request(); req["reactions"][0]["rate_constant"]=100; req["duration"]=1; req["dt"]=1
        with self.assertRaisesRegex(ChemicalKineticsError,"Negative concentration"): simulate_reaction_network(req)

if __name__=="__main__": unittest.main()
