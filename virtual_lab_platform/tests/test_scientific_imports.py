import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import scientific_imports as si

class ScientificImportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
  self.assets=self.base/"scientific_library"/"imported_assets"
  (self.assets/"models").mkdir(parents=True);(self.assets/"datasets").mkdir(parents=True)
  self.index=self.assets/"index.json";self.index.write_text(json.dumps({"schema_version":"1.0","assets":[]}),encoding="utf-8")
  self.patches=[patch.object(si,"BASE",self.base),patch.object(si,"ASSET_DIR",self.assets),patch.object(si,"INDEX",self.index)]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def test_import_sbml_extracts_counts(self):
  xml="""<?xml version="1.0"?><sbml xmlns="http://www.sbml.org/sbml/level3/version2/core" level="3" version="2"><model id="m" name="Demo"><listOfCompartments><compartment id="c"/></listOfCompartments><listOfSpecies><species id="s" compartment="c"/></listOfSpecies><listOfReactions><reaction id="r"/></listOfReactions></model></sbml>"""
  out=si.import_sbml("demo.xml",xml);self.assertEqual(out["metadata"]["species_count"],1);self.assertEqual(out["metadata"]["reaction_count"],1)
  self.assertEqual(out["execution_status"],"stored_not_executed");self.assertTrue((self.base/out["stored_path"]).exists())
 def test_rejects_non_sbml_and_dtd(self):
  with self.assertRaises(ValueError):si.import_sbml("x.xml","<root/>")
  with self.assertRaises(ValueError):si.import_sbml("x.xml",'<!DOCTYPE sbml [<!ENTITY x "y">]><sbml/>')
 def test_import_csv(self):
  out=si.import_dataset("data.csv","time,value\n0,1\n1,2\n")
  self.assertEqual(out["metadata"]["row_count"],2);self.assertEqual(out["metadata"]["columns"],["time","value"])
 def test_rejects_malformed_csv(self):
  with self.assertRaises(ValueError):si.import_dataset("bad.csv","a,b\n1\n")
  with self.assertRaises(ValueError):si.import_dataset("empty.csv","a,b\n")
 def test_duplicate_hash(self):
  xml="<sbml><model id='m'/></sbml>";si.import_sbml("a.xml",xml);si.import_sbml("b.xml",xml)
  self.assertEqual(len(si.list_assets()["assets"]),1)
if __name__=="__main__":unittest.main()
