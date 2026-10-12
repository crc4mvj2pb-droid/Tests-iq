"""v7.5 — exploratory biomedical models: closed forms verified, disclaimers present, no clinical claim."""
from __future__ import annotations

import math

import pytest

import biomed
import domains
import model_registry


def run(model, inputs):
    return model_registry.run_model(model, inputs)["result"]


def _rk4(f, y, t_end, dt):
    for _ in range(int(round(t_end / dt))):
        k1 = f(y); k2 = f([a + dt / 2 * b for a, b in zip(y, k1)]); k3 = f([a + dt / 2 * b for a, b in zip(y, k2)]); k4 = f([a + dt * b for a, b in zip(y, k3)])
        y = [a + dt / 6 * (b + 2 * c + 2 * d + e) for a, b, c, d, e in zip(y, k1, k2, k3, k4)]
    return y


def test_gompertz_against_independent_integration():
    v0, k, r, t = 2.0, 500.0, 0.15, 40.0
    d = run("gompertz_growth", {"initial_size": v0, "carrying_capacity": k, "growth_rate": r, "duration": t, "points": 5})
    reference = _rk4(lambda y: [r * y[0] * math.log(k / y[0])], [v0], t, 1e-3)[0]
    assert d["final_size"] == pytest.approx(reference, rel=1e-9)
    assert d["inflection_time"] == pytest.approx(math.log(math.log(k / v0)) / r)


def test_finke_watzky_against_independent_integration():
    a0, k1, k2, t = 2.0, 5e-3, 0.8, 6.0
    d = run("finke_watzky_aggregation", {"initial_monomer": a0, "k1": k1, "k2": k2, "duration": t, "points": 5})
    b = _rk4(lambda y: [k1 * (a0 - y[0]) + k2 * (a0 - y[0]) * y[0]], [0.0], t, 1e-4)[0]
    assert d["final_aggregate"] == pytest.approx(b, abs=1e-9)
    half = run("finke_watzky_aggregation", {"initial_monomer": a0, "k1": k1, "k2": k2, "duration": d["half_conversion_time"], "points": 3})
    assert half["final_aggregate"] == pytest.approx(a0 / 2, rel=1e-12)


def test_finke_watzky_mass_conservation():
    d = run("finke_watzky_aggregation", {})
    assert all(abs(r["aggregate"] + r["monomer"] - 1.0) < 1e-12 for r in d["rows"])
    long = run("finke_watzky_aggregation", {"duration": 1e5, "points": 3})
    assert long["final_aggregate"] == pytest.approx(1.0)  # overflow-safe at long times


def test_disclaimers_everywhere():
    for model in ("gompertz_growth", "finke_watzky_aggregation"):
        d = run(model, {})
        contract = model_registry.get_contract(model)
        assert "not for diagnosis" in d["disclaimer"] and biomed.DISCLAIMER in contract["assumptions"]
    bio = next(x for x in domains.all_domains() if x["id"] == "exploratory_biomedical")
    assert {"gompertz_growth", "finke_watzky_aggregation"} <= {m["id"] for m in bio["models"]} and "conseil médical" in bio["disclaimer"]


@pytest.mark.parametrize("model,inputs", [("gompertz_growth", {"initial_size": 0.0}), ("finke_watzky_aggregation", {"k1": 0.0})])
def test_invalid_inputs_are_refused(model, inputs):
    with pytest.raises(Exception):
        run(model, inputs)
