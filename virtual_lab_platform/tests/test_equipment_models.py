import unittest
from equipment_models import apply_material_flow_model, apply_equipment_operating_effects
from protocol_engine import validate_protocol, execute_protocol
from lab_designer import run_lab_experiment

class EquipmentModelTests(unittest.TestCase):
    def dilution_request(self):
        return {
            "name":"Flow driven dilution",
            "discipline":"chemistry",
            "workflow_id":"solution_dilution",
            "components":["water","substrate"],
            "equipment":["beaker","pipette","pipette_10ml"],
            "steps":[{"action":"Transfer stock"},{"action":"Add diluent"}],
            "protocol_steps":[
                {"id":"stock","action":"Transfer stock","equipment_id":"pipette","duration_s":1},
                {"id":"diluent","action":"Add diluent","equipment_id":"pipette_10ml","duration_s":1},
            ],
            "edges":[{"from":"stock","to":"diluent"}],
            "material_flows":[
                {"component_id":"substrate","from_step":"stock","to_step":"diluent","amount":0.5,"unit":"mL","role":"stock","transfer_equipment_id":"pipette"},
                {"component_id":"water","from_step":"stock","to_step":"diluent","amount":9.5,"unit":"mL","role":"diluent","transfer_equipment_id":"pipette_10ml"},
            ],
            "measurements":[],
            "parameters":{"stock_concentration_mM":10,"stock_volume_ml":0.5,"diluent_volume_ml":9.5}
        }
    def test_material_flows_override_calculator_volumes(self):
        req=self.dilution_request()
        base=run_lab_experiment(req)["results"]
        out=apply_material_flow_model(req,base)
        self.assertAlmostEqual(out["stock_volume_ml"],0.5)
        self.assertAlmostEqual(out["diluent_volume_ml"],9.5)
        self.assertAlmostEqual(out["final_volume_ml"],10.0)
        self.assertAlmostEqual(out["final_concentration_mM"],0.5)
        self.assertGreater(out["material_flow_model"]["final_concentration_standard_uncertainty_mM"],0)
    def test_flow_changes_change_concentration_and_uncertainty(self):
        req=self.dilution_request()
        out1=apply_material_flow_model(req,run_lab_experiment(req)["results"])
        req["material_flows"][0]["amount"]=1.0
        out2=apply_material_flow_model(req,run_lab_experiment(req)["results"])
        self.assertNotEqual(out1["final_concentration_mM"],out2["final_concentration_mM"])
    def test_over_capacity_transfer_is_rejected(self):
        req=self.dilution_request()
        req["material_flows"][0]["amount"]=1.5
        valid=validate_protocol(req)
        self.assertFalse(valid["valid"])
        self.assertTrue(any(x["code"]=="flow_transfer_capacity" for x in valid["issues"]))
    def test_instrument_measurement_is_reproducible_and_uncertainty_changes_reading(self):
        req={
            "workflow_id":"materials_heating",
            "components":["polymer"],
            "equipment":["thermal_chamber","thermometer"],
            "protocol_steps":[
                {"id":"heat","action":"Heat material","equipment_id":"thermal_chamber","duration_s":1},
                {"id":"measure","action":"Measure temperature","equipment_id":"thermometer","duration_s":1}
            ],
            "edges":[{"from":"heat","to":"measure"}],
            "material_flows":[],
            "measurements":[{"step_id":"measure","kind":"temperature","equipment_id":"thermometer","label":"Midpoint temperature","unit":"°C","target_variable":"T10","sample_index":-1}],
            "parameters":{"length_m":1,"diffusivity_m2_s":0.00001,"left_temp_c":100,"right_temp_c":20,"initial_temp_c":20,"nodes":21,"dt_s":1,"total_time_s":10}
        }
        result=run_lab_experiment(req)["results"]
        a=execute_protocol(req,result)
        b=execute_protocol(req,result)
        m=a["simulated_measurements"][0]
        self.assertEqual(m["status"],"simulated_instrument_reading")
        self.assertEqual(m["observed_value"],b["simulated_measurements"][0]["observed_value"])
        self.assertNotEqual(m["observed_value"],m["true_value"])
        self.assertEqual(m["uncertainty_sd"],0.5)
    def test_thermal_chamber_uncertainty_changes_solver_and_is_reproducible(self):
        req={
            "workflow_id":"materials_heating","components":["polymer"],"equipment":["thermal_chamber"],
            "parameters":{"length_m":1,"diffusivity_m2_s":0.00001,"left_temp_c":100,"right_temp_c":20,"initial_temp_c":20,"nodes":21,"dt_s":1,"total_time_s":10}
        }
        base=run_lab_experiment({**req,"steps":[{"action":"Heat"}]})["results"]
        a=apply_equipment_operating_effects(req,dict(base))
        b=apply_equipment_operating_effects(req,dict(base))
        self.assertEqual(a["equipment_effect_model"]["left_boundary_offset_c"],b["equipment_effect_model"]["left_boundary_offset_c"])
        self.assertNotEqual(a["equipment_effect_model"]["left_boundary_offset_c"],0.0)
        self.assertNotEqual(a["rows"][-1]["T0"],base["rows"][-1]["T0"])
    def test_measurement_without_matching_solver_variable_is_not_fabricated(self):
        req={
            "components":["polymer"],"equipment":["thermal_chamber","thermometer"],
            "protocol_steps":[{"id":"s","action":"Measure","equipment_id":"thermometer","duration_s":0}],
            "edges":[],"material_flows":[],
            "measurements":[{"step_id":"s","kind":"temperature","equipment_id":"thermometer","label":"unknown","target_variable":"not_a_column","sample_index":-1}]
        }
        out=execute_protocol(req,{"rows":[{"T0":22.0}]})
        self.assertIsNone(out["simulated_measurements"][0]["observed_value"])
        self.assertEqual(out["simulated_measurements"][0]["status"],"plan_only_no_matching_solver_output")

if __name__ == "__main__":
    unittest.main()
