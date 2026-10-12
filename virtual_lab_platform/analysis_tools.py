from __future__ import annotations
import math
import random
from typing import Any
from models import run_enzyme

def enzyme_uncertainty(parameters: dict[str, Any], uncertainty: dict[str, float], samples: int = 500, seed: int = 7) -> dict[str, Any]:
    """Exploratory Monte Carlo propagation for independent normal parameter uncertainty."""
    if not isinstance(samples, int) or isinstance(samples, bool) or samples < 100 or samples > 10000:
        raise ValueError("samples must be an integer between 100 and 10000.")
    if not uncertainty or any(k not in ("vmax", "km") for k in uncertainty):
        raise ValueError("Uncertainty is supported for vmax and km only.")
    for key, sd in uncertainty.items():
        if not isinstance(sd, (int, float)) or isinstance(sd, bool) or not math.isfinite(sd) or sd < 0:
            raise ValueError(f"Standard deviation for {key} must be finite and non-negative.")
    rng = random.Random(seed)
    base = dict(parameters)
    # Keep same substrate grid for every draw; parameter uncertainty is sampled independently.
    first = run_enzyme(base)
    xs = [row["x"] for row in first["rows"]]
    ys_by_x = [[] for _ in xs]
    accepted = 0
    rejected = 0
    for _ in range(samples):
        draw = dict(base)
        for key, sd in uncertainty.items():
            draw[key] = rng.gauss(float(base[key]), float(sd))
        if draw["vmax"] <= 0 or draw["km"] <= 0:
            rejected += 1
            continue
        result = run_enzyme(draw)
        accepted += 1
        for i, row in enumerate(result["rows"]):
            ys_by_x[i].append(float(row["y"]))
    if accepted < max(50, int(samples * 0.5)):
        raise ValueError("Too many invalid parameter draws. Reduce uncertainty or change nominal parameters.")
    rows = []
    for x, ys in zip(xs, ys_by_x):
        ordered = sorted(ys)
        n = len(ordered)
        rows.append({
            "x": x,
            "mean": sum(ordered)/n,
            "p05": ordered[max(0, math.ceil(0.05*n)-1)],
            "median": ordered[max(0, math.ceil(0.50*n)-1)],
            "p95": ordered[max(0, math.ceil(0.95*n)-1)],
            "accepted_samples": n
        })
    return {
        "status": "exploratory_uncertainty_analysis",
        "method": "Monte Carlo with independent normal parameter draws",
        "seed": seed,
        "requested_samples": samples,
        "accepted_samples": accepted,
        "rejected_samples": rejected,
        "parameter_standard_deviations": uncertainty,
        "rows": rows,
        "limitations": [
            "This analysis is only as meaningful as the supplied parameter uncertainty.",
            "Normal distributions are assumed and parameter correlations are ignored.",
            "This is not empirical validation and does not include measurement or structural model error.",
            "Only the illustrative enzyme model is supported."
        ]
    }

def enzyme_local_sensitivity(parameters: dict[str, Any], relative_step: float = 0.01) -> dict[str, Any]:
    if not isinstance(relative_step, (int, float)) or not math.isfinite(relative_step) or relative_step <= 0 or relative_step > 0.2:
        raise ValueError("relative_step must be greater than 0 and at most 0.2.")
    base = run_enzyme(parameters)
    outputs = []
    for key in ("vmax", "km"):
        low = dict(parameters); high = dict(parameters)
        low[key] = float(parameters[key]) * (1-relative_step)
        high[key] = float(parameters[key]) * (1+relative_step)
        y_low = run_enzyme(low)["rows"]
        y_high = run_enzyme(high)["rows"]
        for i, row in enumerate(base["rows"]):
            denom = float(y_high[i]["x"])
            slope = (float(y_high[i]["y"])-float(y_low[i]["y"]))/(high[key]-low[key])
            elasticity = slope * float(parameters[key]) / float(row["y"]) if float(row["y"]) != 0 else None
            outputs.append({"parameter": key, "x": row["x"], "local_derivative": slope, "elasticity": elasticity})
    return {
        "status": "local_sensitivity_analysis",
        "relative_step": relative_step,
        "rows": outputs,
        "interpretation": "Finite-difference local sensitivity around the selected parameter values; not a global ranking of scientific importance.",
        "limitations": ["Only the illustrative enzyme model is supported.", "Results depend on local parameter values and finite-difference step."]
    }
