"""v5.7 — verification of the catalogue models against independent references.

Each test compares a model with a reference that does not reuse its code: a closed form evaluated
independently, an adaptive integration (numerics.dopri5) of the stated equations, a conserved
quantity, or a classical analytical result. The maturity level "verified" may only cite these tests.
"""
from __future__ import annotations

import cmath
import math

import pytest

from constants import GAS_CONSTANT
from electrical_advanced import simulate_first_order_step, solve_series_rlc_ac, sweep_series_rlc_frequency
from models import execute_model
from numerics import Tolerances, dopri5

TIGHT = Tolerances(rtol=1e-10, atol=1e-12)


def _integrate(f, y0, times):
    states, _ = dopri5(lambda t, y: f(y), 0.0, y0, times[-1], times, TIGHT)
    return states


def test_enzyme_kinetics_against_michaelis_menten_properties():
    d = execute_model("enzyme_kinetics", {"vmax": 2.0, "km": 0.5, "s_max": 1.0, "points": 3})
    # v(Km) = Vmax/2 exactly; v(0) = 0
    assert d["rows"][0]["y"] == 0 and d["rows"][1]["x"] == 0.5 and d["rows"][1]["y"] == pytest.approx(1.0, rel=1e-15)


def test_sir_epidemic_against_adaptive_integration():
    p = {"population": 10000.0, "beta": 0.3, "gamma": 0.1, "initial_infected": 10.0, "days": 160.0, "dt": 0.01}
    d = execute_model("sir_epidemic", p)
    times = [r["x"] for r in d["rows"]]
    ref = _integrate(lambda y: [-0.3 * y[0] * y[1] / 1e4, 0.3 * y[0] * y[1] / 1e4 - 0.1 * y[1], 0.1 * y[1]], [9990.0, 10.0, 0.0], times)
    peak_model = max(r["infectious"] for r in d["rows"]); peak_ref = max(s[1] for s in ref)
    # explicit Euler with dt = 0.01 d: agreement within 0.5 % on the peak
    assert peak_model == pytest.approx(peak_ref, rel=5e-3)


def _heat_reference(x, t, length, alpha, left, right, initial, terms=400):
    """Dirichlet ends: T = linear steady state + Σ (2/L)·c_n·sin(nπx/L)·e^(−α(nπ/L)²t), c_n from the initial condition."""
    total = left + (right - left) * x / length
    for n in range(1, terms + 1):
        k = n * math.pi / length
        total += 2 / length * _fourier_coeff(n, length, left, right, initial) * math.sin(k * x) * math.exp(-alpha * k * k * t)
    return total


def _fourier_coeff(n, length, left, right, initial):
    # ∫0^L (initial − steady(x)) sin(nπx/L) dx, computed in closed form.
    c = initial - left
    slope = (right - left) / length
    k = n * math.pi / length
    integral_const = c * (1 - math.cos(n * math.pi)) / k
    integral_linear = slope * (-length * math.cos(n * math.pi) / k)  # ∫0^L x sin(kx) dx = −L cos(nπ)/k
    return integral_const - integral_linear


def test_heat_diffusion_against_fourier_series():
    p = {"length_m": 1.0, "diffusivity_m2_s": 1e-4, "left_temp_c": 100.0, "right_temp_c": 20.0, "initial_temp_c": 20.0, "nodes": 41, "dt_s": 1.0, "total_time_s": 1000.0}
    d = execute_model("heat_diffusion_1d", p)
    final = d["rows"][-1]
    for i in (5, 10, 20, 30):
        x = i / 40
        assert final[f"T{i}"] == pytest.approx(_heat_reference(x, 1000.0, 1.0, 1e-4, 100.0, 20.0, 20.0), abs=0.02)  # FTCS, dx = 0.025 m: observed max 0.0095 °C


def test_logistic_growth_against_integration():
    d = execute_model("logistic_growth", {"initial_population": 10.0, "carrying_capacity": 1000.0, "growth_rate": 0.2, "duration": 30.0, "points": 31})
    ref = _integrate(lambda y: [0.2 * y[0] * (1 - y[0] / 1000.0)], [10.0], [r["time"] for r in d["rows"]])
    assert all(r["population"] == pytest.approx(s[0], rel=1e-8) for r, s in zip(d["rows"], ref))


@pytest.mark.parametrize("model_id,params,key,rate,y0", [
    ("first_order_reaction", {"initial_A": 2.0, "rate_constant": 0.3, "duration": 10.0, "points": 11}, "A", 0.3, 2.0),
    ("environmental_decay", {"initial_load": 50.0, "removal_rate": 0.05, "duration": 100.0, "points": 11}, "remaining_load", 0.05, 50.0),
    ("one_compartment_pk", {"input_amount": 100.0, "distribution_volume": 10.0, "clearance": 2.0, "duration": 24.0, "points": 13}, "concentration", 0.2, 10.0),
])
def test_first_order_closed_forms_against_integration(model_id, params, key, rate, y0):
    d = execute_model(model_id, params)
    time_key = "time"
    ref = _integrate(lambda y: [-rate * y[0]], [y0], [r[time_key] for r in d["rows"]])
    assert all(r[key] == pytest.approx(s[0], rel=1e-8) for r, s in zip(d["rows"], ref))


