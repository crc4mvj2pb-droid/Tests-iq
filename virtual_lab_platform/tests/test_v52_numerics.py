"""v5.2 — tolerances, convergence, stiffness, failure diagnostics and uncertainty kinds."""
from __future__ import annotations

import math

import pytest

import numerics
from chemical_kinetics import ChemicalKineticsError, simulate_reaction_network
from numerics import NumericalError, Tolerances, dopri5, implicit_euler

# Robertson's stiff chemical kinetics problem, reference solution at t = 40
# (E. Hairer & G. Wanner, Solving Ordinary Differential Equations II, Springer 1996, §IV.10).
ROBERTSON_T40 = {"A": 0.7158270687, "B": 9.185534764e-6, "C": 0.2841637457}


def robertson(method, **extra):
    return {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}, {"id": "C", "initial_concentration": 0.0}],
            "reactions": [{"id": "r1", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.04},
                          {"id": "r2", "reactants": {"B": 2}, "products": {"B": 1, "C": 1}, "rate_constant": 3e7},
                          {"id": "r3", "reactants": {"B": 1, "C": 1}, "products": {"A": 1, "C": 1}, "rate_constant": 1e4}],
            "duration": 40.0, "dt": 4.0, "method": method, **extra}


def first_order(method="rk4", k=1.0, dt=0.1, **extra):
    return {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
            "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": k}], "duration": 1.0, "dt": dt, "method": method, **extra}


def test_stiff_robertson_problem_matches_published_reference_with_implicit_method():
    d = simulate_reaction_network(robertson("implicit_euler", rtol=1e-7, atol=1e-12))
    final = d["summary"]["final_concentrations"]
    for sid, ref in ROBERTSON_T40.items():
        assert final[sid] == pytest.approx(ref, rel=2e-3), sid
    assert abs(sum(final.values()) - 1.0) < 1e-8  # linear invariant A+B+C conserved
    assert d["diagnostics"]["status"] == "converged" and d["diagnostics"]["accepted_steps"] > 0


def test_explicit_methods_refuse_the_stiff_problem_instead_of_returning_a_wrong_result():
    with pytest.raises(ChemicalKineticsError, match="Negative concentration"):
        simulate_reaction_network(robertson("rk4", dt=0.01))
    with pytest.raises(NumericalError) as exc:
        simulate_reaction_network(robertson("dopri5", max_steps=20000))
    assert exc.value.code in ("max_steps_exceeded", "step_size_underflow") and "implicit_euler" in str(exc.value) or exc.value.code == "step_size_underflow"
    assert exc.value.params["diagnostics"]["accepted_steps"] > 0


def test_rk4_observed_order_is_four():
    errors = [abs(simulate_reaction_network(first_order(dt=dt))["summary"]["final_concentrations"]["A"] - math.exp(-1)) for dt in (0.1, 0.05, 0.025)]
    orders = [math.log2(errors[i] / errors[i + 1]) for i in range(2)]
    assert all(3.8 < o < 4.2 for o in orders), orders


@pytest.mark.parametrize("method", ["dopri5", "implicit_euler"])
def test_adaptive_error_decreases_with_tolerance_and_is_estimated(method):
    errors = []
    for rtol in (1e-4, 1e-6, 1e-8):
        d = simulate_reaction_network(first_order(method, rtol=rtol, atol=rtol * 1e-3))
        true_error = abs(d["summary"]["final_concentrations"]["A"] - math.exp(-1))
        estimate = d["summary"]["estimated_final_error"]["A"]
        errors.append(true_error)
        assert true_error <= 100 * rtol
        # Honest estimate: never much below the true error, never absurdly pessimistic.
        assert 0.1 * true_error <= estimate <= max(1000 * true_error, 10 * rtol), (rtol, true_error, estimate)
        assert estimate > 0 or true_error == 0
    # Non-increasing (output times can impose identical steps for loose tolerances), and decreasing overall.
    assert errors[0] >= errors[1] >= errors[2] and errors[0] > errors[2]


def test_dopri5_harmonic_oscillator_over_ten_periods():
    f = lambda t, y: [y[1], -y[0]]
    times = [2 * math.pi * k for k in range(11)]
    states, diag = dopri5(f, 0.0, [1.0, 0.0], times[-1], times, Tolerances(rtol=1e-10, atol=1e-12))
    assert len(states) == 11 and all(abs(s[0] - 1.0) < 1e-7 and abs(s[1]) < 1e-7 for s in states)
    assert diag["status"] == "converged" and diag["rejected_steps"] >= 0


@pytest.mark.parametrize("solver", [dopri5, implicit_euler])
def test_blow_up_is_reported_not_returned(solver):
    # y' = y² from y(0)=1 has a singularity at t = 1.
    with pytest.raises(NumericalError) as exc:
        solver(lambda t, y: [y[0] ** 2], 0.0, [1.0], 2.0, [2.0], Tolerances(rtol=1e-6, atol=1e-9, max_steps=50000))
    assert exc.value.code in ("non_finite", "step_size_underflow", "max_steps_exceeded", "non_convergence")
    assert "diagnostics" in exc.value.params


def test_step_budget_and_tolerance_validation():
    with pytest.raises(NumericalError) as exc:
        dopri5(lambda t, y: [math.cos(50 * t)], 0.0, [0.0], 100.0, [100.0], Tolerances(rtol=1e-10, atol=1e-12, max_steps=50))
    assert exc.value.code == "max_steps_exceeded" and exc.value.params["diagnostics"]["accepted_steps"] + exc.value.params["diagnostics"]["rejected_steps"] == 50
    for bad in (Tolerances(rtol=1.0), Tolerances(atol=0), Tolerances(max_steps=1)):
        with pytest.raises(NumericalError) as exc:
            dopri5(lambda t, y: [0.0], 0.0, [1.0], 1.0, [1.0], bad)
        assert exc.value.code == "invalid_tolerance"


def test_edge_cases_zero_rate_and_output_at_start():
    d = simulate_reaction_network(first_order("dopri5", k=0.0))
    assert d["summary"]["final_concentrations"]["A"] == 1.0 and d["rows"][0]["time"] == 0.0
    states, _ = implicit_euler(lambda t, y: [0.0], 0.0, [3.0], 1.0, [0.0, 1.0])
    assert states == [[3.0], [3.0]]


def test_uncertainty_kinds_are_separated_in_results():
    for method in ("rk4", "dopri5", "implicit_euler"):
        u = simulate_reaction_network(first_order(method))["uncertainty_breakdown"]
        assert set(u) == {"numerical", "parameter", "measurement"} and u["numerical"]["estimated_final_error"] is not None
    assert set(numerics.UNCERTAINTY_KINDS) == {"numerical", "parameter", "measurement"}


def test_invalid_method_is_refused():
    with pytest.raises(ChemicalKineticsError, match="method must be one of"):
        simulate_reaction_network(first_order("euler"))


def test_adaptive_run_is_saved_and_replayed_with_method_and_unit(tmp_path, monkeypatch):
    import experiment_service, history
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v52.sqlite3")
    d = experiment_service.run_kinetics(first_order("implicit_euler", rtol=1e-7, concentration_unit="mmol/L"))
    assert d["configuration"]["method"] == "implicit_euler" and d["configuration"]["concentration_unit"] == "mmol/L"
    replay = experiment_service.replay(d["history_record"]["id"])
    assert replay["method"] == "implicit_euler" and replay["concentration_unit"] == "mmol/L"
    assert replay["replay_comparison"]["identical_within_tolerance"]
