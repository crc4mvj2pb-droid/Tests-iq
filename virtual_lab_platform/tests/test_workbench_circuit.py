import unittest

from workbench_circuit import solve_workbench_circuit, WorkbenchCircuitError


def component(instance_id, item_id, qty, name=None):
    return {"instanceId": instance_id, "id": item_id, "qty": qty, "displayName": name or instance_id, "cat": "electrical"}


def wire(a, pin_a, b, pin_b):
    return {"a": a, "pinA": pin_a, "b": b, "pinB": pin_b, "kind": "ideal-wire"}


class WorkbenchCircuitTests(unittest.TestCase):
    def setUp(self):
        self.source = component("S", "dc-source", 9, "9 V source")
        self.ground = component("G", "ground", 0, "Ground")
        self.r1 = component("R1", "resistor", 1000, "R1")

    def test_single_resistor_is_solved_from_pin_connections(self):
        result = solve_workbench_circuit({
            "components": [self.source, self.r1, self.ground],
            "connections": [wire("S", "P", "R1", "A"), wire("R1", "B", "G", "GND"), wire("S", "N", "G", "GND")],
        })
        self.assertEqual(result["status"], "computed")
        self.assertAlmostEqual(result["equivalent_resistance_ohm"], 1000)
        self.assertAlmostEqual(result["source_current_a"], 0.009)
        self.assertAlmostEqual(result["branches"][0]["power_w"], 0.081)
        self.assertTrue(result["checks"]["numerically_consistent"])
        self.assertEqual(len(result["topology"]["terminal_nodes"]), 5)

    def test_series_resistors_use_shared_intermediate_net(self):
        r2 = component("R2", "resistor2", 2000, "R2")
        result = solve_workbench_circuit({
            "components": [self.source, self.r1, r2, self.ground],
            "connections": [
                wire("S", "P", "R1", "A"), wire("R1", "B", "R2", "A"),
                wire("R2", "B", "G", "GND"), wire("S", "N", "G", "GND"),
            ],
        })
        self.assertAlmostEqual(result["equivalent_resistance_ohm"], 3000)
        self.assertAlmostEqual(result["source_current_a"], 0.003)
        self.assertEqual(len(result["branches"]), 2)

    def test_parallel_resistors_are_solved_from_shared_nodes(self):
        r2 = component("R2", "resistor2", 2000, "R2")
        result = solve_workbench_circuit({
            "components": [self.source, self.r1, r2, self.ground],
            "connections": [
                wire("S", "P", "R1", "A"), wire("R1", "B", "G", "GND"),
                wire("S", "P", "R2", "A"), wire("R2", "B", "G", "GND"),
                wire("S", "N", "G", "GND"),
            ],
        })
        self.assertAlmostEqual(result["equivalent_resistance_ohm"], 1 / (1 / 1000 + 1 / 2000))
        self.assertAlmostEqual(result["source_current_a"], 0.0135)

    def test_ideal_wire_component_joins_its_own_two_pins(self):
        segment = component("W1", "wire", 0, "Wire segment")
        result = solve_workbench_circuit({
            "components": [self.source, self.r1, self.ground, segment],
            "connections": [wire("S", "P", "W1", "A"), wire("W1", "B", "R1", "A"), wire("R1", "B", "G", "GND"), wire("S", "N", "G", "GND")],
        })
        self.assertAlmostEqual(result["source_current_a"], 0.009)
        self.assertEqual(result["topology"]["wire_count"], 4)

    def test_duplicate_display_names_do_not_break_internal_branch_ids(self):
        r2 = component("R2", "resistor2", 2000, "Resistance")
        r1 = component("R1", "resistor", 1000, "Resistance")
        result = solve_workbench_circuit({
            "components": [self.source, r1, r2, self.ground],
            "connections": [wire("S", "P", "R1", "A"), wire("R1", "B", "R2", "A"), wire("R2", "B", "G", "GND"), wire("S", "N", "G", "GND")],
        })
        self.assertEqual(len({b["id"] for b in result["branches"]}), 2)
        self.assertEqual([b["display_name"] for b in result["branches"]], ["Resistance", "Resistance"])

    def test_missing_terminal_connection_is_rejected(self):
        with self.assertRaisesRegex(WorkbenchCircuitError, "not wired"):
            solve_workbench_circuit({"components": [self.source, self.r1, self.ground], "connections": []})

    def test_source_negative_must_be_connected_to_ground(self):
        with self.assertRaisesRegex(WorkbenchCircuitError, "negative"):
            solve_workbench_circuit({
                "components": [self.source, self.r1, component("R2", "resistor2", 2000, "R2"), self.ground],
                "connections": [wire("S", "P", "R1", "A"), wire("R1", "B", "R2", "A"), wire("R2", "B", "G", "GND"), wire("S", "N", "R2", "A")],
            })

    def test_connected_capacitor_is_rejected_by_dc_engine(self):
        capacitor = component("C1", "capacitor", 1e-6, "C1")
        with self.assertRaisesRegex(WorkbenchCircuitError, "not yet supported"):
            solve_workbench_circuit({
                "components": [self.source, self.r1, capacitor, self.ground],
                "connections": [wire("S", "P", "R1", "A"), wire("R1", "B", "C1", "A"), wire("C1", "B", "G", "GND"), wire("S", "N", "G", "GND")],
            })

    def test_short_circuited_source_is_rejected(self):
        with self.assertRaisesRegex(WorkbenchCircuitError, "short-circuited"):
            solve_workbench_circuit({
                "components": [self.source, self.r1, self.ground],
                "connections": [wire("S", "P", "G", "GND"), wire("S", "N", "G", "GND"), wire("R1", "A", "G", "GND"), wire("R1", "B", "G", "GND")],
            })


if __name__ == "__main__":
    unittest.main()
