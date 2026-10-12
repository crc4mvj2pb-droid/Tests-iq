"""v5.4 — workbench RC/RL transients and series RLC step response, checked against independent references."""
from __future__ import annotations

import math

import pytest

import experiment_service
import history
from electrical_advanced import simulate_series_rlc_step
from numerics import Tolerances, dopri5
from workbench_circuit import WorkbenchCircuitError
from workbench_transient import solve_workbench_transient


def W(a, pa, b, pb):
    return {"a": a, "pinA": pa, "b": b, "pinB": pb}


def comp(iid, kind, qty, unit=None):
    return {"instanceId": iid, "id": kind, "displayName": iid, "qty": qty, **({"unit": unit} if unit else {})}


def rc_divider(c_qty=1e-6, c_unit="F"):
    return {"components": [comp("s", "dc-source", 10), comp("r1", "resistor", 1000), comp("r2", "resistor", 1000), comp("c", "capacitor", c_qty, c_unit), comp("g", "ground", 0)],
            "connections": [W("s", "N", "g", "GND"), W("s", "P", "r1", "A"), W("r1", "B", "r2", "A"), W("r2", "B", "g", "GND"), W("c", "A", "r1", "B"), W("c", "B", "g", "GND")]}


def test_rc_divider_matches_hand_thevenin():
    d = solve_workbench_transient(rc_divider())
    assert d["thevenin_voltage_v"] == pytest.approx(5.0, rel=1e-12) and d["thevenin_resistance_ohm"] == pytest.approx(500.0, rel=1e-12)
    assert d["time_constant_s"] == pytest.approx(5e-4, rel=1e-12)
    for row in d["rows"]:
        assert row["element_voltage_v"] == pytest.approx(5 * (1 - math.exp(-row["time_s"] / 5e-4)), abs=1e-12)
    assert d["checks"]["energy_balance_relative_error"] < 1e-3


def test_capacitance_unit_is_converted():
    assert solve_workbench_transient(rc_divider(1, "µF"))["time_constant_s"] == pytest.approx(5e-4, rel=1e-12)
    with pytest.raises(WorkbenchCircuitError) as exc:
        solve_workbench_transient(rc_divider(1, "Ω"))
    assert exc.value.code == "invalid_reactive_value"


def test_rl_circuit_matches_hand_thevenin():
    req = {"components": [comp("s", "dc-source", 12), comp("r1", "resistor", 100), comp("r2", "resistor", 300), comp("l", "inductor", 0.1, "H"), comp("g", "ground", 0)],
           "connections": [W("s", "N", "g", "GND"), W("s", "P", "r1", "A"), W("r1", "B", "r2", "A"), W("r2", "B", "g", "GND"), W("l", "A", "r1", "B"), W("l", "B", "g", "GND")]}
    d = solve_workbench_transient(req)
    v_th, r_th = 12 * 300 / 400, 100 * 300 / 400
    assert d["thevenin_voltage_v"] == pytest.approx(v_th) and d["thevenin_resistance_ohm"] == pytest.approx(r_th)
    tau = 0.1 / r_th
    assert d["time_constant_s"] == pytest.approx(tau) and d["final_value"] == pytest.approx(v_th / r_th)
    mid = d["rows"][100]
    assert mid["element_current_a"] == pytest.approx(v_th / r_th * (1 - math.exp(-mid["time_s"] / tau)), rel=1e-10)


def test_capacitor_across_a_wheatstone_bridge():
    r1, r2, r3, r4, v = 1000, 2000, 3000, 1500, 9.0
    req = {"components": [comp("s", "dc-source", v), comp("r1", "resistor", r1), comp("r2", "resistor", r2), comp("r3", "resistor", r3), comp("r4", "resistor", r4),
                          comp("c", "capacitor", 2e-6, "F"), comp("g", "ground", 0)],
           "connections": [W("s", "N", "g", "GND"), W("s", "P", "r1", "A"), W("s", "P", "r3", "A"), W("r1", "B", "r2", "A"), W("r2", "B", "g", "GND"),
                           W("r3", "B", "r4", "A"), W("r4", "B", "g", "GND"), W("c", "A", "r1", "B"), W("c", "B", "r3", "B")]}
    d = solve_workbench_transient(req)
    v_th = v * (r2 / (r1 + r2) - r4 / (r3 + r4))
    r_th = r1 * r2 / (r1 + r2) + r3 * r4 / (r3 + r4)
    assert d["thevenin_voltage_v"] == pytest.approx(v_th, rel=1e-12) and d["thevenin_resistance_ohm"] == pytest.approx(r_th, rel=1e-12)
    assert d["time_constant_s"] == pytest.approx(r_th * 2e-6, rel=1e-12)


