from __future__ import annotations
import math
from typing import Any

def interpolate_linear(rows: list[dict[str, Any]], x: float) -> float:
    """Linear interpolation of rows containing numeric x/y; extrapolation is intentionally forbidden."""
    ordered = sorted(rows, key=lambda r: float(r["x"]))
    if x < float(ordered[0]["x"]) or x > float(ordered[-1]["x"]):
        raise ValueError(f"Reference data does not cover x={x}; extrapolation is not allowed.")
    for row in ordered:
        if math.isclose(float(row["x"]), x, rel_tol=0, abs_tol=1e-12):
            return float(row["y"])
    for left, right in zip(ordered, ordered[1:]):
        x0, x1 = float(left["x"]), float(right["x"])
        if x0 <= x <= x1:
            if math.isclose(x0, x1):
                return float(left["y"])
            fraction = (x - x0) / (x1 - x0)
            return float(left["y"]) + fraction * (float(right["y"]) - float(left["y"]))
    raise ValueError("Could not interpolate reference data.")

def compare_to_reference(predictions: list[dict[str, Any]], reference: list[dict[str, Any]]) -> dict[str, Any]:
    if len(reference) < 2:
        raise ValueError("At least two reference data points are required.")
    cleaned = []
    for i, row in enumerate(reference):
        try:
            x, y = float(row["x"]), float(row["y"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Reference row {i+1} must contain numeric x and y.")
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError(f"Reference row {i+1} contains a non-finite value.")
        cleaned.append({"x": x, "y": y})
    cleaned.sort(key=lambda r: r["x"])
    if any(math.isclose(cleaned[i]["x"], cleaned[i+1]["x"], abs_tol=1e-12) for i in range(len(cleaned)-1)):
        raise ValueError("Reference x values must be unique.")
    paired = []
    for pred in predictions:
        x = float(pred["x"])
        # Only compare predictions within the measured x-range.
        if x < cleaned[0]["x"] or x > cleaned[-1]["x"]:
            continue
        ref_y = interpolate_linear(cleaned, x)
        pred_y = float(pred["y"])
        paired.append({"x": x, "predicted": pred_y, "reference": ref_y, "residual": pred_y-ref_y})
    if len(paired) < 2:
        raise ValueError("At least two simulated points must overlap the reference data range.")
    residuals = [p["residual"] for p in paired]
    mae = sum(abs(v) for v in residuals)/len(residuals)
    rmse = math.sqrt(sum(v*v for v in residuals)/len(residuals))
    bias = sum(residuals)/len(residuals)
    scale = max(abs(p["reference"]) for p in paired)
    normalized_rmse = rmse/scale if scale > 0 else None
    return {
        "status": "comparison_completed_not_validation_proof",
        "number_of_comparison_points": len(paired),
        "metrics": {"mae": mae, "rmse": rmse, "mean_bias": bias, "normalized_rmse_by_max_abs_reference": normalized_rmse},
        "paired_values": paired,
        "interpretation": "These metrics quantify agreement with the supplied reference values only. They do not establish model validity outside this dataset, parameter range, or experimental context.",
        "limitations": [
            "Reference data provenance and measurement uncertainty were not independently verified.",
            "Linear interpolation was used between reference points.",
            "No extrapolation was performed.",
            "Agreement with a dataset is not proof of causal correctness or generalization."
        ]
    }
