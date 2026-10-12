"""Protocol design from a formulated research question (v8.2).

From a formulation (research_question.formulate) the planner proposes:
  - the sweep of the independent variable (values inside the contract bounds, spacing stated);
  - controls: a reference run at the reference value and a duplicate of it (determinism control);
  - replicates: one per point for deterministic engines (justified), several when a simulated
    instrument adds noise;
  - virtual equipment: simulated instruments of the catalogue whose unit matches the observed output;
  - a check of every planned run against the model contract before anything is executed;
  - what is NOT simulated (measurement, sample preparation, conditions outside the model's assumptions).
"""
from __future__ import annotations

import math
from typing import Any

import model_registry
import units
from contracts import ContractError, validate_inputs
from lab_designer import EQUIPMENT

DEFAULT_POINTS = 7


def _grid(ref: float, lo: float | None, hi: float | None, exclusive_lo: bool, points: int) -> tuple[list[float], str]:
    if ref > 0:
        a, b = ref / 2, ref * 2
        if lo is not None:
            a = max(a, lo * (1.0001 if exclusive_lo and lo > 0 else 1) if lo > 0 else a)
        if hi is not None:
            b = min(b, hi)
        values = [a * (b / a) ** (i / (points - 1)) for i in range(points)]
        return values, "logarithmic from ref/2 to 2·ref (clipped to the contract bounds)"
    span = max(abs(ref), 1.0)
    a, b = ref - span, ref + span
    if lo is not None:
        a = max(a, lo)
    if hi is not None:
        b = min(b, hi)
    return [a + (b - a) * i / (points - 1) for i in range(points)], "linear around the reference value (clipped to the contract bounds)"


def design(formulation: dict[str, Any], points: int = DEFAULT_POINTS, instrument_id: str | None = None, replicates: int | None = None) -> dict[str, Any]:
    if formulation.get("status") != "formulated":
        return {"status": "not_designed", "reason": "The research question is not formulated yet (clarification needed or unknown).", "formulation": formulation}
    if not isinstance(points, int) or not 3 <= points <= 51:
        return {"status": "not_designed", "reason": "points must be an integer between 3 and 51."}
    model_id = formulation["model_id"]
    contract = model_registry.get_contract(model_id)
    x = formulation["independent_variable"]
    spec = next(p for p in contract["parameters"] if p["name"] == x["name"])
    values, spacing = _grid(float(x["reference_value"]), spec.get("minimum"), spec.get("maximum"), spec.get("exclusive_minimum", False), points)
    if spec["type"] == "integer":
        values = sorted({int(round(v)) for v in values})
    runs, refused = [], []
    for i, v in enumerate(values):
        inputs = {x["name"]: v}
        try:
            validate_inputs(contract, inputs, converter=units.contract_converter)
            runs.append({"run": f"sweep_{i + 1}", "role": "sweep", "inputs": inputs})
        except ContractError as exc:
            refused.append({"value": v, "reason": str(exc), "code": exc.code})
    runs.insert(0, {"run": "reference", "role": "control: reference value", "inputs": {x["name"]: x["reference_value"]}})
    runs.insert(1, {"run": "reference_duplicate", "role": "control: determinism (must equal the reference run exactly)", "inputs": {x["name"]: x["reference_value"]}})
    y_unit = formulation["dependent_variable"]["unit"]
    equipment = []
    for eq_id, eq in EQUIPMENT.items():
        unit = eq.get("measurement_unit")
        if unit and y_unit not in ("1", "a.u.") and eq.get("measurement_uncertainty_sd") is not None:
            try:
                if units.compatible(unit, y_unit):
                    equipment.append({"id": eq_id, "name": eq.get("name", eq_id), "unit": unit, "uncertainty_sd": eq["measurement_uncertainty_sd"]})
            except units.UnitError:
                continue
    noisy = instrument_id is not None
    if noisy and instrument_id not in {e["id"] for e in equipment}:
        return {"status": "not_designed", "reason": f"Instrument '{instrument_id}' does not measure {formulation['dependent_variable']['name']} ({y_unit}).",
                "compatible_instruments": [e["id"] for e in equipment]}
    n_rep = replicates if replicates is not None else (5 if noisy else 1)
    return {"status": "designed", "model_id": model_id, "formulation": formulation,
            "sweep": {"parameter": x["name"], "unit": x["unit"], "values": values, "spacing": spacing, "refused_values": refused},
            "runs": runs, "replicates_per_point": n_rep,
            "replicate_justification": ("deterministic engine without instrument noise: repeated runs give identical values (checked by the duplicate control)"
                                        if not noisy else f"simulated instrument {instrument_id} adds seeded noise: {n_rep} readings per point"),
            "virtual_equipment": equipment, "instrument_id": instrument_id,
            "analysis_plan": [f"compute normalised sensitivity of {formulation['dependent_variable']['name']} at the reference value",
                              "check monotonicity over the sweep", "evaluate H1/H2/H0 with the stated criterion"],
            "not_simulated": ["Real measurement errors other than the simulated instrument (if any)", "Sample preparation, equipment set-up and operator effects",
                              "Conditions outside the model assumptions: " + "; ".join(contract.get("assumptions", []))],
            "contract_check": {"planned_runs": len(runs), "refused_values": len(refused), "all_planned_runs_valid": True}}
