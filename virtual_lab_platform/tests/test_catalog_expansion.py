import unittest
from lab_designer import CATALOG, COMPONENTS, EQUIPMENT, WORKFLOWS
from models import MODEL_CATALOG, MODEL_CATALOG_BY_ID


class ExpandedCatalogTests(unittest.TestCase):
    def test_catalog_is_expanded_and_ids_are_unique(self):
        self.assertGreaterEqual(len(CATALOG["disciplines"]), 18)
        self.assertGreaterEqual(len(COMPONENTS), 58)
        self.assertGreaterEqual(len(EQUIPMENT), 70)
        self.assertGreaterEqual(len(WORKFLOWS), 42)
        self.assertGreaterEqual(len(MODEL_CATALOG), 43)
        self.assertEqual(len(COMPONENTS), len(CATALOG["components"]))
        self.assertEqual(len(EQUIPMENT), len(CATALOG["equipment"]))
        self.assertEqual(len(WORKFLOWS), len(CATALOG["workflows"]))
        self.assertEqual(len(MODEL_CATALOG), len(MODEL_CATALOG_BY_ID))

    def test_all_workflow_requirements_reference_catalog_entries(self):
        for workflow in CATALOG["workflows"]:
            for component in workflow.get("required_components", []):
                self.assertIn(component, COMPONENTS, workflow["id"])
            for equipment in workflow.get("required_equipment", []):
                self.assertIn(equipment, EQUIPMENT, workflow["id"])

    def test_new_model_templates_do_not_claim_to_be_simulated(self):
        for model in MODEL_CATALOG:
            if model["status"] == "workflow_template":
                self.assertEqual(model["validation_level"], "L0")
                self.assertTrue("solver" in model["caveat"].lower() or "solver" in model["description"].lower() or "no " in model["caveat"].lower())


if __name__ == "__main__":
    unittest.main()
