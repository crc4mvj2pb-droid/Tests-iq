"""First-order transients of workbench circuits (v5.4): one capacitor OR one inductor + resistors + DC source.

The resistive network seen by the reactive element is reduced to its Thévenin equivalent with the
DC solver validated in v4.4, so the transient is exact (one time constant):
- R_th: source short-circuited, 1 V applied across the element's terminals, R_th = 1 V / current;
- V_th: element replaced by a test resistor R_t, V_th = V_t·(R_t + R_th)/R_t.
Capacitor: v(t) = V_th + (v0 − V_th)·e^(−t/τ), τ = R_th·C. Inductor: i(t) = I_N + (i0 − I_N)·e^(−t/τ),
I_N = V_th/R_th, τ = L/R_th. Circuits with two or more reactive elements are refused.
"""
from __future__ import annotations

import math

import units
from electrical_circuits import CircuitError, solve_dc_circuit
from workbench_circuit import PINS, WorkbenchCircuitError, solve_workbench_circuit

ENGINE_ID = "workbench_first_order_transient"
ENGINE_VERSION = "1.0"
REACTIVE = {"capacitor": ("C", "F"), "capacitor2": ("C", "F"), "inductor": ("L", "H")}
TEST_RESISTANCE = 1000.0


def _value(item: dict, expected_unit: str) -> float:
    label = str(item.get("displayName") or item.get("id"))
    raw = item.get("qty")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
        raise WorkbenchCircuitError(f"Enter a numeric value for '{label}'.", "invalid_reactive_value", name=label)
    try:
        value = units.convert(float(raw), item.get("unit") or expected_unit, expected_unit)
    except units.UnitError as exc:
        raise WorkbenchCircuitError(f"'{label}': {exc}", "invalid_reactive_value", name=label) from exc
    if value <= 0 or value > 1e6:
        raise WorkbenchCircuitError(f"The value of '{label}' must be > 0 and ≤ 1e6 {expected_unit}.", "invalid_reactive_value", name=label)
    return value


