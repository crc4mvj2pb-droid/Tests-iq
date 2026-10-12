"""v4.4 — DC solver checked against independent references and topology diagnostics.

References used here do not call the application's solver:
- closed-form formulas (series, parallel, divider, Wheatstone bridge via Thevenin, R-2R ladder);
- an exact rational-arithmetic nodal solver written below (fractions.Fraction, Gauss-Jordan),
  sharing no code with electrical_circuits.py.
"""
from __future__ import annotations

import math
import random
from fractions import Fraction

import pytest

from electrical_circuits import solve_dc_circuit
from workbench_circuit import WorkbenchCircuitError, solve_workbench_circuit


def exact_nodal(voltage, resistors, source="S", ground="0"):
    nodes = sorted({n for r in resistors for n in (r["a"], r["b"])} - {source, ground})
    idx = {n: i for i, n in enumerate(nodes)}
    size = len(nodes)
    g = [[Fraction(0)] * size + [Fraction(0)] for _ in range(size)]
    fixed = {source: Fraction(voltage), ground: Fraction(0)}
    for r in resistors:
        cond = 1 / Fraction(r["resistance_ohm"])
        for x, y in ((r["a"], r["b"]), (r["b"], r["a"])):
            if x in idx:
                g[idx[x]][idx[x]] += cond
                if y in idx:
                    g[idx[x]][idx[y]] -= cond
                else:
                    g[idx[x]][size] += cond * fixed[y]
    for col in range(size):
        piv = next(r for r in range(col, size) if g[r][col] != 0)
        g[col], g[piv] = g[piv], g[col]
        g[col] = [v / g[col][col] for v in g[col]]
        for r in range(size):
            if r != col and g[r][col] != 0:
                f = g[r][col]; g[r] = [a - f * b for a, b in zip(g[r], g[col])]
    v = dict(fixed); v.update({n: g[idx[n]][size] for n in nodes})
    return v


def net(voltage, resistors):
    return solve_dc_circuit({"source_voltage": voltage, "ground": "0", "source_node": "S", "resistors": resistors})


def R(rid, a, b, ohm):
    return {"id": rid, "a": a, "b": b, "resistance_ohm": ohm}


def close(x, y, rel=1e-10):
    return math.isclose(float(x), float(y), rel_tol=rel, abs_tol=1e-15)


def test_series_parallel_divider_closed_forms(evidence=None):
    d = net(12, [R("R1", "S", "N", 1000), R("R2", "N", "0", 2000)])
    assert close(d["source_current_a"], 12 / 3000) and close(d["node_voltages_v"]["N"], 12 * 2000 / 3000)
    d = net(5, [R("R1", "S", "0", 100), R("R2", "S", "0", 400)])
    assert close(d["equivalent_resistance_ohm"], 1 / (1 / 100 + 1 / 400))
    assert d["checks"]["numerically_consistent"] is True


@pytest.mark.parametrize("r1,r2,r3,r4,rg", [(100, 200, 300, 600, 50), (1000, 1000, 1000, 1000, 470), (220, 470, 330, 100, 1e6)])
def test_wheatstone_bridge_matches_thevenin_formula(r1, r2, r3, r4, rg):
    v = 10.0
    # Left divider S-R1-A-R2-0, right divider S-R3-B-R4-0, galvanometer resistor Rg between A and B.
    d = net(v, [R("R1", "S", "A", r1), R("R2", "A", "0", r2), R("R3", "S", "B", r3), R("R4", "B", "0", r4), R("Rg", "A", "B", rg)])
    v_th = v * (r2 / (r1 + r2) - r4 / (r3 + r4))
    r_th = r1 * r2 / (r1 + r2) + r3 * r4 / (r3 + r4)
    i_g = v_th / (r_th + rg)
    galvanometer = next(b for b in d["branches"] if b["id"] == "Rg")
    assert math.isclose(galvanometer["current_a"], i_g, rel_tol=1e-9, abs_tol=1e-15)


@pytest.mark.parametrize("stages", [1, 3, 6])
def test_r2r_ladder_halves_voltage_at_each_stage(stages):
    # Classic R-2R ladder: series R between taps, 2R to ground at each tap, 2R termination at the last tap.
    res, prev = [], "S"
    for k in range(1, stages + 1):
        tap = f"T{k}"
        res.append(R(f"Rs{k}", prev, tap, 1000)); res.append(R(f"Rp{k}", tap, "0", 2000)); prev = tap
    # Input resistance of an infinite-equivalent R-2R section terminated in 2R is 2R, so each tap is half the previous.
    d = net(8, [R("Rin", "S", "T0", 2000), R("Rt", "T0", "0", 2000)] if stages == 0 else res[:-1] + [R(f"Rp{stages}", prev, "0", 1000)])
    for k in range(1, stages + 1):
        assert close(d["node_voltages_v"][f"T{k}"], 8 / 2 ** k, rel=1e-9)


