"""Validation of models on sourced data (v7.3), with protocols and acceptance criteria fixed in advance.

A protocol states — before any result is looked at — the dataset, the subset, how the data are split
between fitting and validation, the statistic and the acceptance threshold. `run(protocol_id)` executes
it and returns the verdict with every number. A protocol may also define negative controls: data the
model is NOT expected to describe; the criterion must reject them, which shows that it discriminates.
A passing protocol is the evidence required for the maturity level "validated_on_data".
"""
from __future__ import annotations

import math
from typing import Any

import data_catalog
import fitting

PROTOCOLS: dict[str, dict[str, Any]] = {
    "michaelis_menten_puromycin_treated": {
        "model_id": "enzyme_kinetics", "fit_model": "michaelis_menten", "fixed_in_version": "7.3",
        "question": "Does the Michaelis–Menten form describe the initial velocity of the Puromycin-treated enzyme within measurement noise?",
        "dataset_id": "puromycin_treloar_1974", "x_column": "conc", "y_column": "rate", "where": {"state": "treated"},
        "split": "Fit on the first measurement at each concentration (6 points); validate on the second replicate (6 points).",
        "statistic": "validation RMSE / s_rep, where s_rep is the pooled replicate standard deviation of the duplicates (s_rep² = Σ d_i² / 2n)",
        "threshold": 2.0,
        "criterion": "validated if validation RMSE ≤ 2 × s_rep (prediction error comparable to the replicate noise)",
        "negative_controls": [{"name": "untreated cells", "where": {"state": "untreated"},
                               "expectation": "rejected: the treated-cell parameters must not describe untreated cells"}],
    },
}


def _replicate_sd(xs: list[float], ys: list[float]) -> float:
    groups: dict[float, list[float]] = {}
    for x, y in zip(xs, ys):
        groups.setdefault(x, []).append(y)
    pairs = [g for g in groups.values() if len(g) == 2]
    if not pairs:
        raise ValueError("No duplicate measurements: the replicate noise cannot be estimated.")
    return math.sqrt(sum((a - b) ** 2 for a, b in pairs) / (2 * len(pairs)))


def run(protocol_id: str) -> dict[str, Any]:
    if protocol_id not in PROTOCOLS:
        raise KeyError(protocol_id)
    p = PROTOCOLS[protocol_id]
    entry = data_catalog.get_entry(p["dataset_id"])
    xs = data_catalog.column_values(entry, p["x_column"], p["where"])
    ys = data_catalog.column_values(entry, p["y_column"], p["where"])
    s_rep = _replicate_sd(xs, ys)
    fit = fitting.fit({"model": p["fit_model"], "x": xs, "y": ys, "validation": {"method": "alternate"}})
    ratio = fit["validation"]["rmse"] / s_rep
    controls = []
    for control in p.get("negative_controls", []):
        cx = data_catalog.column_values(entry, p["x_column"], control["where"])
        cy = data_catalog.column_values(entry, p["y_column"], control["where"])
        pred = fitting.predict(fit, cx)
        rmse = math.sqrt(sum((q["y"] - y) ** 2 for q, y in zip(pred, cy)) / len(cy))
        controls.append({"name": control["name"], "points": len(cy), "rmse": rmse, "ratio": rmse / s_rep, "rejected": rmse / s_rep > p["threshold"],
                         "expectation": control["expectation"], "extrapolated_points": sum(q["extrapolation"] for q in pred)})
    validated = ratio <= p["threshold"] and all(c["rejected"] for c in controls)
    return {"protocol_id": protocol_id, **{k: p[k] for k in ("model_id", "question", "split", "statistic", "criterion", "threshold", "fixed_in_version")},
            "dataset": {"id": entry["id"], "version": entry["version"], "content_sha256": entry["content_sha256"], "data_kind": entry["data_kind"],
                        "source_ids": entry["source_ids"], "subset": p["where"]},
            "replicate_sd": s_rep, "fit_parameters": {k: {"value": v["value"], "standard_error": v["standard_error"], "unit": v["unit"]} for k, v in fit["parameters"].items()},
            "validation_points": fit["validation"]["points"], "validation_rmse": fit["validation"]["rmse"], "ratio": ratio,
            "negative_controls": controls, "verdict": "validated" if validated else "not_validated",
            "scope": "Valid for this dataset and its conditions only; not a general property of the enzyme or of other systems."}


def all_results() -> list[dict[str, Any]]:
    return [run(pid) for pid in PROTOCOLS]