def solve_workbench_transient(request: dict) -> dict:
    components, connections = request.get("components"), request.get("connections")
    if not isinstance(components, list) or not isinstance(connections, list):
        raise WorkbenchCircuitError("The workbench must provide component and wire lists.", "invalid_request")
    wired = {c.get("a") for c in connections if isinstance(c, dict)} | {c.get("b") for c in connections if isinstance(c, dict)}
    reactive = [c for c in components if isinstance(c, dict) and c.get("id") in REACTIVE and c.get("instanceId") in wired]
    if len(reactive) != 1:
        raise WorkbenchCircuitError(
            f"The transient solver needs exactly one wired capacitor or inductor (found {len(reactive)}). "
            "Two or more reactive elements form a higher-order circuit, not supported on the workbench (use the series RLC model).",
            "reactive_count", count=len(reactive))
    element = reactive[0]
    kind, unit = REACTIVE[element["id"]]
    value = _value(element, unit)
    label = str(element.get("displayName") or element["id"])

    # V_t: the element replaced by a test resistor, solved by the validated DC workbench solver.
    test_id = element["instanceId"]
    test_components = [dict(c, id="resistor", qty=TEST_RESISTANCE) if c is element else c for c in components]
    dc = solve_workbench_circuit({"components": test_components, "connections": connections})
    test_branch = next(b for b in dc["branches"] if b["id"].endswith(":" + test_id))
    v_test = test_branch["voltage_v"]  # V(A) − V(B) of the element's terminals

    # R_th: source shorted, 1 V applied between the element's nodes (other resistors unchanged).
    a, b = test_branch["a"], test_branch["b"]
    merge = lambda n: "0" if n == "SOURCE_PLUS" else n
    a, b = merge(a), merge(b)
    if a == b:
        raise WorkbenchCircuitError(f"'{label}' is directly across the ideal source: its transient is instantaneous (capacitor) or unbounded "
                                    "(inductor). Add a series resistor.", "reactive_across_source", name=label)
    network = [{**r, "a": merge(r["a"]), "b": merge(r["b"])} for r in dc["topology"]["netlist"] if not r["id"].endswith(":" + test_id)]
    network = [r for r in network if r["a"] != r["b"]]
    component = _component(network, {a, b})
    try:
        probe = solve_dc_circuit({"source_voltage": 1.0, "ground": b, "source_node": a, "resistors": component})
        conductance = abs(probe["source_current_a"])
    except CircuitError:
        conductance = 0.0
    if not component or conductance <= 0:
        raise WorkbenchCircuitError(f"'{label}' is not on a closed resistive path: no current can charge or discharge it.", "reactive_not_in_loop", name=label)
    r_th = 1.0 / conductance
    v_th = v_test * (TEST_RESISTANCE + r_th) / TEST_RESISTANCE

    tau = r_th * value if kind == "C" else value / r_th
    # Initial state with its own unit: capacitor voltage in V, inductor current in A.
    initial = request.get("initial_voltage_v" if kind == "C" else "initial_current_a", 0.0)
    if isinstance(initial, bool) or not isinstance(initial, (int, float)):
        raise WorkbenchCircuitError("The initial state must be a number.", "invalid_request")
    initial = float(initial)
    if not math.isfinite(initial):
        raise WorkbenchCircuitError("initial_value must be finite.", "invalid_request")
    duration = float(request.get("duration_s") or 5 * tau)
    points = int(request.get("points", 201))
    if not (duration > 0 and math.isfinite(duration)) or not 2 <= points <= 2001:
        raise WorkbenchCircuitError("duration_s must be > 0 and points between 2 and 2001.", "invalid_request")
    rows = []
    for i in range(points):
        t = duration * i / (points - 1)
        decay = math.exp(-t / tau)
        if kind == "C":
            v = v_th + (initial - v_th) * decay
            current = (v_th - v) / r_th  # into terminal A of the capacitor
            energy = 0.5 * value * v * v
        else:
            current = v_th / r_th + (initial - v_th / r_th) * decay  # from A to B through the inductor
            v = v_th - r_th * current
            energy = 0.5 * value * current * current
        rows.append({"time_s": t, "element_voltage_v": v, "element_current_a": current, "stored_energy_j": energy,
                     "thevenin_source_power_w": v_th * current, "thevenin_resistor_power_w": r_th * current * current})
    # Energy balance over the simulated interval, from the closed forms: supplied = dissipated + Δstored.
    supplied = _trapezoid(rows, "thevenin_source_power_w")
    dissipated = _trapezoid(rows, "thevenin_resistor_power_w")
    stored = rows[-1]["stored_energy_j"] - rows[0]["stored_energy_j"]
    scale = max(abs(supplied), abs(dissipated), abs(stored), 1e-300)
    return {
        "model": f"workbench_first_order_{kind.lower()}_transient", "status": "computed", "element": {"name": label, "kind": "capacitor" if kind == "C" else "inductor",
                                                                                                       "value": value, "unit": unit},
        "thevenin_voltage_v": v_th, "thevenin_resistance_ohm": r_th, "time_constant_s": tau, "duration_s": duration,
        "initial_value": initial, "initial_value_unit": "V" if kind == "C" else "A",
        "final_value": v_th if kind == "C" else v_th / r_th, "rows": rows,
        "checks": {"energy_supplied_j": supplied, "energy_dissipated_j": dissipated, "energy_stored_change_j": stored,
                   "energy_balance_relative_error": abs(supplied - dissipated - stored) / scale,
                   "note": "trapezoidal integration of the sampled closed-form powers; the error decreases with more points"},
        "dc_reference": {"test_resistance_ohm": TEST_RESISTANCE, "test_voltage_v": v_test, "warnings": dc.get("warnings", [])},
        "conventions": {"element_voltage": "V(A) − V(B) of the reactive element", "element_current": "from terminal A to B inside the element"},
        "assumptions": ["Ideal linear capacitor or inductor; ideal DC source switched on at t = 0 with the given initial state.",
                        "The rest of the circuit is linear and resistive, reduced exactly to its Thévenin equivalent."],
        "limitations": ["Only one reactive element; node voltages of the rest of the circuit are not traced over time.",
                        "No switch events, no AC sources, no nonlinear devices; not SPICE."],
    }


def _trapezoid(rows, key):
    return sum((rows[i + 1]["time_s"] - rows[i]["time_s"]) * (rows[i + 1][key] + rows[i][key]) / 2 for i in range(len(rows) - 1))


def _component(resistors, start_nodes):
    """Resistors connected (through other resistors) to the given nodes; the rest cannot carry probe current."""
    reached, changed = set(start_nodes), True
    while changed:
        changed = False
        for r in resistors:
            if (r["a"] in reached) != (r["b"] in reached):
                reached |= {r["a"], r["b"]}; changed = True
    return [r for r in resistors if r["a"] in reached and r["b"] in reached]
