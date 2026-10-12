"""Illustrative virtual-instrument measurements with explicit uncertainty.

This module creates simulated readings, never experimental observations. Instrument
catalogue uncertainties are educational estimates rather than certified specifications.
"""
from __future__ import annotations
import math
import random
from typing import Any
from lab_designer import EQUIPMENT


def _finite_number(value: Any, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be at least {minimum:g}.")
    return result


def simulate_instrument_measurement(request: dict[str, Any]) -> dict[str, Any]:
    """Generate a seeded instrument reading, calibration correction and uncertainty budget."""
    instrument_id = request.get("instrument_id")
    if not isinstance(instrument_id, str) or instrument_id not in EQUIPMENT:
        raise ValueError("Unknown instrument_id. Choose an instrument from the equipment catalogue.")
    instrument = EQUIPMENT[instrument_id]
    if "measurement_uncertainty_sd" not in instrument or "measurement_unit" not in instrument:
        raise ValueError("The selected catalogue item has no supported measurement uncertainty model.")

    unit = instrument["measurement_unit"]
    supplied_unit = request.get("unit", unit)
    if supplied_unit != unit:
        raise ValueError(f"Unit mismatch for {instrument['name']}: expected '{unit}'.")
    true_value = _finite_number(request.get("true_value"), "true_value")
    instrument_bias = _finite_number(request.get("instrument_bias", 0.0), "instrument_bias")
    calibration_offset = _finite_number(request.get("calibration_offset", 0.0), "calibration_offset")
    calibration_gain = _finite_number(request.get("calibration_gain", 1.0), "calibration_gain", minimum=1e-12)
    calibration_sd = _finite_number(request.get("calibration_uncertainty_sd", 0.0), "calibration_uncertainty_sd", minimum=0.0)
    resolution = _finite_number(request.get("resolution", 0.0), "resolution", minimum=0.0)
    seed = request.get("seed", 7)
    if isinstance(seed, bool) or not isinstance(seed, int) or not -(2**63) <= seed < 2**63:
        raise ValueError("seed must be an integer in the signed 64-bit range.")

    instrument_sd = float(instrument["measurement_uncertainty_sd"])
    rng = random.Random(seed)
    noise = rng.gauss(0.0, instrument_sd)
    raw_reading = true_value + instrument_bias + noise
    corrected_reading = (raw_reading - calibration_offset) * calibration_gain
    if resolution > 0:
        indicated_reading = round(round(corrected_reading / resolution) * resolution, 12)
    else:
        indicated_reading = corrected_reading

    # Independent standard uncertainties; resolution is modelled as a rectangular
    # quantisation interval of width resolution (standard uncertainty r/sqrt(12)).
    instrument_component = abs(calibration_gain) * instrument_sd
    calibration_component = abs(calibration_gain) * calibration_sd
    resolution_component = resolution / math.sqrt(12.0)
    standard_uncertainty = math.sqrt(
        instrument_component**2 + calibration_component**2 + resolution_component**2
    )
    expanded_uncertainty = 2.0 * standard_uncertainty
    difference = indicated_reading - true_value
    z_score = difference / standard_uncertainty if standard_uncertainty > 0 else (0.0 if difference == 0 else None)

    return {
        "status": "simulated_measurement",
        "experimental_data": False,
        "instrument": {"id": instrument_id, "name": instrument["name"], "unit": unit},
        "theoretical_value": true_value,
        "raw_simulated_reading": raw_reading,
        "calibrated_reading_before_rounding": corrected_reading,
        "indicated_reading": indicated_reading,
        "unit": unit,
        "calibration": {
            "offset_correction": calibration_offset,
            "gain_correction": calibration_gain,
            "calibration_standard_uncertainty": calibration_sd,
            "injected_instrument_bias": instrument_bias,
        },
        "uncertainty_budget": {
            "instrument_standard_uncertainty": instrument_component,
            "calibration_standard_uncertainty": calibration_component,
            "resolution_standard_uncertainty": resolution_component,
            "combined_standard_uncertainty": standard_uncertainty,
            "expanded_uncertainty_k2": expanded_uncertainty,
            "coverage_factor": 2.0,
            "approximate_interval_k2": [indicated_reading - expanded_uncertainty, indicated_reading + expanded_uncertainty],
            "method": "root-sum-square of independent standard uncertainty components; resolution treated as rectangular",
        },
        "comparison": {
            "measurement_minus_theory": difference,
            "absolute_error": abs(difference),
            "normalized_difference_z": z_score,
            "within_expanded_uncertainty": abs(difference) <= expanded_uncertainty,
        },
        "seed": seed,
        "assumptions": [
            "This is a simulated reading generated from a seeded Gaussian noise model, not an experimental observation.",
            "Catalogue instrument uncertainty is illustrative and is not a certified manufacturer specification.",
            "Instrument noise, injected bias, calibration correction and resolution are simplified; drift, hysteresis, response time and environmental effects are not modelled.",
            "The expanded uncertainty uses k=2 as an approximate coverage interval; coverage is not guaranteed for every distribution or small sample.",
            "The theoretical value is supplied by the user; this endpoint does not independently validate the scientific model that produced it.",
        ],
    }
