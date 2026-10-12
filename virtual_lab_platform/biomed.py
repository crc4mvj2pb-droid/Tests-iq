"""Exploratory biomedical models (v7.5): closed-form growth and aggregation kinetics.

EXPLORATORY ONLY. These equations are used in the literature to describe tumour growth curves and
protein aggregation kinetics, but here they are not fitted to any patient or clinical dataset. They
must not be used for diagnosis, prognosis, treatment decisions or as clinical predictions.

Gompertz growth (Gompertz 1825; Laird 1964): dV/dt = r·V·ln(K/V)  ⇒  V(t) = K·exp(ln(V0/K)·e^(−r·t)).
Finke–Watzky two-step aggregation (Watzky & Finke 1997): A → B (k1), A + B → 2B (k2)
    [B](t) = A0 − (k1/k2 + A0) / (1 + (k1/(k2·A0))·e^((k1 + k2·A0)·t)).
"""
from __future__ import annotations

import math
from typing import Any

ENGINE_ID = "exploratory_biomedical_closed_forms"
ENGINE_VERSION = "1.0"
DISCLAIMER = ("Exploratory model: not fitted to clinical data; not for diagnosis, prognosis, treatment decisions or clinical prediction.")


class BiomedError(ValueError):
    def __init__(self, message: str, code: str = "invalid_parameter", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def _grid(duration: float, points: int):
    if not (duration > 0 and math.isfinite(duration)) or not 3 <= points <= 5001:
        raise BiomedError("duration must be > 0 and points between 3 and 5001.")
    return [duration * i / (points - 1) for i in range(points)]


def gompertz(p: dict[str, Any]) -> dict[str, Any]:
    v0, k, r = float(p.get("initial_size", 1.0)), float(p.get("carrying_capacity", 100.0)), float(p.get("growth_rate", 0.1))
    if not (0 < v0 and 0 < k and r >= 0):
        raise BiomedError("initial_size and carrying_capacity must be > 0 and growth_rate ≥ 0.")
    rows = [{"time": t, "size": k * math.exp(math.log(v0 / k) * math.exp(-r * t))} for t in _grid(float(p.get("duration", 60.0)), int(p.get("points", 121)))]
    inflection = math.log(math.log(k / v0)) / r if r > 0 and v0 < k / math.e else None  # V = K/e at the inflection
    return {"model": "gompertz_growth", "status": "computed", "rows": rows, "final_size": rows[-1]["size"], "inflection_time": inflection,
            "doubling_time_initial": math.log(2) / (r * math.log(k / v0)) if r > 0 and v0 < k else None,
            "disclaimer": DISCLAIMER, "assumptions": ["Deterministic growth with a constant decay of the specific growth rate"],
            "limitations": ["No treatment, immune or spatial effects", DISCLAIMER]}


def finke_watzky(p: dict[str, Any]) -> dict[str, Any]:
    a0, k1, k2 = float(p.get("initial_monomer", 1.0)), float(p.get("k1", 1e-3)), float(p.get("k2", 1.0))
    if not (a0 > 0 and k1 > 0 and k2 > 0):
        raise BiomedError("initial_monomer, k1 and k2 must be > 0.")
    def b_of(t):
        x = (k1 + k2 * a0) * t
        if x > 700:  # e^x overflows; the second term vanishes
            return a0
        return a0 - (k1 / k2 + a0) / (1 + k1 / (k2 * a0) * math.exp(x))
    rows = [{"time": t, "aggregate": b_of(t), "monomer": a0 - b_of(t)} for t in _grid(float(p.get("duration", 20.0)), int(p.get("points", 201)))]
    # time to half conversion, from [B] = A0/2: 1 + (k1/(k2 A0)) e^x = 2(k1/k2 + A0)/A0
    t_half = math.log((2 * (k1 / k2 + a0) / a0 - 1) * k2 * a0 / k1) / (k1 + k2 * a0)
    return {"model": "finke_watzky_aggregation", "status": "computed", "rows": rows, "half_conversion_time": t_half, "final_aggregate": rows[-1]["aggregate"],
            "disclaimer": DISCLAIMER, "assumptions": ["Two pseudo-elementary steps: nucleation A→B and autocatalytic growth A+B→2B", "Closed, well-mixed system"],
            "limitations": ["Phenomenological: rate constants are not molecular mechanisms", DISCLAIMER]}