def test_initial_state_and_discharge():
    d = solve_workbench_transient({**rc_divider(), "initial_voltage_v": 10.0})
    assert d["rows"][0]["element_voltage_v"] == pytest.approx(10.0) and d["rows"][-1]["element_voltage_v"] == pytest.approx(5 + 5 * math.exp(-5), rel=1e-12)


@pytest.mark.parametrize("variant,code", [("two_capacitors", "reactive_count"), ("across_source", "reactive_across_source"), ("zero_value", "invalid_reactive_value"),
                                          ("bool_value", "invalid_reactive_value")])
def test_unsupported_transients_are_refused(variant, code):
    req = rc_divider()
    if variant == "two_capacitors":
        req["components"].append(comp("c2", "capacitor", 1e-6, "F")); req["connections"] += [W("c2", "A", "r1", "B"), W("c2", "B", "g", "GND")]
    elif variant == "across_source":
        req["connections"] = [W("s", "N", "g", "GND"), W("s", "P", "r1", "A"), W("r1", "B", "r2", "A"), W("r2", "B", "g", "GND"), W("c", "A", "s", "P"), W("c", "B", "g", "GND")]
    elif variant == "zero_value":
        req["components"][3]["qty"] = 0
    else:
        req["components"][3]["qty"] = True
    with pytest.raises(WorkbenchCircuitError) as exc:
        solve_workbench_transient(req)
    assert exc.value.code == code


@pytest.mark.parametrize("resistance,regime", [(10, "underdamped"), (200, "critically_damped"), (2000, "overdamped")])
def test_rlc_step_matches_independent_numerical_integration(resistance, regime):
    L, C, V, v0, i0 = 0.01, 1e-6, 5.0, 1.0, 0.002
    d = simulate_series_rlc_step({"source_voltage_v": V, "resistance_ohm": resistance, "inductance_h": L, "capacitance_f": C,
                                  "initial_capacitor_voltage_v": v0, "initial_current_a": i0, "points": 201})
    assert d["regime"] == regime
    # Independent reference: integrate C·v' = i, L·i' = V − v − R·i with the adaptive Dormand–Prince method.
    times = [r["time_s"] for r in d["points"]]
    states, _ = dopri5(lambda t, y: [y[1] / C, (V - y[0] - resistance * y[1]) / L], 0.0, [v0, i0], times[-1], times, Tolerances(rtol=1e-11, atol=1e-14))
    for row, (v, i) in zip(d["points"], states):
        assert row["capacitor_voltage_v"] == pytest.approx(v, abs=1e-7)
        assert row["current_a"] == pytest.approx(i, abs=1e-9)


@pytest.mark.parametrize("resistance", [10, 200, 2000])
def test_rlc_energy_balance(resistance):
    L, C, V = 0.01, 1e-6, 5.0
    d = simulate_series_rlc_step({"source_voltage_v": V, "resistance_ohm": resistance, "inductance_h": L, "capacitance_f": C, "points": 5001})
    p = d["points"]
    supplied = sum((p[k + 1]["time_s"] - p[k]["time_s"]) * V * (p[k]["current_a"] + p[k + 1]["current_a"]) / 2 for k in range(len(p) - 1))
    dissipated = sum((p[k + 1]["time_s"] - p[k]["time_s"]) * resistance * (p[k]["current_a"] ** 2 + p[k + 1]["current_a"] ** 2) / 2 for k in range(len(p) - 1))
    stored = p[-1]["stored_energy_j"] - p[0]["stored_energy_j"]
    assert supplied == pytest.approx(dissipated + stored, rel=2e-3)


def test_transient_is_saved_and_replayed(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v54.sqlite3")
    d = experiment_service.run_workbench_transient({**rc_divider(), "initial_voltage_v": 2.0})
    assert d["configuration"]["initial_voltage_v"] == 2.0
    replay = experiment_service.replay(d["history_record"]["id"])
    assert replay["replay_comparison"]["identical_within_tolerance"] and replay["replay_comparison"]["compared_values"] > 400
