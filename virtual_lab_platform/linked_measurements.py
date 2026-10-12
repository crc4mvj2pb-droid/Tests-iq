"""Simulated instrument readings of quantities computed by the engines (v4.7).

The reference value is read from a saved, verified experiment dossier instead of being typed
by the user. Units are checked and converted explicitly, the model's own numerical uncertainty
is added to the instrument's uncertainty budget, and the provenance (source dossier, hash,
quantity, engine) is recorded. The result is a simulated measurement, never experimental data.
"""
from __future__ import annotations

import math
from typing import Any

import units
from virtual_instruments import simulate_instrument_measurement

ENGINE_ID = "linked_virtual_instrument"
ENGINE_VERSION = "1.0"

# Illustrative electrical meters (not certified specifications). Accuracy is given as a
# ±(percent of reading + floor) limit and converted to a standard uncertainty by dividing by √3
# (rectangular distribution), as is usual for manufacturer accuracy limits.
METERS: dict[str, dict[str, Any]] = {
    "dmm_dc_voltage": {"name": "Multimètre numérique — tension CC (illustratif)", "measurement_unit": "V",
                       "accuracy_percent_of_reading": 0.5, "accuracy_floor": 0.002, "default_resolution": 0.001},
    "dmm_dc_current": {"name": "Multimètre numérique — courant CC (illustratif)", "measurement_unit": "mA",
                       "accuracy_percent_of_reading": 1.0, "accuracy_floor": 0.02, "default_resolution": 0.01},
}
SPECTRO_ID = "spectrophotometer"

def _factor(source_unit: str, target_unit: str) -> float | None:
    """Conversion factor from the units module (v5.1); None when the dimensions differ."""
    try:
        return units.convert(1.0, source_unit, target_unit)
    except units.UnitError:
        return None


class MeasurementError(ValueError):
    pass


