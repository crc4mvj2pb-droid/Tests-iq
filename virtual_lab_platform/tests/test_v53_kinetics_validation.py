"""v5.3 — kinetics validated against analytical solutions with every integrator; conservation and positivity."""
from __future__ import annotations

import pytest

from benchmarks.kinetics_analytic import CASES, max_abs_error
from chemical_kinetics import simulate_reaction_network

SETTINGS = {"rk4": ({"dt": 0.05}, 2e-7), "dopri5": ({"dt": 0.1, "rtol": 1e-8, "atol": 1e-11}, 5e-8), "implicit_euler": ({"dt": 0.1, "rtol": 1e-6, "atol": 1e-9}, 2e-6)}


@pytest.mark.parametrize("method", list(SETTINGS))
@pytest.mark.parametrize("case", list(CASES))
def test_trajectory_matches_analytical_solution(case, method):
    settings, bound = SETTINGS[method]
    d = simulate_reaction_network({**CASES[case]["request"], "method": method, **settings})
    assert max_abs_error(d, CASES[case]["exact"]) < bound
    assert all(row[sid] >= 0 for row in d["rows"] for sid in d["species_ids"])  # positivity


@pytest.mark.parametrize("method", list(SETTINGS))
@pytest.mark.parametrize("case", list(CASES))
def test_final_error_is_not_underestimated_by_much(case, method):
    settings, _ = SETTINGS[method]
    d = simulate_reaction_network({**CASES[case]["request"], "method": method, **settings})
    ref = CASES[case]["exact"](d["rows"][-1]["time"])
    true_final = max(abs(d["summary"]["final_concentrations"][sid] - v) for sid, v in ref.items())
    estimate = max(d["summary"]["estimated_final_error"].values())
    assert estimate >= 0.1 * true_final or true_final < 1e-13, (true_final, estimate)


@pytest.mark.parametrize("method", list(SETTINGS))
def test_element_totals_are_conserved(method):
    settings, _ = SETTINGS[method]
    d = simulate_reaction_network({
        "species": [{"id": "N2O4", "initial_concentration": 1.0, "atoms": {"N": 2, "O": 4}}, {"id": "NO2", "initial_concentration": 0.1, "atoms": {"N": 1, "O": 2}}],
        "reactions": [{"id": "f", "reactants": {"N2O4": 1}, "products": {"NO2": 2}, "rate_constant": 0.9},
                      {"id": "b", "reactants": {"NO2": 2}, "products": {"N2O4": 1}, "rate_constant": 0.4}],
        "duration": 5.0, "method": method, **settings})
    c = d["summary"]["element_conservation"]
    assert c["initial"] == {"N": pytest.approx(2.1), "O": pytest.approx(4.2)}
    assert c["max_relative_drift"] < 1e-9


def test_conservation_is_not_reported_without_formulas():
    d = simulate_reaction_network({**CASES["first_order"]["request"], "dt": 0.1})
    assert d["summary"]["element_conservation"] is None


def test_every_case_has_a_consistent_exact_solution_at_t0():
    # Guard against typos in the reference formulas: t = 0 must give the initial concentrations.
    for case in CASES.values():
        initial = {s["id"]: s["initial_concentration"] for s in case["request"]["species"]}
        for sid, value in case["exact"](0.0).items():
            assert value == pytest.approx(initial[sid], abs=1e-12)
