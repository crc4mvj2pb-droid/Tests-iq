import math
import pytest
from electrical_advanced import simulate_first_order_step, solve_series_rlc_ac, sweep_series_rlc_frequency, ElectricalModelError

def test_rc_time_constant_and_final_value():
    d=simulate_first_order_step({'kind':'RC','source_voltage_v':5,'resistance_ohm':1000,'capacitance_f':1e-6,'duration_s':0.01,'points':101})
    assert d['time_constant_s']==pytest.approx(.001)
    assert d['points'][0]['capacitor_voltage_v']==pytest.approx(0)
    assert d['points'][-1]['capacitor_voltage_v']==pytest.approx(5,abs=1e-3)
    assert d['checks']['finite_outputs']

def test_rl_step_final_current():
    d=simulate_first_order_step({'kind':'RL','source_voltage_v':10,'resistance_ohm':5,'inductance_h':.5,'duration_s':2,'points':51})
    assert d['time_constant_s']==pytest.approx(.1)
    assert d['final_value']==pytest.approx(2)
    assert d['points'][-1]['inductor_current_a']==pytest.approx(2,abs=1e-8)

def test_series_rlc_resonance_and_power():
    L=.01; C=1e-6; f=1/(2*math.pi*math.sqrt(L*C))
    d=solve_series_rlc_ac({'source_voltage_rms_v':5,'resistance_ohm':100,'inductance_h':L,'capacitance_f':C,'frequency_hz':f})
    assert d['net_reactance_ohm']==pytest.approx(0,abs=1e-8)
    assert d['current_rms_a']==pytest.approx(.05)
    assert d['real_power_w']==pytest.approx(.25)

def test_log_sweep_and_bounds():
    d=sweep_series_rlc_frequency({'resistance_ohm':100,'inductance_h':.01,'capacitance_f':1e-6,'start_frequency_hz':10,'stop_frequency_hz':1e6,'points':51})
    assert len(d['points'])==51
    assert d['points'][0]['frequency_hz']==pytest.approx(10)
    assert d['points'][-1]['frequency_hz']==pytest.approx(1e6)

def test_reject_bad_physical_parameters():
    with pytest.raises(ElectricalModelError): solve_series_rlc_ac({'resistance_ohm':0,'inductance_h':1,'capacitance_f':1e-6,'frequency_hz':60})
    with pytest.raises(ElectricalModelError): simulate_first_order_step({'kind':'BAD'})
