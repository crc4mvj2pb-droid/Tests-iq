"""Classical single-neuron models (v7.4): Hodgkin–Huxley (1952) and FitzHugh–Nagumo.

These are mathematical models of a patch of membrane or of excitability in general. They are not
models of a human brain, of a network, or of any patient; they are bounded teaching and research tools.

Hodgkin–Huxley, squid giant axon, modern sign convention (resting potential ≈ −65 mV):
  C·dV/dt = I − g_Na·m³h·(V − E_Na) − g_K·n⁴·(V − E_K) − g_L·(V − E_L)
  dx/dt = α_x(V)(1 − x) − β_x(V)·x for x ∈ {m, h, n}; rate functions as in Hodgkin & Huxley (1952), shifted to V_rest = −65 mV.
FitzHugh–Nagumo (FitzHugh 1961):
  dv/dt = v − v³/3 − w + I,  dw/dt = ε·(v + a − b·w).
"""
from __future__ import annotations

import math
from typing import Any

ENGINE_ID = "single_neuron_models"
ENGINE_VERSION = "1.0"
HH_DEFAULTS = {"capacitance_uf_cm2": 1.0, "g_na_ms_cm2": 120.0, "g_k_ms_cm2": 36.0, "g_l_ms_cm2": 0.3,
               "e_na_mv": 50.0, "e_k_mv": -77.0, "e_l_mv": -54.387}


