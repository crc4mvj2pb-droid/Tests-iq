"""v7.4 — classical neuron models (Hodgkin–Huxley, FitzHugh–Nagumo) checked against independent computations."""
from __future__ import annotations

import math

import pytest

import model_registry
import neuro


def run(model, inputs):
    return model_registry.run_model(model, inputs)["result"]


# --- independent re-implementation of the HH equations (written separately from neuro.py) ---------
def _alpha_beta(v):
    def vtrap(x, y):
        return y if abs(x) < 1e-9 else x / (1 - math.exp(-x / y))
    an, bn = 0.01 * vtrap(v + 55, 10), 0.125 * math.exp(-(v + 65) / 80)
    am, bm = 0.1 * vtrap(v + 40, 10), 4 * math.exp(-(v + 65) / 18)
    ah, bh = 0.07 * math.exp(-(v + 65) / 20), 1 / (1 + math.exp(-(v + 35) / 10))
    return an, bn, am, bm, ah, bh


def _ionic(v):
    an, bn, am, bm, ah, bh = _alpha_beta(v)
    m, h, n = am / (am + bm), ah / (ah + bh), an / (an + bn)
    return 120 * m ** 3 * h * (v - 50) + 36 * n ** 4 * (v + 77) + 0.3 * (v + 54.387)


def test_resting_potential_against_an_independent_steady_state_root():
    lo, hi = -80.0, -50.0
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _ionic(lo) * _ionic(mid) > 0 else (lo, mid)
    v_rest = (lo + hi) / 2
    r = run("hodgkin_huxley", {"current_ua_cm2": 0.0, "duration_ms": 200.0, "initial_voltage_mv": -60.0})
    assert r["spike_count"] == 0 and r["final_voltage_mv"] == pytest.approx(v_rest, abs=1e-3)
    assert v_rest == pytest.approx(-65.0, abs=0.05)


def test_spike_times_against_independent_fine_step_integration():
    def rhs(s, current):
        v, m, h, n = s
        an, bn, am, bm, ah, bh = _alpha_beta(v)
        i_ion = 120 * m ** 3 * h * (v - 50) + 36 * n ** 4 * (v + 77) + 0.3 * (v + 54.387)
        return (current - i_ion, am * (1 - m) - bm * m, ah * (1 - h) - bh * h, an * (1 - n) - bn * n)
    an, bn, am, bm, ah, bh = _alpha_beta(-65.0)
    s, dt, t, spikes = (-65.0, am / (am + bm), ah / (ah + bh), an / (an + bn)), 0.0025, 0.0, []
    while t < 50.0:
        k1 = rhs(s, 10.0); k2 = rhs(tuple(a + dt / 2 * b for a, b in zip(s, k1)), 10.0)
        k3 = rhs(tuple(a + dt / 2 * b for a, b in zip(s, k2)), 10.0); k4 = rhs(tuple(a + dt * b for a, b in zip(s, k3)), 10.0)
        new = tuple(a + dt / 6 * (b + 2 * c + 2 * d + e) for a, b, c, d, e in zip(s, k1, k2, k3, k4))
        if s[0] < 0 <= new[0]:
            spikes.append(t + dt * (-s[0]) / (new[0] - s[0]))
        s, t = new, t + dt
    r = run("hodgkin_huxley", {"current_ua_cm2": 10.0, "duration_ms": 50.0, "dt_ms": 0.01})
    assert len(r["spike_times_ms"]) == len(spikes) >= 3
    for a, b in zip(r["spike_times_ms"], spikes):
        assert a == pytest.approx(b, abs=0.02)


def test_class_two_excitability():
    """Hodgkin–Huxley neurons start firing repetitively at a non-zero frequency (class II, Hodgkin 1948 classification)."""
    silent = run("hodgkin_huxley", {"current_ua_cm2": 2.0, "duration_ms": 200.0})
    firing = run("hodgkin_huxley", {"current_ua_cm2": 6.5, "duration_ms": 200.0})
    strong = run("hodgkin_huxley", {"current_ua_cm2": 20.0, "duration_ms": 200.0})
    assert silent["spike_count"] == 0 and firing["firing_rate_hz"] > 40 and strong["firing_rate_hz"] > firing["firing_rate_hz"]


def test_fhn_equilibrium_is_an_exact_root():
    for current in (0.0, 0.5, 1.2):
        r = run("fitzhugh_nagumo", {"current": current, "duration": 1.0})
        v, w = r["equilibrium"]["v"], r["equilibrium"]["w"]
        assert abs(v - v ** 3 / 3 - w + current) < 1e-12 and abs(v + 0.7 - 0.8 * w) < 1e-12


def test_fhn_loses_stability_exactly_at_the_analytical_hopf_current():
    a, b, eps = 0.7, 0.8, 0.08
    v_h = -math.sqrt(1 - eps * b)
    i_h = -(v_h - v_h ** 3 / 3 - (v_h + a) / b)
    assert neuro.fhn_hopf_currents(a, b, eps)[0] == pytest.approx(i_h, rel=1e-12)
    for current, grows in ((i_h - 0.02, False), (i_h + 0.02, True)):
        v_eq, w_eq = neuro.fhn_equilibrium(current, a, b)
        r = run("fitzhugh_nagumo", {"current": current, "initial_v": v_eq + 0.01, "initial_w": w_eq, "duration": 600.0})
        assert r["equilibrium_stable"] is (not grows) and r["oscillating"] is grows, current


@pytest.mark.parametrize("model,inputs,code", [("hodgkin_huxley", {"dt_ms": 0.2}, "invalid_step"), ("fitzhugh_nagumo", {"b": 1.5}, "invalid_parameter")])
def test_invalid_inputs(model, inputs, code):
    with pytest.raises(neuro.NeuronModelError) as exc:
        neuro.hodgkin_huxley(inputs) if model == "hodgkin_huxley" else neuro.fitzhugh_nagumo(inputs)
    assert exc.value.code == code


def test_limitations_rule_out_brain_twin_claims():
    r = run("hodgkin_huxley", {"duration_ms": 5.0})
    assert any("Not a model of mammalian or human neurons" in text for text in r["limitations"])
