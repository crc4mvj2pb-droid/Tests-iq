"""Analytical reference solutions for mass-action kinetics (v5.3).

Each case gives a request for chemical_kinetics.simulate_reaction_network and the exact
concentrations as functions of time, derived by hand (standard results of chemical kinetics,
e.g. Atkins & de Paula, Physical Chemistry; Espenson, Chemical Kinetics and Reaction Mechanisms).
"""
from __future__ import annotations

import math


def _sp(**c0):
    return [{"id": k, "initial_concentration": v} for k, v in c0.items()]


def _rx(rid, reactants, products, k):
    return {"id": rid, "reactants": reactants, "products": products, "rate_constant": k}


CASES = {
    "first_order": {
        "description": "A → B, k = 0.7 s⁻¹ : [A] = A0·e^(−kt)",
        "request": {"species": _sp(A=1.0, B=0.0), "reactions": [_rx("r", {"A": 1}, {"B": 1}, 0.7)], "duration": 5.0},
        "exact": lambda t: {"A": math.exp(-0.7 * t), "B": 1 - math.exp(-0.7 * t)},
    },
    "consecutive": {
        "description": "A → B → C, k1 = 1.0, k2 = 0.4 s⁻¹ : [B] = A0·k1/(k2−k1)·(e^(−k1t) − e^(−k2t))",
        "request": {"species": _sp(A=1.0, B=0.0, C=0.0), "reactions": [_rx("r1", {"A": 1}, {"B": 1}, 1.0), _rx("r2", {"B": 1}, {"C": 1}, 0.4)], "duration": 8.0},
        "exact": lambda t: {"A": math.exp(-t), "B": 1.0 / (0.4 - 1.0) * (math.exp(-t) - math.exp(-0.4 * t)),
                            "C": 1 - math.exp(-t) - 1.0 / (0.4 - 1.0) * (math.exp(-t) - math.exp(-0.4 * t))},
    },
    "consecutive_equal_rates": {
        "description": "A → B → C with k1 = k2 = 0.5 s⁻¹ (degenerate case) : [B] = A0·k·t·e^(−kt)",
        "request": {"species": _sp(A=1.0, B=0.0, C=0.0), "reactions": [_rx("r1", {"A": 1}, {"B": 1}, 0.5), _rx("r2", {"B": 1}, {"C": 1}, 0.5)], "duration": 8.0},
        "exact": lambda t: {"A": math.exp(-0.5 * t), "B": 0.5 * t * math.exp(-0.5 * t), "C": 1 - math.exp(-0.5 * t) - 0.5 * t * math.exp(-0.5 * t)},
    },
    "second_order_dimerisation": {
        "description": "2A → P, k = 0.5 : d[A]/dt = −2k[A]² ⇒ [A] = A0/(1 + 2k·A0·t)",
        "request": {"species": _sp(A=1.0, P=0.0), "reactions": [_rx("r", {"A": 2}, {"P": 1}, 0.5)], "duration": 10.0},
        "exact": lambda t: {"A": 1 / (1 + t), "P": 0.5 * (1 - 1 / (1 + t))},
    },
    "mixed_second_order": {
        "description": "A + B → P, k = 0.3, A0 = 1, B0 = 2 : [A] = A0(B0−A0)/(B0·e^((B0−A0)kt) − A0)",
        "request": {"species": _sp(A=1.0, B=2.0, P=0.0), "reactions": [_rx("r", {"A": 1, "B": 1}, {"P": 1}, 0.3)], "duration": 10.0},
        "exact": lambda t: (lambda a: {"A": a, "B": a + 1.0, "P": 1.0 - a})(1.0 * (2.0 - 1.0) / (2.0 * math.exp((2.0 - 1.0) * 0.3 * t) - 1.0)),
    },
    "reversible": {
        "description": "A ⇌ B, kf = 0.8, kr = 0.2 : [A] = A_eq + (A0 − A_eq)·e^(−(kf+kr)t), A_eq = kr/(kf+kr)",
        "request": {"species": _sp(A=1.0, B=0.0), "reactions": [_rx("f", {"A": 1}, {"B": 1}, 0.8), _rx("b", {"B": 1}, {"A": 1}, 0.2)], "duration": 6.0},
        "exact": lambda t: {"A": 0.2 + 0.8 * math.exp(-t), "B": 0.8 - 0.8 * math.exp(-t)},
    },
    "parallel": {
        "description": "A → B (k1 = 0.6), A → C (k2 = 0.2) : [B] = k1/(k1+k2)·A0·(1 − e^(−(k1+k2)t))",
        "request": {"species": _sp(A=1.0, B=0.0, C=0.0), "reactions": [_rx("r1", {"A": 1}, {"B": 1}, 0.6), _rx("r2", {"A": 1}, {"C": 1}, 0.2)], "duration": 8.0},
        "exact": lambda t: {"A": math.exp(-0.8 * t), "B": 0.75 * (1 - math.exp(-0.8 * t)), "C": 0.25 * (1 - math.exp(-0.8 * t))},
    },
}


def max_abs_error(result: dict, exact) -> float:
    """Largest |computed − exact| over every sampled row and species."""
    worst = 0.0
    for row in result["rows"]:
        ref = exact(row["time"])
        for sid, value in ref.items():
            worst = max(worst, abs(row[sid] - value))
    return worst