@pytest.mark.parametrize("seed", range(12))
def test_random_networks_match_exact_rational_solver(seed):
    rng = random.Random(seed)
    nodes = ["S", "0"] + [f"N{i}" for i in range(rng.randint(1, 7))]
    resistors, k = [], 0
    for i, node in enumerate(nodes[2:]):  # spanning chain guarantees every node is connected
        k += 1; resistors.append(R(f"R{k}", rng.choice(nodes[:2 + i]), node, rng.choice([1, 47, 220, 1e3, 4.7e4, 1e6])))
    for _ in range(rng.randint(1, 8)):
        a, b = rng.sample(nodes, 2)
        k += 1; resistors.append(R(f"R{k}", a, b, round(rng.uniform(1, 1e5), 3)))
    voltage = rng.uniform(-50, 50)
    d, exact = net(voltage, resistors), exact_nodal(voltage, resistors)
    for node, value in exact.items():
        assert math.isclose(d["node_voltages_v"][node], float(value), rel_tol=1e-9, abs_tol=1e-9)
    assert d["checks"]["kcl_satisfied"] and d["checks"]["power_balance_satisfied"]


def test_extreme_but_valid_resistances_are_solved():
    d = net(9, [R("R1", "S", "N", 1e15), R("R2", "N", "0", 1e15)])
    assert close(d["node_voltages_v"]["N"], 4.5)
    d = net(9, [R("R1", "S", "N", 1), R("R2", "N", "0", 1e9)])
    assert close(d["node_voltages_v"]["N"], 9 * 1e9 / (1e9 + 1)) and d["checks"]["numerically_consistent"] and d["warnings"] == []


def test_precision_loss_at_extreme_ratio_is_flagged_not_hidden():
    # 1 mΩ in series with 1 TΩ (ratio 1e15): the tiny branch voltage is a difference of nearly equal numbers.
    d = net(9, [R("R1", "S", "N", 1e-3), R("R2", "N", "0", 1e12)])
    assert close(d["node_voltages_v"]["N"], 9 * 1e12 / (1e12 + 1e-3))
    assert [w["code"] for w in d["warnings"]] == ["numerical_precision"]
    assert "R1" in d["warnings"][0]["params"]["names"] and "R2" not in d["warnings"][0]["params"]["names"]
    assert d["checks"]["kcl_satisfied"] and d["checks"]["power_balance_satisfied"]  # within the propagated bounds


def test_sign_conventions_are_explicit_and_consistent():
    d = net(-6, [R("R1", "S", "0", 3)])
    assert d["source_current_a"] == pytest.approx(-2.0) and d["branches"][0]["current_a"] == pytest.approx(-2.0)
    assert d["source_power_supplied_w"] == pytest.approx(12.0) and d["branches"][0]["power_w"] == pytest.approx(12.0)
    assert "a to terminal b" in d["conventions"]["branch_current"]
    assert d["checks"]["source_loop_residual_a"] == pytest.approx(0.0, abs=1e-15)


# ---- workbench topology diagnostics -------------------------------------------------------------

def comp(iid, kind, qty=1):
    return {"instanceId": iid, "id": kind, "displayName": iid, "qty": qty}


def W(a, pa, b, pb):
    return {"a": a, "pinA": pa, "b": b, "pinB": pb}


BASE = [comp("V", "dc-source", 9), comp("G", "ground", 0), comp("R1", "resistor", 1000)]
BASE_W = [W("V", "N", "G", "GND"), W("V", "P", "R1", "A"), W("R1", "B", "G", "GND")]


def test_floating_subnetwork_is_named_before_solving():
    req = {"components": BASE + [comp("Ra", "resistor", 10), comp("Rb", "resistor", 20)],
           "connections": BASE_W + [W("Ra", "A", "Rb", "A"), W("Ra", "B", "Rb", "B")]}
    with pytest.raises(WorkbenchCircuitError) as exc:
        solve_workbench_circuit(req)
    assert exc.value.code == "floating_network" and "Ra" in exc.value.params["names"] and "Rb" in exc.value.params["names"]


