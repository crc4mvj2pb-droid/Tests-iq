"""Validated analytical electrical models: first-order RC/RL steps and series RLC AC.

These are idealized domain models, not a SPICE engine. SI units are used throughout.
"""
from __future__ import annotations
import math

ENGINE_ID = "analytical_linear_circuits"
ENGINE_VERSION = "1.0"

class ElectricalModelError(ValueError):
    pass

def _finite(name, value, *, minimum=None, maximum=None):
    try: x=float(value)
    except (TypeError, ValueError): raise ElectricalModelError(f"{name} must be numeric.")
    if not math.isfinite(x): raise ElectricalModelError(f"{name} must be finite.")
    if minimum is not None and x < minimum: raise ElectricalModelError(f"{name} must be ≥ {minimum}.")
    if maximum is not None and x > maximum: raise ElectricalModelError(f"{name} must be ≤ {maximum}.")
    return x

def simulate_first_order_step(req: dict) -> dict:
    """Analytical step response of an ideal series RC or RL circuit.

    RC: capacitor voltage starts at initial_value_v and approaches source_voltage_v.
    RL: inductor current starts at initial_value_a and approaches source_voltage_v/R.
    """
    kind=str(req.get('kind','RC')).upper()
    if kind not in ('RC','RL'): raise ElectricalModelError("kind must be RC or RL.")
    source=_finite('source_voltage_v',req.get('source_voltage_v',5),minimum=-1e6,maximum=1e6)
    resistance=_finite('resistance_ohm',req.get('resistance_ohm',1000),minimum=1e-9,maximum=1e12)
    component=_finite('capacitance_f' if kind=='RC' else 'inductance_h',req.get('capacitance_f' if kind=='RC' else 'inductance_h',1e-6),minimum=1e-15,maximum=1e6)
    duration=_finite('duration_s',req.get('duration_s',0.01),minimum=1e-12,maximum=1e9)
    count=int(_finite('points',req.get('points',101),minimum=2,maximum=2001))
    initial_key='initial_voltage_v' if kind=='RC' else 'initial_current_a'
    initial=_finite(initial_key,req.get(initial_key,0),minimum=-1e9,maximum=1e9)
    tau=resistance*component if kind=='RC' else component/resistance
    final=source if kind=='RC' else source/resistance
    rows=[]
    for i in range(count):
        t=duration*i/(count-1)
        value=final+(initial-final)*math.exp(-t/tau)
        if kind=='RC':
            current=(source-value)/resistance
            rows.append({'time_s':t,'capacitor_voltage_v':value,'current_a':current,'resistor_voltage_v':source-value,'stored_energy_j':0.5*component*value*value})
        else:
            rows.append({'time_s':t,'inductor_current_a':value,'resistor_voltage_v':value*resistance,'inductor_voltage_v':source-value*resistance,'stored_energy_j':0.5*component*value*value})
    return {'model':f'ideal_{kind.lower()}_step_response','status':'computed','kind':kind,'time_constant_s':tau,'time_constant_ms':tau*1000,'final_value':final,'points':rows,'checks':{'time_constant_positive':tau>0,'finite_outputs':all(math.isfinite(v) for row in rows for v in row.values()),'approaches_final_value':abs(rows[-1][('capacitor_voltage_v' if kind=='RC' else 'inductor_current_a')]-final) <= abs(initial-final)+1e-12},'assumptions':['Ideal step source, linear component, zero parasitics, constant R/C/L.','Initial conditions are explicitly supplied; RC reports capacitor voltage, RL reports inductor current.'],'limitations':['Not a general transient circuit solver; topology is a single ideal first-order series circuit.','No component tolerances, ESR, leakage, saturation, temperature effects, switching nonidealities or measurement noise.','Numerical predictions need independent validation before hardware design.']}

