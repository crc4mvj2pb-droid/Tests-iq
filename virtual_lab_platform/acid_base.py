"""Aqueous acid–base equilibria (v7.2): exact charge balance for mono- and polyprotic acids at 25 °C.

For each weak acid system HnA with total concentration C and dissociation constants Ka1…Kan, the
fraction of each form follows from [H+] (α_j = Π_{i≤j} Ka_i·h^(n−j) / Σ_k …). The pH is the root of the
charge balance
    h + Σ strong cations + Σ_systems Σ_j (charge of base forms) = Kw/h + Σ strong anions + Σ_systems Σ_j j·C·α_j
found by bisection on log10(h) (the balance is monotonic in h). No Henderson–Hasselbalch approximation is used;
it is reported only for comparison when a single buffer pair is present.

Assumptions: ideal dilute solution (activities = concentrations, ionic strength effects ignored), 25 °C,
Kw = 1.0e-14 (pKw = 14.00, rounded value; 13.995 at 25 °C is often cited).
"""
from __future__ import annotations

import math
from typing import Any

ENGINE_ID = "acid_base_charge_balance"
ENGINE_VERSION = "1.0"
PKW_25C = 14.00


class AcidBaseError(ValueError):
    def __init__(self, message: str, code: str = "invalid_parameter", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def fractions(h: float, pkas: list[float]) -> list[float]:
    """α_0 … α_n for H_nA, H_(n−1)A⁻ … Aⁿ⁻ at hydrogen-ion concentration h (mol/L)."""
    n = len(pkas)
    kas = [10 ** -p for p in pkas]
    terms = []
    for j in range(n + 1):
        prod = 1.0
        for i in range(j):
            prod *= kas[i]
        terms.append(prod * h ** (n - j))
    total = sum(terms)
    return [t / total for t in terms]


def _systems(request: dict[str, Any]) -> list[dict[str, Any]]:
    systems = request.get("weak_systems", [])
    if not isinstance(systems, list) or len(systems) > 10:
        raise AcidBaseError("weak_systems must be a list of at most 10 {name, pka: [...], total_concentration_mol_l, charge_of_fully_protonated}.", "invalid_systems")
    out = []
    for i, s in enumerate(systems):
        try:
            pkas = [float(x) for x in s["pka"]]
            c = float(s["total_concentration_mol_l"])
        except (KeyError, TypeError, ValueError):
            raise AcidBaseError(f"System {i + 1}: pka (list) and total_concentration_mol_l are required.", "invalid_systems") from None
        if not 1 <= len(pkas) <= 4 or any(not -2 <= p <= 16 for p in pkas) or pkas != sorted(pkas):
            raise AcidBaseError(f"System {i + 1}: 1 to 4 increasing pKa values between −2 and 16.", "invalid_systems")
        if not (c >= 0 and math.isfinite(c) and c <= 20):
            raise AcidBaseError(f"System {i + 1}: concentration must be between 0 and 20 mol/L.", "invalid_systems")
        z0 = int(s.get("charge_of_fully_protonated", 0))  # 0 for HnA (acetic acid), +1 for NH4+
        out.append({"name": str(s.get("name") or f"system {i + 1}"), "pka": pkas, "c": c, "z0": z0})
    return out


def charge_balance(h: float, systems, strong_cations: float, strong_anions: float, kw: float) -> float:
    positive = h + strong_cations
    negative = kw / h + strong_anions
    for s in systems:
        alphas = fractions(h, s["pka"])
        for j, a in enumerate(alphas):
            z = s["z0"] - j  # each lost proton lowers the charge by one
            if z > 0:
                positive += z * s["c"] * a
            elif z < 0:
                negative += -z * s["c"] * a
    return positive - negative


def solve_ph(systems, strong_cations: float = 0.0, strong_anions: float = 0.0, pkw: float = PKW_25C) -> float:
    kw = 10 ** -pkw
    lo, hi = -1.5, 15.5  # pH bounds searched (log10 h from −15.5 to 1.5)
    f = lambda ph: charge_balance(10 ** -ph, systems, strong_cations, strong_anions, kw)
    if f(lo) * f(hi) > 0:
        raise AcidBaseError("No pH between −1.5 and 15.5 satisfies the charge balance (check concentrations).", "no_solution")
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def equilibrium(request: dict[str, Any]) -> dict[str, Any]:
    systems = _systems(request)
    cations = float(request.get("strong_base_mol_l", 0.0))   # e.g. Na+ from NaOH or from a sodium salt
    anions = float(request.get("strong_acid_mol_l", 0.0))    # e.g. Cl- from HCl
    if cations < 0 or anions < 0 or not math.isfinite(cations + anions):
        raise AcidBaseError("Strong acid and base concentrations must be ≥ 0.", "invalid_parameter")
    pkw = float(request.get("pkw", PKW_25C))
    ph = solve_ph(systems, cations, anions, pkw)
    h = 10 ** -ph
    species = []
    for s in systems:
        for j, a in enumerate(fractions(h, s["pka"])):
            species.append({"system": s["name"], "protons_lost": j, "charge": s["z0"] - j, "fraction": a, "concentration_mol_l": a * s["c"]})
    residual = charge_balance(h, systems, cations, anions, 10 ** -pkw)
    result = {"model": "acid_base_equilibrium", "status": "computed", "ph": ph, "h_mol_l": h, "oh_mol_l": 10 ** -pkw / h, "pkw": pkw, "species": species,
              "checks": {"charge_balance_residual_mol_l": residual, "fractions_sum_to_one": all(abs(sum(fractions(h, s["pka"])) - 1) < 1e-12 for s in systems)},
              "assumptions": ["Ideal dilute solution: activities taken equal to concentrations (ionic strength ignored)", "25 °C; pKw = 14.00 unless given",
                              "Fully dissociated strong acids and bases"],
              "limitations": ["Above ~0.1 mol/L ionic strength, activity corrections change pH by several hundredths or more", "No precipitation, complexation or gas exchange (CO2)"]}
    if len(systems) == 1 and len(systems[0]["pka"]) == 1 and systems[0]["z0"] == 0 and 0 < cations < systems[0]["c"]:
        s = systems[0]
        result["henderson_hasselbalch_ph"] = s["pka"][0] + math.log10(cations / (s["c"] - cations))
        result["henderson_hasselbalch_note"] = "Approximation for comparison only; the reported pH is the exact charge-balance solution."
    return result


def titration(request: dict[str, Any]) -> dict[str, Any]:
    """Titration of a weak acid system (volume V0) by a strong base (concentration Cb) — dilution included."""
    systems = _systems({"weak_systems": [request.get("analyte")]} if request.get("analyte") else {})
    if len(systems) != 1:
        raise AcidBaseError("analyte {name, pka, total_concentration_mol_l} is required.", "invalid_systems")
    v0, cb, vmax = float(request.get("analyte_volume_ml", 25.0)), float(request.get("titrant_concentration_mol_l", 0.1)), float(request.get("max_titrant_ml", 50.0))
    points = int(request.get("points", 101))
    if not (v0 > 0 and cb > 0 and vmax > 0 and 3 <= points <= 2001):
        raise AcidBaseError("Volumes and titrant concentration must be > 0, points between 3 and 2001.", "invalid_parameter")
    s = systems[0]
    rows = []
    for i in range(points):
        v = vmax * i / (points - 1)
        total = v0 + v
        diluted = [{**s, "c": s["c"] * v0 / total}]
        rows.append({"titrant_ml": v, "ph": solve_ph(diluted, strong_cations=cb * v / total)})
    equivalence = [s["c"] * v0 * (j + 1) / cb for j in range(len(s["pka"]))]
    return {"model": "acid_base_titration", "status": "computed", "rows": rows, "equivalence_volumes_ml": equivalence,
            "half_equivalence_ph_expected_near_pka": s["pka"][0], "assumptions": ["Same as acid_base_equilibrium; volumes additive"]}