def test_branch_hanging_from_a_single_node_is_reported_with_zero_current():
    # D1 links the source + net to n1; D2 and D3 are in parallel between n1 and n2: no return path.
    req = {"components": BASE + [comp("D1", "resistor", 10), comp("D2", "resistor", 20), comp("D3", "resistor", 30)],
           "connections": BASE_W + [W("D1", "A", "V", "P"), W("D1", "B", "D2", "A"), W("D2", "A", "D3", "A"), W("D2", "B", "D3", "B")]}
    d = solve_workbench_circuit(req)
    dead = next(w for w in d["warnings"] if w["code"] == "dead_end_branch")["params"]["names"]
    assert all(n in dead for n in ("D1", "D2", "D3")) and "R1" not in dead
    for b in d["branches"]:
        if b["display_name"] in ("D1", "D2", "D3"):
            assert abs(b["current_a"]) < 1e-15


def test_bridge_resistor_on_a_cycle_is_not_reported():
    # R2 closes a second loop (parallel to R1): both carry current, no warning.
    d = solve_workbench_circuit({"components": BASE + [comp("R2", "resistor", 500)],
                                 "connections": BASE_W + [W("R2", "A", "V", "P"), W("R2", "B", "G", "GND")]})
    assert not [w for w in d["warnings"] if w["code"] == "dead_end_branch"]


def test_unwired_unsupported_components_are_listed_as_ignored():
    d = solve_workbench_circuit({"components": BASE + [comp("LED1", "led")], "connections": BASE_W})
    assert d["ignored_components"] == ["LED1"]
    assert any(w["code"] == "ignored_components" for w in d["warnings"])
    assert d["source_current_a"] == pytest.approx(0.009)


@pytest.mark.parametrize("qty", [True, None, "", "1k", float("nan"), -5, 0, 2e15])
def test_invalid_resistance_values_are_rejected_with_code(qty):
    comps = [dict(c) for c in BASE]; comps[2]["qty"] = qty
    with pytest.raises(WorkbenchCircuitError) as exc:
        solve_workbench_circuit({"components": comps, "connections": BASE_W})
    assert exc.value.code == "invalid_resistance"


def _random_network(seed, values):
    rng = random.Random(seed)
    nodes = ["S", "0"] + [f"N{i}" for i in range(rng.randint(1, 9))]
    resistors, k = [], 0
    for i, node in enumerate(nodes[2:]):
        k += 1; resistors.append(R(f"R{k}", rng.choice(nodes[:2 + i]), node, rng.choice(values)))
    for _ in range(rng.randint(0, 10)):
        a, b = rng.sample(nodes, 2)
        k += 1; resistors.append(R(f"R{k}", a, b, rng.choice(values) * rng.uniform(0.5, 2)))
    return rng.uniform(-100, 100), resistors


@pytest.mark.parametrize("seed", range(300))
def test_reported_uncertainty_bounds_the_true_error(seed):
    # Ill-conditioned on purpose: resistances spread over nine decades.
    voltage, resistors = _random_network(seed, [1, 10, 1e3, 1e5, 1e7, 1e9])
    d, exact = net(voltage, resistors), exact_nodal(voltage, resistors)
    for node, value in exact.items():
        error = abs(d["node_voltages_v"][node] - float(value))
        assert error <= d["node_voltage_uncertainty_v"][node] + 1e-300, (node, error)
    for b in d["branches"]:
        true_current = float((exact[b["a"]] - exact[b["b"]]) / Fraction(b["resistance_ohm"]))
        assert abs(b["current_a"] - true_current) <= b["current_rounding_uncertainty_a"] + 1e-300
    assert d["checks"]["kcl_satisfied"] and d["checks"]["power_balance_satisfied"]


def test_largest_accepted_network_solves_quickly():
    import time
    rng = random.Random(1)
    nodes = ["S", "0"] + [f"N{i}" for i in range(120)]
    resistors = [R(f"C{i}", nodes[i], nodes[i + 1], rng.uniform(10, 1e4)) for i in range(1, len(nodes) - 1)]
    resistors.append(R("C0", "S", "N0", 100))
    resistors += [R(f"X{i}", rng.choice(nodes), rng.choice(nodes[2:]), rng.uniform(10, 1e4)) for i in range(200 - len(resistors))]
    resistors = [r for r in resistors if r["a"] != r["b"]]
    started = time.perf_counter()
    d = net(12, resistors)
    assert time.perf_counter() - started < 10 and d["checks"]["numerically_consistent"]
