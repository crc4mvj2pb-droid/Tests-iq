import unittest
from models import execute_model
from engine import run_experiment

class SolverTests(unittest.TestCase):
    def test_enzyme_monotonic_and_bounded(self):
        r=execute_model("enzyme_kinetics", {"vmax":1.2,"km":0.8,"s_max":6.4,"points":21})
        self.assertTrue(all(r["checks"].values()))
        self.assertEqual(len(r["rows"]),21)

    def test_sir_population_approximately_conserved(self):
        r=execute_model("sir_epidemic", {"population":10000,"beta":0.3,"gamma":0.1,"initial_infected":10,"days":160,"dt":0.1})
        self.assertTrue(r["checks"]["compartments_nonnegative"])
        self.assertTrue(r["checks"]["population_approximately_conserved"])

    def test_heat_diffusion_stability_guard(self):
        with self.assertRaisesRegex(ValueError, "unstable"):
            execute_model("heat_diffusion_1d", {"length_m":1,"diffusivity_m2_s":1e-5,"left_temp_c":100,"right_temp_c":20,"initial_temp_c":20,"nodes":21,"dt_s":200,"total_time_s":1000})

    def test_heat_diffusion_stable_run(self):
        r=execute_model("heat_diffusion_1d", {"length_m":1,"diffusivity_m2_s":1e-5,"left_temp_c":100,"right_temp_c":20,"initial_temp_c":20,"nodes":21,"dt_s":1,"total_time_s":1000})
        self.assertTrue(all(r["checks"].values()))

    def test_cosmetics_is_not_falsely_simulated(self):
        r=execute_model("cosmetic_formulation", {})
        self.assertEqual(r["validation_level"],"L0")
        self.assertEqual(r["status"],"not_simulated")
        self.assertEqual(r["rows"],[])

    def test_engine_dossier_has_hash_and_limitations(self):
        d=run_experiment({"name":"test","question":"does it work?","model_id":"enzyme_kinetics","parameters":{"vmax":1,"km":1,"s_max":2,"points":3}})
        self.assertEqual(len(d["configuration_sha256"]),64)
        self.assertIn("limitations",d["result"])

    def test_invalid_enzyme_parameters_rejected(self):
        with self.assertRaises(ValueError):
            execute_model("enzyme_kinetics", {"vmax":0,"km":1,"s_max":2,"points":3})

if __name__ == "__main__":
    unittest.main()


class ValidationAndPlannerTests(unittest.TestCase):
    def test_reference_comparison_exact_match(self):
        from validation import compare_to_reference
        predictions = [{"x":0.0,"y":0.0},{"x":1.0,"y":1.0},{"x":2.0,"y":1.5}]
        reference = [{"x":0.0,"y":0.0},{"x":1.0,"y":1.0},{"x":2.0,"y":1.5}]
        out = compare_to_reference(predictions, reference)
        self.assertAlmostEqual(out["metrics"]["rmse"], 0.0)
        self.assertEqual(out["number_of_comparison_points"], 3)

    def test_reference_comparison_forbids_extrapolation_by_overlap(self):
        from validation import compare_to_reference
        predictions = [{"x":0.0,"y":0.0},{"x":1.0,"y":1.0},{"x":2.0,"y":2.0},{"x":3.0,"y":3.0}]
        reference = [{"x":1.0,"y":1.0},{"x":2.0,"y":2.0}]
        out = compare_to_reference(predictions, reference)
        self.assertEqual(out["number_of_comparison_points"], 2)

    def test_reference_comparison_rejects_duplicate_x(self):
        from validation import compare_to_reference
        with self.assertRaisesRegex(ValueError, "unique"):
            compare_to_reference([{"x":0,"y":0},{"x":1,"y":1}], [{"x":0,"y":0},{"x":0,"y":1}])

    def test_sweep_returns_each_parameter_setting(self):
        from planner import plan_enzyme_sweep
        out = plan_enzyme_sweep({"vmax":1.2,"km":0.8,"s_max":2,"points":3}, "km", [0.5,1.0])
        self.assertEqual(out["status"], "sweep_completed")
        self.assertEqual(len(out["rows"]), 6)