def solve_series_rlc_ac(req: dict) -> dict:
    """Steady-state sinusoidal response of a series RLC circuit; RMS phasors."""
    voltage=_finite('source_voltage_rms_v',req.get('source_voltage_rms_v',5),minimum=0,maximum=1e6)
    resistance=_finite('resistance_ohm',req.get('resistance_ohm',100),minimum=1e-9,maximum=1e12)
    inductance=_finite('inductance_h',req.get('inductance_h',0.01),minimum=0,maximum=1e6)
    capacitance=_finite('capacitance_f',req.get('capacitance_f',1e-6),minimum=1e-15,maximum=1e6)
    frequency=_finite('frequency_hz',req.get('frequency_hz',1000),minimum=1e-9,maximum=1e12)
    omega=2*math.pi*frequency
    xl=omega*inductance; xc=1/(omega*capacitance); x=xl-xc
    z=math.hypot(resistance,x); current=voltage/z
    phase=math.atan2(x,resistance)
    vr=current*resistance; vl=current*xl; vc=current*xc
    real= current*current*resistance
    ql=current*current*xl; qc=-current*current*xc
    resonance=1/(2*math.pi*math.sqrt(inductance*capacitance)) if inductance>0 else None
    return {'model':'ideal_series_rlc_sinusoidal_steady_state','status':'computed','phasor_convention':'RMS magnitudes; source voltage phase = 0°; current phase = -arg(Z).','frequency_hz':frequency,'angular_frequency_rad_s':omega,'source_voltage_rms_v':voltage,'resistance_ohm':resistance,'inductance_h':inductance,'capacitance_f':capacitance,'inductive_reactance_ohm':xl,'capacitive_reactance_ohm':xc,'net_reactance_ohm':x,'impedance_magnitude_ohm':z,'impedance_phase_deg':math.degrees(phase),'current_rms_a':current,'current_phase_deg':-math.degrees(phase),'resistor_voltage_rms_v':vr,'inductor_voltage_rms_v':vl,'capacitor_voltage_rms_v':vc,'real_power_w':real,'reactive_power_var':ql+qc,'power_factor':math.cos(phase),'resonant_frequency_hz':resonance,'checks':{'finite_outputs':all(math.isfinite(v) for v in [xl,xc,x,z,current,vr,vl,vc,real]),'positive_impedance_magnitude':z>0},'assumptions':['Ideal sinusoidal source and ideal linear R, L, C in series; steady state only.','Voltage and current magnitudes are RMS.','Power calculations assume ideal sinusoidal steady state.'],'limitations':['No transient startup, parasitics, component tolerances, nonlinear devices or frequency-dependent losses.','Component voltage magnitudes may exceed source voltage near resonance; do not interpret as a hardware safety guarantee.','Not a replacement for SPICE or validated electrical engineering software.']}

def sweep_series_rlc_frequency(req: dict) -> dict:
    start=_finite('start_frequency_hz',req.get('start_frequency_hz',10),minimum=1e-9,maximum=1e12)
    stop=_finite('stop_frequency_hz',req.get('stop_frequency_hz',1e6),minimum=start,maximum=1e12)
    points=int(_finite('points',req.get('points',101),minimum=2,maximum=2001))
    base={k:req.get(k) for k in ('source_voltage_rms_v','resistance_ohm','inductance_h','capacitance_f') if k in req}
    rows=[]
    for i in range(points):
        # Log spacing is appropriate for frequency response across decades.
        f=start*(stop/start)**(i/(points-1))
        row=solve_series_rlc_ac({**base,'frequency_hz':f})
        rows.append({k:row[k] for k in ('frequency_hz','current_rms_a','impedance_magnitude_ohm','impedance_phase_deg','real_power_w','power_factor')})
    peak=max(rows,key=lambda r:r['current_rms_a'])
    return {'model':'ideal_series_rlc_log_frequency_sweep','status':'computed','frequency_spacing':'logarithmic','points':rows,'peak_current_sampled':peak,'analytical_resonant_frequency_hz':solve_series_rlc_ac({**base,'frequency_hz':math.sqrt(start*stop)})['resonant_frequency_hz'],'assumptions':['Each point is an independent ideal steady-state sinusoidal solve.'],'limitations':['Peak current is the largest sampled point, not necessarily the exact resonance. Increase point count or refine around the analytical resonant frequency.','Not a physical measurement or component safety assessment.']}
