import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import scientific_imports as si
import sbml_engine as se

class SBMLSimulationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.base=Path(self.tmp.name)
  self.assets=self.base/"scientific_library"/"imported_assets"
  (self.assets/"models").mkdir(parents=True); (self.assets/"datasets").mkdir(parents=True)
  self.index=self.assets/"index.json"; self.index.write_text(json.dumps({"schema_version":"1.0","assets":[]}),encoding="utf-8")
  self.patches=[patch.object(si,"BASE",self.base),patch.object(si,"ASSET_DIR",self.assets),patch.object(si,"INDEX",self.index),
                patch.object(se,"BASE",self.base),patch.object(se,"ASSET_DIR",self.assets)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def _model(self):
  xml="""<sbml xmlns="http://www.sbml.org/sbml/level3/version2/core" level="3" version="2"><model id="first_order" name="First order decay">
  <listOfCompartments><compartment id="cell" size="1" constant="true"/></listOfCompartments>
  <listOfSpecies><species id="A" compartment="cell" initialAmount="10" hasOnlySubstanceUnits="true"/><species id="B" compartment="cell" initialAmount="0" hasOnlySubstanceUnits="true"/></listOfSpecies>
  <listOfParameters><parameter id="k" value="0.2" constant="true"/></listOfParameters>
  <listOfReactions><reaction id="r1"><listOfReactants><speciesReference species="A" stoichiometry="1" constant="true"/></listOfReactants><listOfProducts><speciesReference species="B" stoichiometry="1" constant="true"/></listOfProducts>
  <kineticLaw><math xmlns="http://www.w3.org/1998/Math/MathML"><apply><times/><ci>k</ci><ci>A</ci></apply></math></kineticLaw></reaction></listOfReactions></model></sbml>"""
  return si.import_sbml("first_order.xml",xml)
 def test_rk4_simulation_tracks_first_order_solution(self):
  rec=self._model(); out=se.simulate_sbml(rec["id"],2,0.01)
  final=out["summary"]["final_amounts"]
  self.assertAlmostEqual(final["A"],10*__import__("math").exp(-0.4),places=5)
  self.assertAlmostEqual(final["A"]+final["B"],10,places=6)
  self.assertTrue(out["checks"]["all_outputs_finite"])
 def test_rejects_unsupported_rule(self):
  rec=self._model()
  file=self.base/rec["stored_path"]
  txt=file.read_text().replace("<listOfReactions>","<listOfRules><assignmentRule variable='A'><math xmlns='http://www.w3.org/1998/Math/MathML'><cn>1</cn></math></assignmentRule></listOfRules><listOfReactions>")
  file.write_text(txt)
  with self.assertRaises(se.SBMLSimulationError):se.simulate_sbml(rec["id"],1,0.1)
 def test_rejects_too_many_steps(self):
  rec=self._model()
  with self.assertRaises(se.SBMLSimulationError):se.simulate_sbml(rec["id"],1000,0.001)

 def test_global_parameter_override_changes_result(self):
  rec=self._model(); base=se.simulate_sbml(rec['id'],2,0.01); faster=se.simulate_sbml(rec['id'],2,0.01,parameter_overrides={'k':0.4})
  self.assertGreater(faster['summary']['final_amounts']['B'],base['summary']['final_amounts']['B'])
  self.assertEqual(faster['parameter_values']['k'],0.4)
 def test_unknown_parameter_override_rejected(self):
  rec=self._model()
  with self.assertRaises(se.SBMLSimulationError):se.simulate_sbml(rec['id'],2,0.01,parameter_overrides={'missing':1})

if __name__=='__main__':
 unittest.main()