def test_lotka_volterra_conserves_its_first_integral_and_matches_integration():
    p = {"initial_prey": 40.0, "initial_predators": 9.0, "prey_growth": 1.0, "predation_rate": 0.1, "predator_growth": 0.075, "predator_decay": 1.5, "duration": 20.0, "dt": 0.01}
    d = execute_model("lotka_volterra", p)
    V = lambda x, y: 0.075 * x - 1.5 * math.log(x) + 0.1 * y - 1.0 * math.log(y)
    v0 = V(40.0, 9.0)
    assert all(abs(V(r["prey"], r["predators"]) - v0) < 1e-7 * abs(v0) for r in d["rows"])
    ref = _integrate(lambda y: [y[0] - 0.1 * y[0] * y[1], 0.075 * y[0] * y[1] - 1.5 * y[1]], [40.0, 9.0], [r["time"] for r in d["rows"]])
    assert all(r["prey"] == pytest.approx(s[0], rel=1e-6) for r, s in zip(d["rows"], ref))


def test_leaky_integrate_and_fire_against_analytical_interspike_interval():
    p = {"v_rest_mv": -65.0, "v_reset_mv": -70.0, "v_threshold_mv": -50.0, "initial_voltage_mv": -70.0, "tau_ms": 10.0, "resistance_mohm": 10.0,
         "current_na": 2.0, "duration_ms": 100.0, "dt_ms": 0.001}
    d = execute_model("leaky_integrate_fire", p)
    # From reset, V reaches threshold after T = τ·ln((RI − (Vreset − Vrest))/(RI − (θ − Vrest))) (no refractory period).
    T = 10.0 * math.log((20.0 - (-5.0)) / (20.0 - 15.0))
    spikes = d["summary"]["spike_times_ms"]
    assert spikes[0] == pytest.approx(T, abs=2e-3) and spikes[1] - spikes[0] == pytest.approx(T, abs=2e-3)
    assert d["summary"]["spike_count"] == int(100.0 // T)


def test_arrhenius_rate_constant_against_independent_evaluation():
    d = execute_model("arrhenius_reaction", {"pre_exponential_s_inv": 1e7, "activation_energy_j_mol": 50000.0, "temperature_k": 310.0})
    assert d["summary"]["rate_constant_s_inv"] == pytest.approx(1e7 * math.exp(-50000.0 / (GAS_CONSTANT * 310.0)), rel=1e-14)


@pytest.mark.parametrize("kind,params", [("RC", {"resistance_ohm": 2200.0, "capacitance_f": 4.7e-6, "initial_voltage_v": 1.0, "source_voltage_v": 5.0}),
                                         ("RL", {"resistance_ohm": 50.0, "inductance_h": 0.2, "initial_current_a": 0.0, "source_voltage_v": 12.0})])
def test_rc_rl_step_against_integration(kind, params):
    d = simulate_first_order_step({"kind": kind, "duration_s": 0.05, "points": 51, **params})
    times = [r["time_s"] for r in d["points"]]
    if kind == "RC":
        ref = _integrate(lambda y: [(5.0 - y[0]) / (2200.0 * 4.7e-6)], [1.0], times); key = "capacitor_voltage_v"
    else:
        ref = _integrate(lambda y: [(12.0 - 50.0 * y[0]) / 0.2], [0.0], times); key = "inductor_current_a"
    assert all(r[key] == pytest.approx(s[0], rel=1e-8, abs=1e-12) for r, s in zip(d["points"], ref))


@pytest.mark.parametrize("f", [50.0, 1591.549, 1e5])
def test_series_rlc_ac_against_complex_arithmetic(f):
    R, L, C, V = 100.0, 0.01, 1e-6, 5.0
    d = solve_series_rlc_ac({"source_voltage_rms_v": V, "resistance_ohm": R, "inductance_h": L, "capacitance_f": C, "frequency_hz": f})
    z = complex(R, 2 * math.pi * f * L - 1 / (2 * math.pi * f * C))
    i = V / z
    assert d["impedance_magnitude_ohm"] == pytest.approx(abs(z), rel=1e-12) and d["current_rms_a"] == pytest.approx(abs(i), rel=1e-12)
    assert d["impedance_phase_deg"] == pytest.approx(math.degrees(cmath.phase(z)), abs=1e-9)
    assert d["real_power_w"] == pytest.approx(abs(i) ** 2 * R, rel=1e-12)


def test_rlc_sweep_points_equal_individual_solves():
    base = {"source_voltage_rms_v": 5.0, "resistance_ohm": 100.0, "inductance_h": 0.01, "capacitance_f": 1e-6}
    d = sweep_series_rlc_frequency({**base, "start_frequency_hz": 100.0, "stop_frequency_hz": 1e4, "points": 41})
    for row in d["points"]:
        single = solve_series_rlc_ac({**base, "frequency_hz": row["frequency_hz"]})
        assert row["current_rms_a"] == single["current_rms_a"]
    assert d["analytical_resonant_frequency_hz"] == pytest.approx(1 / (2 * math.pi * math.sqrt(0.01 * 1e-6)), rel=1e-12)
