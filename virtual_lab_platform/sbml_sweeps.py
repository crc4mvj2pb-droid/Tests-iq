"""Bounded one-parameter sweeps for supported imported SBML models."""
from __future__ import annotations
import math
from typing import Any
from sbml_engine import simulate_sbml, SBMLSimulationError

def sweep_sbml(asset_id: Any, duration: Any, dt: Any, parameter_id: Any, values: Any) -> dict:
    if not isinstance(parameter_id, str) or not parameter_id.strip():
        raise SBMLSimulationError("Provide a global parameter ID to sweep.")
    parameter_id = parameter_id.strip()
    if not isinstance(values, list) or not 2 <= len(values) <= 25:
        raise SBMLSimulationError("Provide between 2 and 25 parameter values.")
    parsed = []
    for i, value in enumerate(values):
        if isinstance(value, bool):
            raise SBMLSimulationError(f"Sweep value {i+1} must be numeric.")
        try:
            n = float(value)
        except (TypeError, ValueError):
            raise SBMLSimulationError(f"Sweep value {i+1} must be numeric.") from None
        if not math.isfinite(n):
            raise SBMLSimulationError(f"Sweep value {i+1} must be finite.")
        parsed.append(n)
    if len(set(parsed)) != len(parsed):
        raise SBMLSimulationError("Sweep values must be unique.")
    runs = []
    for value in parsed:
        out = simulate_sbml(asset_id, duration, dt, "rk4", {parameter_id: value})
        runs.append({
            "parameter_value": value,
            "final_amounts": out["summary"]["final_amounts"],
            "final_reaction_rates": out["summary"]["final_reaction_rates"],
            "steps": out["steps"],
            "checks": out["checks"],
        })
    return {
        "asset_id": asset_id,
        "parameter_id": parameter_id,
        "duration": float(duration),
        "dt": float(dt),
        "runs": runs,
        "comparison": {
            "run_count": len(runs),
            "species": sorted(runs[0]["final_amounts"]),
            "rows": [{"parameter_value": r["parameter_value"], **r["final_amounts"]} for r in runs],
        },
        "validation_status": "exploratory_parameter_sweep_not_empirically_validated",
        "warnings": [
            "Only a single global numeric parameter is varied; all other parameters and initial conditions remain fixed.",
            "The model must be supported by this SBML subset and its units/time scale must be checked.",
            "A parameter sweep is exploratory and does not establish real-world validity.",
        ],
    }
