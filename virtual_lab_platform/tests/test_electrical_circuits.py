import unittest
from electrical_circuits import solve_dc_circuit, CircuitError

class ElectricalCircuitTests(unittest.TestCase):
    def test_single_resistor_ohms_law(self):
        d=solve_dc_circuit({'source_voltage':10,'resistors':[{'id':'R1','a':'S','b':'0','resistance_ohm':1000}]})
        self.assertAlmostEqual(d['source_current_a'],0.01,12)
        self.assertAlmostEqual(d['equivalent_resistance_ohm'],1000,8)
        self.assertAlmostEqual(d['branches'][0]['power_w'],0.1,10)
        self.assertTrue(d['checks']['numerically_consistent'])
    def test_parallel_network(self):
        d=solve_dc_circuit({'source_voltage':12,'resistors':[{'id':'R1','a':'S','b':'0','resistance_ohm':1000},{'id':'R2','a':'S','b':'0','resistance_ohm':1000}]})
        self.assertAlmostEqual(d['source_current_a'],0.024,10)
        self.assertAlmostEqual(d['equivalent_resistance_ohm'],500,8)
        self.assertAlmostEqual(d['total_resistor_power_w'],0.288,8)
    def test_series_network(self):
        d=solve_dc_circuit({'source_voltage':9,'resistors':[{'id':'R1','a':'S','b':'N1','resistance_ohm':1000},{'id':'R2','a':'N1','b':'0','resistance_ohm':2000}]})
        self.assertAlmostEqual(d['source_current_a'],0.003,10)
        self.assertAlmostEqual(d['equivalent_resistance_ohm'],3000,8)
        self.assertAlmostEqual(d['node_voltages_v']['N1'],6,8)
    def test_rejects_nonpositive_resistance(self):
        with self.assertRaises(CircuitError): solve_dc_circuit({'resistors':[{'id':'R1','a':'S','b':'0','resistance_ohm':0}]})
    def test_floating_node_is_detected(self):
        with self.assertRaises(CircuitError): solve_dc_circuit({'resistors':[{'id':'R1','a':'N1','b':'N2','resistance_ohm':100}]})

if __name__=='__main__': unittest.main()