def measurable_quantities(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """Quantities of a dossier that an instrument can read, with unit and model uncertainty."""
    model_id = dossier.get("model_id")
    out: list[dict[str, Any]] = []
    if model_id == "electrical_workbench_dc":
        unc = dossier.get("node_voltage_uncertainty_v") or {}
        for node, value in (dossier.get("node_voltages_v") or {}).items():
            out.append({"key": f"node_voltage:{node}", "label": f"Tension du nœud {node}", "value": value, "unit": "V", "model_uncertainty": unc.get(node, 0.0)})
        for b in dossier.get("branches", []):
            name = b.get("display_name") or b["id"]
            du = unc.get(b["a"], 0.0) + unc.get(b["b"], 0.0)
            out.append({"key": f"branch_voltage:{b['id']}", "label": f"Tension aux bornes de {name}", "value": b["voltage_v"], "unit": "V", "model_uncertainty": du})
            out.append({"key": f"branch_current:{b['id']}", "label": f"Courant dans {name}", "value": b["current_a"], "unit": "A",
                        "model_uncertainty": b.get("current_rounding_uncertainty_a", 0.0)})
        if "source_current_a" in dossier:
            out.append({"key": "source_current", "label": "Courant de la source", "value": dossier["source_current_a"], "unit": "A", "model_uncertainty": 0.0})
    elif model_id == "chemical_kinetics_network":
        summary = dossier.get("summary", {})
        errors = summary.get("estimated_final_error") or {}
        for sid, value in (summary.get("final_concentrations") or {}).items():
            out.append({"key": f"final_concentration:{sid}", "label": f"[{sid}] final", "value": value, "unit": "mol/L", "model_uncertainty": errors.get(sid, 0.0)})
    elif model_id == "chemical_stoichiometry":
        for sid, value in (dossier.get("product_amounts_theoretical_mol") or {}).items():
            out.append({"key": f"product_amount:{sid}", "label": f"Quantité théorique de {sid}", "value": value, "unit": "mol", "model_uncertainty": 0.0})
        for sid, value in (dossier.get("reactant_amounts_remaining_mol") or {}).items():
            out.append({"key": f"remaining_amount:{sid}", "label": f"Quantité restante de {sid}", "value": value, "unit": "mol", "model_uncertainty": 0.0})
    return out


def instruments_for_unit(unit: str) -> list[dict[str, Any]]:
    options = [{"id": k, "name": v["name"], "unit": v["measurement_unit"]} for k, v in METERS.items() if _factor(unit, v["measurement_unit"]) is not None]
    if unit == "mol/L":
        options.append({"id": SPECTRO_ID, "name": "Spectrophotomètre (absorbance via Beer–Lambert)", "unit": "AU", "requires": ["epsilon_l_per_mol_cm", "path_length_cm"]})
    return options


def _positive(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise MeasurementError(f"{name} must be a finite number > 0.")
    return float(value)


def measure(dossier: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Simulate an instrument reading of one quantity of a (verified) dossier."""
    quantities = {q["key"]: q for q in measurable_quantities(dossier)}
    key = request.get("quantity")
    if key not in quantities:
        raise MeasurementError(f"Unknown quantity {key!r} for this dossier. Available: {', '.join(sorted(quantities)) or 'none'}.")
    q = quantities[key]
    instrument_id = request.get("instrument_id")
    seed = request.get("seed", 7)
    calibration = {k: request[k] for k in ("instrument_bias", "calibration_offset", "calibration_gain", "calibration_uncertainty_sd") if k in request}

    if instrument_id in METERS:
        meter = METERS[instrument_id]
        factor = _factor(q["unit"], meter["measurement_unit"])
        if factor is None:
            raise MeasurementError(f"Unit mismatch: {q['unit']} cannot be read by {meter['name']} ({meter['measurement_unit']}).")
        reference = q["value"] * factor
        model_u = q["model_uncertainty"] * factor
        limit = meter["accuracy_percent_of_reading"] / 100 * abs(reference) + meter["accuracy_floor"]
        instrument_sd = limit / math.sqrt(3)
        resolution = request.get("resolution", meter["default_resolution"])
        unit, transform = meter["measurement_unit"], {"type": "unit_conversion", "from": q["unit"], "to": meter["measurement_unit"], "factor": factor}
        reading = simulate_instrument_measurement({"instrument_id": instrument_id, "unit": unit, "true_value": reference, "seed": seed,
                                                  "resolution": resolution, **calibration},
                                                 instrument_override={"name": meter["name"], "measurement_unit": unit, "measurement_uncertainty_sd": instrument_sd},
                                                 reference_standard_uncertainty=model_u)
        reading["instrument"]["accuracy_specification"] = f"±({meter['accuracy_percent_of_reading']} % of reading + {meter['accuracy_floor']} {unit}), rectangular → /√3"
    elif instrument_id == SPECTRO_ID:
        if q["unit"] != "mol/L":
            raise MeasurementError("The spectrophotometer reads a concentration (mol/L) through Beer–Lambert's law.")
        epsilon = _positive(request.get("epsilon_l_per_mol_cm"), "epsilon_l_per_mol_cm")
        path = _positive(request.get("path_length_cm"), "path_length_cm")
        factor = epsilon * path
        reference, model_u = q["value"] * factor, q["model_uncertainty"] * factor
        unit, transform = "AU", {"type": "beer_lambert", "epsilon_l_per_mol_cm": epsilon, "path_length_cm": path, "factor": factor,
                                 "note": "A = ε·l·c; ε and l are user-supplied and their uncertainty is not included."}
        reading = simulate_instrument_measurement({"instrument_id": SPECTRO_ID, "unit": "AU", "true_value": reference, "seed": seed,
                                                  "resolution": request.get("resolution", 0.001), **calibration},
                                                 reference_standard_uncertainty=model_u)
        if reference > 2.0:
            reading.setdefault("warnings", []).append({"code": "absorbance_out_of_linear_range", "params": {"absorbance": reference},
                                                       "message": f"Expected absorbance {reference:.3g} AU exceeds ~2 AU: Beer–Lambert linearity is doubtful; dilute or shorten the path."})
    else:
        raise MeasurementError(f"Instrument {instrument_id!r} cannot read {q['unit']}. Compatible: {', '.join(i['id'] for i in instruments_for_unit(q['unit'])) or 'none'}.")

    reading["linked_quantity"] = {"key": key, "label": q["label"], "model_value": q["value"], "model_unit": q["unit"],
                                  "model_numerical_uncertainty": q["model_uncertainty"], "transform": transform, "reference_value_in_instrument_unit": reference}
    reading["provenance"] = {"source_model_id": dossier.get("model_id"), "source_dossier_hash": dossier.get("dossier_hash"),
                             "source_engine": dossier.get("engine"), "source_title": dossier.get("title")}
    reading["assumptions"] = [a for a in reading["assumptions"] if not a.startswith("The theoretical value is supplied by the user")] + [
        "The reference value is the engine result stored in the source dossier; it is a calculated value, not a measured one.",
        "The model's numerical uncertainty is combined with the instrument components; model-form error is not included.",
    ]
    return reading