class NeuronModelError(ValueError):
    def __init__(self, message: str, code: str = "invalid_parameter", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def _ratio(x: float, scale: float) -> float:
    """x / (1 − e^(−x/scale)), with its limit `scale` at x = 0 (removable singularity of α_n and α_m)."""
    return scale * (1 + x / (2 * scale)) if abs(x) < 1e-7 else x / (1 - math.exp(-x / scale))


def rates(v: float) -> dict[str, float]:
    return {"an": 0.01 * _ratio(v + 55.0, 10.0), "bn": 0.125 * math.exp(-(v + 65.0) / 80.0),
            "am": 0.1 * _ratio(v + 40.0, 10.0), "bm": 4.0 * math.exp(-(v + 65.0) / 18.0),
            "ah": 0.07 * math.exp(-(v + 65.0) / 20.0), "bh": 1.0 / (1.0 + math.exp(-(v + 35.0) / 10.0))}


def steady_gates(v: float) -> tuple[float, float, float]:
    r = rates(v)
    return r["am"] / (r["am"] + r["bm"]), r["ah"] / (r["ah"] + r["bh"]), r["an"] / (r["an"] + r["bn"])


def _hh_rhs(state, p, current):
    v, m, h, n = state
    r = rates(v)
    i_ion = p["g_na_ms_cm2"] * m ** 3 * h * (v - p["e_na_mv"]) + p["g_k_ms_cm2"] * n ** 4 * (v - p["e_k_mv"]) + p["g_l_ms_cm2"] * (v - p["e_l_mv"])
    return ((current - i_ion) / p["capacitance_uf_cm2"], r["am"] * (1 - m) - r["bm"] * m, r["ah"] * (1 - h) - r["bh"] * h, r["an"] * (1 - n) - r["bn"] * n)


def hodgkin_huxley(params: dict[str, Any]) -> dict[str, Any]:
    p = {k: float(params.get(k, v)) for k, v in HH_DEFAULTS.items()}
    current = float(params.get("current_ua_cm2", 10.0))
    duration, dt = float(params.get("duration_ms", 100.0)), float(params.get("dt_ms", 0.01))
    onset = float(params.get("current_onset_ms", 0.0))
    if not (0 < dt <= 0.05) or not (0 < duration <= 5000) or duration / dt > 1_000_000:
        raise NeuronModelError("dt_ms must be in (0, 0.05] (explicit RK4 stability) and duration_ms in (0, 5000].", "invalid_step")
    v0 = float(params.get("initial_voltage_mv", -65.0))
    state = (v0, *steady_gates(v0))
    steps = int(round(duration / dt))
    sample = max(1, steps // 2000)
    rows, spikes = [{"time_ms": 0.0, "membrane_voltage_mv": v0, "m": state[1], "h": state[2], "n": state[3]}], []
    for i in range(steps):
        t = i * dt
        inj = current if t >= onset else 0.0
        k1 = _hh_rhs(state, p, inj)
        k2 = _hh_rhs(tuple(s + dt / 2 * k for s, k in zip(state, k1)), p, inj)
        k3 = _hh_rhs(tuple(s + dt / 2 * k for s, k in zip(state, k2)), p, inj)
        k4 = _hh_rhs(tuple(s + dt * k for s, k in zip(state, k3)), p, inj)
        new = tuple(s + dt / 6 * (a + 2 * b + 2 * c + d) for s, a, b, c, d in zip(state, k1, k2, k3, k4))
        if not all(math.isfinite(x) for x in new):
            raise NeuronModelError("Integration diverged; reduce dt_ms.", "numerical_instability")
        if state[0] < 0.0 <= new[0]:  # upward crossing of 0 mV, interpolated
            spikes.append(t + dt * (0.0 - state[0]) / (new[0] - state[0]))
        state = new
        if (i + 1) % sample == 0 or i == steps - 1:
            rows.append({"time_ms": (i + 1) * dt, "membrane_voltage_mv": state[0], "m": state[1], "h": state[2], "n": state[3]})
    isi = [b - a for a, b in zip(spikes, spikes[1:])]
    return {"model": "hodgkin_huxley", "status": "computed", "rows": rows, "spike_times_ms": spikes, "spike_count": len(spikes),
            "mean_isi_ms": sum(isi[1:]) / len(isi[1:]) if len(isi) > 1 else None,
            "firing_rate_hz": 1000.0 / (sum(isi[1:]) / len(isi[1:])) if len(isi) > 1 else 0.0,
            "final_voltage_mv": state[0], "parameters": {**p, "current_ua_cm2": current},
            "assumptions": ["Space-clamped membrane patch (no propagation)", "Squid giant axon parameters at 6.3 °C", "Constant injected current density"],
            "limitations": ["Not a model of mammalian or human neurons, networks or brain function", "Spikes detected as upward crossings of 0 mV"]}


def fhn_equilibrium(current: float, a: float, b: float) -> tuple[float, float]:
    """Unique equilibrium for b < 1 (monotonic cubic): v − v³/3 − (v + a)/b + I = 0, solved by bisection."""
    f = lambda v: v - v ** 3 / 3 - (v + a) / b + current
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    v = (lo + hi) / 2
    return v, (v + a) / b


def fhn_hopf_currents(a: float, b: float, eps: float) -> list[float]:
    """Currents at which the equilibrium loses stability: trace of the Jacobian 1 − v² − ε·b = 0."""
    if 1 - eps * b <= 0:
        return []
    out = []
    for v in (-math.sqrt(1 - eps * b), math.sqrt(1 - eps * b)):
        out.append(-(v - v ** 3 / 3 - (v + a) / b))
    return sorted(out)


def fitzhugh_nagumo(params: dict[str, Any]) -> dict[str, Any]:
    a, b, eps = float(params.get("a", 0.7)), float(params.get("b", 0.8)), float(params.get("epsilon", 0.08))
    current = float(params.get("current", 0.5))
    duration, dt = float(params.get("duration", 200.0)), float(params.get("dt", 0.01))
    if not (0 < b < 1):
        raise NeuronModelError("This implementation requires 0 < b < 1 (single equilibrium).", "invalid_parameter")
    if not (0 < dt <= 0.1) or not (0 < duration <= 10000) or duration / dt > 1_000_000:
        raise NeuronModelError("dt must be in (0, 0.1] and duration in (0, 10000].", "invalid_step")
    v, w = float(params.get("initial_v", -1.2)), float(params.get("initial_w", -0.6))
    f = lambda v, w: (v - v ** 3 / 3 - w + current, eps * (v + a - b * w))
    steps, rows = int(round(duration / dt)), []
    sample = max(1, steps // 2000)
    rows.append({"time": 0.0, "v": v, "w": w})
    for i in range(steps):
        k1 = f(v, w); k2 = f(v + dt / 2 * k1[0], w + dt / 2 * k1[1]); k3 = f(v + dt / 2 * k2[0], w + dt / 2 * k2[1]); k4 = f(v + dt * k3[0], w + dt * k3[1])
        v += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]); w += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        if (i + 1) % sample == 0 or i == steps - 1:
            rows.append({"time": (i + 1) * dt, "v": v, "w": w})
    tail = [r["v"] for r in rows if r["time"] >= duration / 2]
    v_eq, w_eq = fhn_equilibrium(current, a, b)
    trace = 1 - v_eq ** 2 - eps * b
    return {"model": "fitzhugh_nagumo", "status": "computed", "rows": rows, "equilibrium": {"v": v_eq, "w": w_eq},
            "equilibrium_stable": trace < 0, "hopf_currents": fhn_hopf_currents(a, b, eps),
            "late_amplitude": max(tail) - min(tail), "oscillating": (max(tail) - min(tail)) > 0.5,
            "assumptions": ["Two-variable reduction of excitable dynamics in dimensionless units"],
            "limitations": ["Qualitative model: no physiological units, not fitted to any neuron"]}
