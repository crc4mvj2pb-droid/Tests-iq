import unittest
from models import execute_model, MODEL_CATALOG
from research_tools import parameter_sweep, monte_carlo_uncertainty, compare_model_output

class ExtendedSolverTests(unittest.TestCase):
    def test_logistic_growth_is_bounded_and_monotonic(self):
        r=execute_model('logistic_growth', {'initial_population':10,'carrying_capacity':100,'growth_rate':0.2,'duration':20,'points':21})
        self.assertTrue(all(r['checks'].values()))
        self.assertEqual(r['rows'][0]['population'],10)
        self.assertLessEqual(r['summary']['final_population'],100)

    def test_first_order_reaction_preserves_mass(self):
        r=execute_model('first_order_reaction', {'initial_A':2,'rate_constant':0.5,'duration':5,'points':11})
        self.assertTrue(all(r['checks'].values()))
        self.assertAlmostEqual(r['rows'][-1]['A']+r['rows'][-1]['B'],2)
        self.assertAlmostEqual(r['summary']['half_life'], 1.38629436112, places=8)

    def test_environmental_decay_balance(self):
        r=execute_model('environmental_decay', {'initial_load':100,'removal_rate':0.1,'duration':10,'points':11})
        self.assertTrue(all(r['checks'].values()))
        self.assertAlmostEqual(r['rows'][-1]['remaining_load']+r['rows'][-1]['removed_or_decayed'],100)

    def test_pk_model_is_explicitly_teaching_only(self):
        r=execute_model('one_compartment_pk', {'input_amount':100,'distribution_volume':10,'clearance':1,'duration':24,'points':25})
        self.assertTrue(all(r['checks'].values()))
        self.assertAlmostEqual(r['rows'][0]['concentration'],10)
        self.assertTrue(any('Not for dose selection' in x for x in r['limitations']))

    def test_lotka_volterra_rk4_stays_finite_for_default_case(self):
        r=execute_model('lotka_volterra', {'initial_prey':40,'initial_predators':9,'prey_growth':1,'predation_rate':0.1,'predator_growth':0.075,'predator_decay':1.5,'duration':20,'dt':0.01})
        self.assertTrue(all(r['checks'].values()))
        self.assertLessEqual(len(r['rows']), 502)

    def test_leaky_integrate_fire_produces_bounded_spike_events(self):
        r=execute_model('leaky_integrate_fire', {'v_rest_mv':-65,'v_reset_mv':-70,'v_threshold_mv':-50,'initial_voltage_mv':-65,'tau_ms':10,'resistance_mohm':10,'current_na':2,'duration_ms':100,'dt_ms':0.1})
        self.assertTrue(all(r['checks'].values()))
        self.assertGreater(r['summary']['spike_count'],0)
        self.assertTrue(all(0<t<=100 for t in r['summary']['spike_times_ms']))

    def test_arrhenius_reaction_responds_to_temperature(self):
        base={'initial_A':1,'pre_exponential_s_inv':1,'activation_energy_j_mol':40000,'duration_s':10,'points':11}
        cold=execute_model('arrhenius_reaction',{**base,'temperature_k':280})
        warm=execute_model('arrhenius_reaction',{**base,'temperature_k':320})
        self.assertTrue(all(cold['checks'].values()) and all(warm['checks'].values()))
        self.assertGreater(warm['summary']['rate_constant_s_inv'],cold['summary']['rate_constant_s_inv'])
        self.assertLess(warm['summary']['final_A'],cold['summary']['final_A'])

    def test_catalog_and_solver_registry_match_for_new_models(self):
        ids={x['id'] for x in MODEL_CATALOG}
        for model_id in ('logistic_growth','first_order_reaction','environmental_decay','one_compartment_pk','lotka_volterra','leaky_integrate_fire','arrhenius_reaction'):
            self.assertIn(model_id,ids)
            self.assertEqual(execute_model(model_id, {}).get('status'),'computed_basic_checks_passed')

class GeneralResearchToolTests(unittest.TestCase):
    def test_generic_sweep(self):
        r=parameter_sweep('first_order_reaction', {'initial_A':1,'rate_constant':0.2,'duration':10,'points':11}, 'rate_constant',[0.1,0.2,0.3], 'final_A')
        self.assertEqual(len(r['rows']),3)
        self.assertTrue(r['all_basic_checks_passed'])
        self.assertGreater(r['rows'][0]['summary_value'],r['rows'][-1]['summary_value'])

    def test_generic_uncertainty_is_seeded(self):
        args=('logistic_growth', {'initial_population':10,'carrying_capacity':100,'growth_rate':0.2,'duration':10,'points':11}, {'growth_rate':0.01}, 'final_population')
        a=monte_carlo_uncertainty(*args,samples=40,seed=12)
        b=monte_carlo_uncertainty(*args,samples=40,seed=12)
        self.assertEqual(a['summary'],b['summary'])
        self.assertGreaterEqual(a['samples_accepted'],20)

    def test_generic_reference_comparison_uses_selected_columns(self):
        ref=[{'x':0,'y':10},{'x':10,'y':50}]
        r=compare_model_output('logistic_growth', {'initial_population':10,'carrying_capacity':100,'growth_rate':0.2,'duration':10,'points':11},ref,'time','population')
        self.assertEqual(r['source_output_columns'],{'x':'time','y':'population'})
        self.assertEqual(r['number_of_comparison_points'],11)

    def test_sweep_rejects_duplicate_values(self):
        with self.assertRaisesRegex(ValueError,'unique'):
            parameter_sweep('first_order_reaction', {'initial_A':1,'rate_constant':0.2,'duration':10,'points':11}, 'rate_constant',[0.1,0.1])

if __name__=='__main__': unittest.main()
