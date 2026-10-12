import unittest
from lab_designer import CATALOG, validate_experiment, run_lab_experiment

class LabDesignerTests(unittest.TestCase):
    def setup_request(self, workflow='solution_dilution'):
        wf=next(x for x in CATALOG['workflows'] if x['id']==workflow)
        params={'stock_concentration_mM':10,'stock_volume_ml':0.5,'diluent_volume_ml':9.5} if workflow=='solution_dilution' else ({'vmax':1,'km':0.5,'substrate_max':3,'points':11} if workflow=='enzyme_assay' else {})
        return {'name':'test','workflow_id':workflow,'discipline':wf['discipline'],'components':wf['required_components'][:],'equipment':wf['required_equipment'][:]+[group[0] for group in wf.get('required_equipment_options',[])],'steps':[{'action':'Prepare setup'},{'action':'Record observation'}],'parameters':params}
    def test_catalog_has_components_equipment_and_workflows(self):
        self.assertGreaterEqual(len(CATALOG['components']),8)
        self.assertGreaterEqual(len(CATALOG['equipment']),8)
        self.assertGreaterEqual(len(CATALOG['workflows']),5)
    def test_solution_dilution_calculation(self):
        out=run_lab_experiment(self.setup_request())
        self.assertAlmostEqual(out['results']['final_volume_ml'],10.0)
        self.assertAlmostEqual(out['results']['final_concentration_mM'],0.5)
        self.assertEqual(out['validation_level'],'L1')
    def test_missing_machine_blocks_run(self):
        req=self.setup_request();req['equipment'].remove('pipette')
        check=validate_experiment(req)
        self.assertFalse(check['valid'])
        with self.assertRaises(ValueError):run_lab_experiment(req)
    def test_pipette_capacity_is_checked(self):
        req=self.setup_request();req['parameters']['stock_volume_ml']=2
        check=validate_experiment(req)
        self.assertTrue(any(x['code']=='pipette_capacity' for x in check['issues']))
    def test_larger_pipette_capacity_allows_larger_transfer(self):
        req=self.setup_request();req['parameters']['stock_volume_ml']=2;req['parameters']['diluent_volume_ml']=8;req['equipment'].remove('pipette');req['equipment'].append('pipette_10ml')
        self.assertTrue(validate_experiment(req)['valid'])
    def test_enzyme_assay_returns_curve(self):
        out=run_lab_experiment(self.setup_request('enzyme_assay'))
        self.assertEqual(len(out['results']['rows']),11)
        self.assertTrue(out['results']['checks']['rate_not_above_vmax'])
    def test_workflow_without_solver_does_not_invent_result(self):
        out=run_lab_experiment(self.setup_request('microscopy'))
        self.assertEqual(out['validation_level'],'L0')
        self.assertFalse(out['results']['computed_scientific_result'])
    def test_invalid_protocol_step(self):
        req=self.setup_request();req['steps']=[{}]
        self.assertFalse(validate_experiment(req)['valid'])


    def test_material_heating_workflow_runs_connected_solver(self):
        req=self.setup_request('materials_heating')
        req['parameters']={'length_m':1.0,'diffusivity_m2_s':1e-5,'left_temp_c':100.0,'right_temp_c':20.0,'initial_temp_c':20.0,'nodes':21,'dt_s':1.0,'total_time_s':100.0}
        out=run_lab_experiment(req)
        self.assertEqual(out['results']['model_id'],'heat_diffusion_1d')
        self.assertTrue(out['results']['checks']['stability_condition_satisfied'])
        self.assertTrue(out['results']['computed_scientific_result'])
        self.assertGreater(len(out['results']['rows']),1)

    def test_material_heating_blocks_unstable_solver_step(self):
        req=self.setup_request('materials_heating')
        req['parameters']={'length_m':1.0,'diffusivity_m2_s':1e-5,'left_temp_c':100.0,'right_temp_c':20.0,'initial_temp_c':20.0,'nodes':21,'dt_s':200.0,'total_time_s':1000.0}
        with self.assertRaisesRegex(ValueError,'unstable'):
            run_lab_experiment(req)

    def test_sir_workflow_runs_connected_solver(self):
        req=self.setup_request('epidemic_sir')
        req['parameters']={'population':10000,'initial_infected':10,'beta':0.3,'gamma':0.1,'days':20,'dt':0.1}
        out=run_lab_experiment(req)
        self.assertEqual(out['results']['model_id'],'sir_epidemic')
        self.assertTrue(out['results']['checks']['population_approximately_conserved'])
        self.assertTrue(out['results']['computed_scientific_result'])

    def test_sir_workflow_rejects_invalid_duration_step_pair(self):
        req=self.setup_request('epidemic_sir')
        req['parameters']={'population':10000,'initial_infected':10,'beta':0.3,'gamma':0.1,'days':20,'dt':0.3}
        self.assertFalse(validate_experiment(req)['valid'])

if __name__=='__main__':unittest.main()
