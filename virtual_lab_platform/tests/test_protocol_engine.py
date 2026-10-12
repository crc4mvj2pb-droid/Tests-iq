import unittest
from protocol_engine import validate_protocol, execute_protocol

class ProtocolEngineTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "name": "test protocol",
            "components": ["water"],
            "equipment": ["beaker", "thermometer"],
            "protocol_steps": [
                {"id":"mix", "action":"Prepare mixture", "equipment_id":"beaker", "duration_s":10},
                {"id":"measure", "action":"Measure temperature", "equipment_id":"thermometer", "duration_s":5},
            ],
            "edges": [{"from":"mix","to":"measure"}],
            "material_flows": [{"component_id":"water","from_step":"mix","to_step":"measure","amount":10,"unit":"mL"}],
            "measurements": [{"step_id":"measure","kind":"temperature","equipment_id":"thermometer","label":"Temperature","unit":"°C"}]
        }
    def test_valid_protocol_has_order_and_hash(self):
        out = validate_protocol(self.base)
        self.assertTrue(out["valid"])
        self.assertEqual(out["execution_order"], ["mix","measure"])
        self.assertEqual(len(out["protocol_sha256"]), 64)
    def test_incompatible_instrument_is_rejected(self):
        req = dict(self.base)
        req["equipment"] = ["beaker"]
        req["protocol_steps"] = [
            {"id":"mix","action":"Prepare mixture","equipment_id":"beaker","duration_s":0},
            {"id":"measure","action":"Measure temperature","equipment_id":"beaker","duration_s":0}
        ]
        req["measurements"] = [{"step_id":"measure","kind":"temperature","equipment_id":"beaker","label":"Temperature"}]
        out = validate_protocol(req)
        self.assertFalse(out["valid"])
        self.assertTrue(any(x["code"]=="measurement_instrument_incompatible" for x in out["issues"]))
    def test_unit_mismatch_is_rejected(self):
        req = dict(self.base)
        req["material_flows"] = [{"component_id":"water","from_step":"mix","to_step":"measure","amount":1,"unit":"g"}]
        out = validate_protocol(req)
        self.assertTrue(any(x["code"]=="flow_unit_mismatch" for x in out["issues"]))
    def test_cycles_are_rejected(self):
        req = dict(self.base)
        req["edges"] = [{"from":"mix","to":"measure"},{"from":"measure","to":"mix"}]
        out = validate_protocol(req)
        self.assertFalse(out["valid"])
        self.assertTrue(any(x["code"]=="protocol_cycle" for x in out["issues"]))
    def test_flow_requires_dependency_path(self):
        req = dict(self.base)
        req["edges"] = []
        out = validate_protocol(req)
        self.assertTrue(any(x["code"]=="flow_without_dependency" for x in out["issues"]))
    def test_execution_trace_never_fabricates_measurement(self):
        out = execute_protocol(self.base)
        self.assertEqual(out["status"], "protocol_trace_recorded")
        self.assertIsNone(out["trace"][1]["measurement_result"])
        self.assertEqual(out["total_planned_duration_s"], 15)
    def test_invalid_step_duration_rejected(self):
        req = dict(self.base)
        req["protocol_steps"] = [{"id":"x","action":"bad","duration_s":-1}]
        req["edges"] = []
        req["material_flows"] = []
        req["measurements"] = []
        self.assertFalse(validate_protocol(req)["valid"])

if __name__ == "__main__":
    unittest.main()