class HistoryTests(unittest.TestCase):
    def test_history_store_round_trip(self):
        import tempfile
        import history
        from pathlib import Path
        old_path = history.DB_PATH
        try:
            with tempfile.TemporaryDirectory() as tmp:
                history.DB_PATH = Path(tmp) / "history.sqlite3"
                saved = history.save_experiment({
                    "model_id": "test_model",
                    "title": "test record",
                    "configuration_hash": "abc",
                    "status": "completed",
                    "rows": [{"x": 1, "y": 2}]
                })
                self.assertEqual(len(history.list_experiments()), 1)
                loaded = history.get_experiment(saved["id"])
                self.assertEqual(loaded["title"], "test record")
                self.assertEqual(loaded["rows"][0]["y"], 2)
        finally:
            history.DB_PATH = old_path



class AnalysisToolsTests(unittest.TestCase):
    def test_uncertainty_is_reproducible(self):
        from analysis_tools import enzyme_uncertainty
        params = {"vmax": 1.2, "km": 0.8, "s_max": 2, "points": 4}
        a = enzyme_uncertainty(params, {"vmax": 0.05, "km": 0.04}, samples=120, seed=9)
        b = enzyme_uncertainty(params, {"vmax": 0.05, "km": 0.04}, samples=120, seed=9)
        self.assertEqual(a["rows"], b["rows"])
        self.assertGreaterEqual(a["accepted_samples"], 100)

    def test_sensitivity_returns_both_parameters(self):
        from analysis_tools import enzyme_local_sensitivity
        out = enzyme_local_sensitivity({"vmax": 1.2, "km": 0.8, "s_max": 2, "points": 4})
        self.assertEqual({r["parameter"] for r in out["rows"]}, {"vmax", "km"})

    def test_provenance_hash_is_stable(self):
        from provenance import create_provenance_record
        a = create_provenance_record("enzyme_kinetics", "demo-1", {"vmax": 1.2})
        b = create_provenance_record("enzyme_kinetics", "demo-1", {"vmax": 1.2})
        self.assertEqual(a["record_sha256"], b["record_sha256"])

    def test_csv_parser_rejects_non_finite(self):
        from provenance import parse_xy_csv
        with self.assertRaisesRegex(ValueError, "non-finite"):
            parse_xy_csv("x,y\n0,1\n1,nan")


class AdapterTests(unittest.TestCase):
    def test_adapter_metadata_validation(self):
        from adapters import validate_adapter_metadata
        errors = validate_adapter_metadata({"model_id": "demo"})
        self.assertIn("Missing required adapter field: version", errors)


class ExperimentDesignTests(unittest.TestCase):
    def test_design_ranking_returns_valid_designs(self):
        from design import rank_enzyme_experiments
        out = rank_enzyme_experiments({"vmax": 1.2, "km": 0.8}, [0.1, 0.2, 0.5, 0.8, 1.2], 3, 0.05, 3)
        self.assertEqual(out["status"], "exploratory_design_ranking")
        self.assertEqual(len(out["ranked_designs"]), 3)
        self.assertEqual(len(out["ranked_designs"][0]["concentrations"]), 3)

    def test_design_rejects_duplicate_candidates(self):
        from design import rank_enzyme_experiments
        with self.assertRaisesRegex(ValueError, "unique"):
            rank_enzyme_experiments({"vmax": 1.2, "km": 0.8}, [0.1, 0.1, 1.0], 2)


class ScientificLibraryTests(unittest.TestCase):
    def test_catalog_has_sources_and_limitations_fields(self):
        import json
        from pathlib import Path
        catalog = json.loads((Path(__file__).resolve().parents[1] / "scientific_library" / "catalog.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(catalog["entries"]), 3)
        for entry in catalog["entries"]:
            self.assertIn("status", entry)
            self.assertIn("limitations", entry)
            self.assertIn("source", entry)
            self.assertIsNotNone(entry["id"])


class ScientificSourceRegistryTests(unittest.TestCase):
    def test_source_registry_has_cautious_import_status(self):
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / "scientific_library" / "sources.json"
        registry = json.loads(path.read_text(encoding="utf-8"))
        ids = {source["id"] for source in registry["sources"]}
        self.assertTrue({"biomodels", "sbml_test_suite", "sedml"}.issubset(ids))
        self.assertTrue(all("verification_status" in source for source in registry["sources"]))
