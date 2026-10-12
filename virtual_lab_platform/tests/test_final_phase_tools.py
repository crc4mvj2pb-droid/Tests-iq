import unittest
from models import execute_model
from research_tools import fit_model_parameters, run_software_validation_suite

class FinalPhaseToolsTests(unittest.TestCase):
    def test_fit_recovers_first_order_rate_from_synthetic_reference(self):
        generated = execute_model('first_order_reaction', {
            'initial_A': 1, 'rate_constant': 0.3, 'duration': 10, 'points': 21
        })
        reference = [{'x': row['time'], 'y': row['A']} for row in generated['rows'][::2]]
        result = fit_model_parameters(
            'first_order_reaction',
            {'initial_A': 1, 'rate_constant': 0.1, 'duration': 10, 'points': 21},
            reference, 'time', 'A', {'rate_constant': [0.01, 1.0]}
        )
        self.assertAlmostEqual(result['fitted_parameters']['rate_constant'], 0.3, places=5)
        self.assertLess(result['metrics']['rmse'], 1e-5)
        self.assertEqual(result['observations_used'], len(reference))

    def test_fit_rejects_out_of_bounds_initial_parameter(self):
        with self.assertRaisesRegex(ValueError, 'inside its bounds'):
            fit_model_parameters('first_order_reaction',
                {'initial_A': 1, 'rate_constant': 0.5, 'duration': 10, 'points': 11},
                [{'x': 0, 'y': 1}, {'x': 1, 'y': 0.8}, {'x': 2, 'y': 0.6}],
                'time', 'A', {'rate_constant': [0.01, 0.2]})

    def test_software_sanity_suite_covers_all_current_solver_models(self):
        result = run_software_validation_suite()
        self.assertEqual(result['total'], 10)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(result['passed'], 10)
        self.assertIn('not empirical', result['scope'])

if __name__ == '__main__':
    unittest.main()
