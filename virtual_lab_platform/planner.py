from __future__ import annotations
import math
from typing import Any
from models import run_enzyme

def plan_enzyme_sweep(params: dict[str, Any], parameter: str, values: list[float]) -> dict[str, Any]:
    if parameter not in ("vmax", "km"):
        raise ValueError("Only vmax and km sweeps are supported in this prototype.")
    if not isinstance(values, list) or len(values) < 2 or len(values) > 100:
        raise ValueError("Provide between 2 and 100 sweep values.")
    base = dict(params)
    sweep_rows = []
    for i, value in enumerate(values):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Sweep value {i+1} must be finite and greater than zero.")
        p = dict(base)
        p[parameter] = float(value)
        out = run_enzyme(p)
        for row in out["rows"]:
            sweep_rows.append({
                "sweep_parameter": parameter,
                "sweep_value": float(value),
                "x": row["x"],
                "y": row["y"]
            })
    return {
        "status": "sweep_completed",
        "swept_parameter": parameter,
        "sweep_values": values,
        "rows": sweep_rows,
        "interpretation": "This is a deterministic model-based parameter sweep. It explores the selected model; it does not establish which physical experiment is worth running without empirical uncertainty, cost, feasibility and decision criteria.",
        "limitations": [
            "Only the Michaelis–Menten demonstration model is supported.",
            "Parameter values are not fitted or independently verified.",
            "No experimental cost, measurement noise or value-of-information calculation is included."
        ]
    }
