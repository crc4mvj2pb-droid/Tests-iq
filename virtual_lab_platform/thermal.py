"""Thermal models with one time constant and steady 1D conduction (v7.1).

lumped_thermal_transient — body of uniform temperature heated by P and losing heat through R_th:
    C·dT/dt = P − (T − T_amb)/R_th  ⇒  T(t) = T_ss + (T0 − T_ss)·e^(−t/τ), T_ss = T_amb + P·R_th, τ = R_th·C.
    Validity of the lumped assumption: Biot number Bi = h·L_c/k < 0.1 (Incropera et al., §5.1), checked when h, L_c, k are given.
plane_wall_conduction — steady heat flow through plane layers in series, with optional surface convection:
    q = (T_hot − T_cold)/ΣR, R_layer = L/(k·A), R_conv = 1/(h·A); interface temperatures from the cumulative resistances.
"""
from __future__ import annotations

import math
from typing import Any

ENGINE_ID = "thermal_lumped_and_conduction"
ENGINE_VERSION = "1.0"
BIOT_LIMIT = 0.1


class ThermalError(ValueError):
    def __init__(self, message: str, code: str = "invalid_parameter", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def lumped_transient(p: dict[str, Any]) -> dict[str, Any]:
    # Defaults identical to the contract's (checked by tests/test_v50_contracts.py).
    power, t_amb = p.get("power_w", 3.0), p.get("ambient_temperature_k", 298.15)
    r_th, c_th = p.get("thermal_resistance_k_per_w", 4.0), p.get("thermal_capacitance_j_per_k", 5.0)
    t0 = p.get("initial_temperature_k", t_amb)
    tau = r_th * c_th
    t_ss = t_amb + power * r_th
    duration = p.get("duration_s") or 5 * tau
    points = p.get("points", 201)
    rows = []
    for i in range(points):
        t = duration * i / (points - 1)
        temp = t_ss + (t0 - t_ss) * math.exp(-t / tau)
        rows.append({"time_s": t, "temperature_k": temp, "heat_loss_w": (temp - t_amb) / r_th, "stored_energy_j": c_th * (temp - t0)})
    supplied = power * duration
    lost = sum((rows[i + 1]["time_s"] - rows[i]["time_s"]) * (rows[i + 1]["heat_loss_w"] + rows[i]["heat_loss_w"]) / 2 for i in range(points - 1))
    stored = rows[-1]["stored_energy_j"]
    warnings, biot = [], None
    if all(p.get(k) is not None for k in ("convection_coefficient_w_m2k", "characteristic_length_m", "conductivity_w_mk")):
        biot = p["convection_coefficient_w_m2k"] * p["characteristic_length_m"] / p["conductivity_w_mk"]
        if biot >= BIOT_LIMIT:
            warnings.append({"code": "lumped_assumption_invalid", "message": f"Biot number {biot:.3g} ≥ {BIOT_LIMIT}: the body is not at a uniform temperature; "
                                                                             "the one-time-constant model is not valid (use a conduction model)."})
    elif p.get("convection_coefficient_w_m2k") is not None or p.get("characteristic_length_m") is not None or p.get("conductivity_w_mk") is not None:
        raise ThermalError("Give h, characteristic length and conductivity together to check the Biot number.", "incomplete_biot_inputs")
    return {"model": "lumped_thermal_transient", "status": "computed", "time_constant_s": tau, "steady_temperature_k": t_ss,
            "final_temperature_k": rows[-1]["temperature_k"], "duration_s": duration, "rows": rows, "biot_number": biot, "warnings": warnings,
            "checks": {"energy_supplied_j": supplied, "energy_lost_j": lost, "energy_stored_j": stored,
                       "energy_balance_relative_error": abs(supplied - lost - stored) / max(supplied, abs(lost), abs(stored), 1e-300),
                       "note": "losses integrated by trapezoids on the sampled closed form; the error decreases with more points"},
            "assumptions": ["Uniform body temperature (lumped capacitance)", "Constant power, resistance and capacitance", "Ambient temperature constant"],
            "limitations": ["Valid only when Bi < 0.1", "No radiation non-linearity, no phase change"]}


def plane_wall(p: dict[str, Any]) -> dict[str, Any]:
    layers, area = p.get("layers"), p.get("area_m2", 1.0)
    if not isinstance(layers, list) or not 1 <= len(layers) <= 20:
        raise ThermalError("layers must list 1 to 20 layers {name, thickness_m, conductivity_w_mk}.", "invalid_layers")
    resistances = []
    h_hot, h_cold = p.get("h_hot_w_m2k"), p.get("h_cold_w_m2k")
    if h_hot is not None:
        resistances.append(("convection (hot side)", 1.0 / (h_hot * area)))
    for i, layer in enumerate(layers):
        try:
            thickness, k = float(layer["thickness_m"]), float(layer["conductivity_w_mk"])
        except (KeyError, TypeError, ValueError):
            raise ThermalError(f"Layer {i + 1}: thickness_m and conductivity_w_mk are required numbers.", "invalid_layers") from None
        if not (thickness > 0 and k > 0 and math.isfinite(thickness) and math.isfinite(k)):
            raise ThermalError(f"Layer {i + 1}: thickness and conductivity must be > 0.", "invalid_layers")
        resistances.append((str(layer.get("name") or f"layer {i + 1}"), thickness / (k * area)))
    if h_cold is not None:
        resistances.append(("convection (cold side)", 1.0 / (h_cold * area)))
    total = sum(r for _, r in resistances)
    t_hot, t_cold = p.get("hot_temperature_k", 293.15), p.get("cold_temperature_k", 273.15)
    q = (t_hot - t_cold) / total
    temperatures, current = [{"position": "hot fluid" if h_hot is not None else "hot surface", "temperature_k": t_hot}], t_hot
    for name, r in resistances:
        current -= q * r
        temperatures.append({"position": f"after {name}", "temperature_k": current})
    return {"model": "plane_wall_conduction", "status": "computed", "heat_rate_w": q, "heat_flux_w_m2": q / area, "total_resistance_k_per_w": total,
            "u_value_w_m2k": 1.0 / (total * area), "resistances": [{"element": n, "resistance_k_per_w": r} for n, r in resistances], "temperatures": temperatures,
            "checks": {"cold_side_recovered_k": temperatures[-1]["temperature_k"], "closure_error_k": abs(temperatures[-1]["temperature_k"] - t_cold)},
            "assumptions": ["Steady state", "One-dimensional conduction, constant conductivities", "Perfect contact between layers"],
            "limitations": ["No contact resistance, no thermal bridges, no radiation"]}
