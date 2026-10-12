"""Research question → variables, testable hypotheses and evaluation criteria (v8.1).

Rule-based (no language model). From a question such as "Quel est l'effet de la résistance sur la
constante de temps ?" it identifies, using only the model contracts:
  - the model able to answer (a contract with that parameter and that output);
  - the independent variable (a contract parameter, with unit and bounds), the dependent variable
    (a declared output, with unit) and the controlled variables (all other parameters, at stated values);
  - testable hypotheses: H1 (the output increases with the parameter), H2 (it decreases), H0 (no effect),
    each with an explicit, computable evaluation criterion;
  - what is missing: when the parameter, the output or the model is ambiguous or absent, it asks for a
    clarification listing the valid choices instead of guessing.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import maturity
import model_registry

EFFECT_THRESHOLD = 0.05  # |normalised sensitivity| below this value counts as "no effect" (H0)

PARAMETER_WORDS = {
    "resistance_ohm": ("resistance",), "capacitance_f": ("capacite", "capacitance", "condensateur"), "inductance_h": ("inductance", "bobine"),
    "source_voltage_v": ("tension", "voltage"), "temperature_k": ("temperature",), "activation_energy_j_mol": ("energie d'activation", "activation energy"),
    "pre_exponential_s_inv": ("facteur pre-exponentiel", "pre-exponential"), "power_w": ("puissance", "power"),
    "thermal_resistance_k_per_w": ("resistance thermique", "thermal resistance"), "thermal_capacitance_j_per_k": ("capacite thermique", "heat capacity"),
    "current_ua_cm2": ("courant", "current"), "growth_rate": ("taux de croissance", "growth rate"), "carrying_capacity": ("capacite d'accueil", "carrying capacity"),
    "beta": ("taux de transmission", "transmission rate", "beta"), "gamma": ("taux de guerison", "recovery rate", "gamma"),
    "frequency_hz": ("frequence", "frequency"), "strong_base_mol_l": ("base forte", "strong base"), "strong_acid_mol_l": ("acide fort", "strong acid"),
}
OUTPUT_WORDS = {
    "time_constant": ("constante de temps", "time constant"), "rate_constant": ("constante de vitesse", "rate constant", "vitesse de reaction"),
    "steady_temperature": ("temperature stationnaire", "temperature d'equilibre", "steady temperature", "temperature finale"),
    "firing_rate": ("frequence de decharge", "firing rate", "frequence des potentiels"), "peak_infectious": ("pic epidemique", "pic d'infectes", "epidemic peak"),
    "final_population": ("population finale", "final population"), "ph": ("ph",), "impedance_magnitude": ("impedance",),
    "current_rms": ("courant efficace", "rms current"), "heat_rate": ("flux de chaleur", "heat flow", "heat rate"), "final_size": ("taille finale", "final size"),
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower().replace("’", "'"))
    return "".join(c for c in text if not unicodedata.combining(c))


def _find(text: str, table: dict[str, tuple]) -> list[str]:
    """Names whose longest matching phrase appears in the text; longer phrases win over their own sub-phrases."""
    hits = []
    for name, words in table.items():
        best = max((len(w) for w in words if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text)), default=0)
        if best:
            hits.append((best, name, [w for w in words if len(w) == best][0]))
    hits.sort(reverse=True)
    kept, used = [], []
    for length, name, phrase in hits:
        if any(phrase in other for other in used):
            continue
        kept.append(name); used.append(phrase)
    return kept


def formulate(question: str) -> dict[str, Any]:
    text = _norm(question if isinstance(question, str) else "")
    params, outputs = _find(text, PARAMETER_WORDS), _find(text, OUTPUT_WORDS)
    base = {"question": question, "method": "rule-based extraction from model contracts (not a language model)"}
    if not outputs:
        return {**base, "status": "clarification_needed", "missing": ["dependent_variable"],
                "message": "Which quantity should be observed?", "choices": sorted(OUTPUT_WORDS)}
    if not params:
        return {**base, "status": "clarification_needed", "missing": ["independent_variable"],
                "message": "Which parameter should be varied?", "choices": sorted(PARAMETER_WORDS)}
    candidates = []
    for c in model_registry.list_contracts():
        names = {p["name"]: p for p in c["parameters"]}
        outs = {o["name"]: o for o in c["outputs"]}
        for out in outputs:
            for par in params:
                if par in names and out in outs and names[par]["type"] in ("number", "integer") and "default" in names[par]:
                    candidates.append((c, names[par], outs[out]))
    if not candidates:
        return {**base, "status": "unknown", "message": f"No model of the platform has the parameter(s) {params} and the output(s) {outputs} together."}
    models = sorted({c["id"] for c, _, _ in candidates})
    if len(models) > 1:
        return {**base, "status": "clarification_needed", "missing": ["model"], "message": "Several models fit this question; choose one.", "choices": models}
    contract, par, out = candidates[0]
    controlled = [{"name": p["name"], "value": p.get("default"), "unit": p.get("unit") or p.get("unit_from"), "provenance": (p.get("default_provenance") or {}).get("status")}
                  for p in contract["parameters"] if p["name"] != par["name"] and p["type"] in ("number", "integer") and "default" in p]
    criterion = (f"normalised sensitivity S = (∂y/∂x)·(x/y) at the reference point, and the sign of the change of y over the swept range; "
                 f"|S| < {EFFECT_THRESHOLD} → H0")
    return {**base, "status": "formulated", "model_id": contract["id"], "model_title": contract["title"],
            "model_maturity": maturity.maturity_of(contract["id"])["level"],
            "independent_variable": {"name": par["name"], "unit": par.get("unit"), "reference_value": par.get("default"),
                                     "minimum": par.get("minimum"), "maximum": par.get("maximum")},
            "dependent_variable": {"name": out["name"], "unit": out["unit"]},
            "controlled_variables": controlled,
            "hypotheses": [{"id": "H1", "statement": f"{out['name']} increases when {par['name']} increases", "test": f"S > {EFFECT_THRESHOLD} and y monotonically increasing"},
                           {"id": "H2", "statement": f"{out['name']} decreases when {par['name']} increases", "test": f"S < −{EFFECT_THRESHOLD} and y monotonically decreasing"},
                           {"id": "H0", "statement": f"{par['name']} has no appreciable effect on {out['name']}", "test": f"|S| < {EFFECT_THRESHOLD}"}],
            "evaluation_criterion": criterion,
            "scope_note": ("Hypotheses are tested on the model, not on the real system"
                           + ("" if maturity.maturity_of(contract["id"])["level"] == "validated_on_data" else "; this model is not validated on data") + ".")}
