"""Iterative planning (v8.5): propose the next experiment for an explicit objective, optimise under known
constraints, compare plans and keep the user's decision.

Objectives implemented:
  - "estimate parameters precisely" (Michaelis–Menten on catalogue data): the next substrate concentration
    is the candidate that maximises det(JᵀJ) of the augmented design (D-optimality: smallest joint confidence
    region of Vm and K under the linear approximation). Verified against Duggleby's analytical 2-point design.
  - "reach a target value": find the value of the independent variable for which the model output equals a
    target, inside the contract bounds (bisection on a monotonic output), or report that it is unreachable.
Every proposal states its criterion; the user's choice among alternatives is recorded (SQLite).
"""
from __future__ import annotations

import json
import math
from contextlib import closing
from datetime import datetime, timezone
from typing import Any

import data_catalog
import fitting
import history
import model_registry
import research_question


def _det2(points: list[float], vm: float, k: float) -> float:
    """det(JᵀJ) for v = Vm·x/(K + x): ∂v/∂Vm = x/(K + x), ∂v/∂K = −Vm·x/(K + x)²."""
    a = b = c = 0.0
    for x in points:
        g1, g2 = x / (k + x), -vm * x / (k + x) ** 2
        a += g1 * g1; b += g1 * g2; c += g2 * g2
    return a * c - b * b


def duggleby_two_point_design(k: float, x_max: float) -> list[float]:
    """Analytical D-optimal 2-point design for Michaelis–Menten (Duggleby 1979): x_max and K·x_max/(2K + x_max)."""
    return [k * x_max / (2 * k + x_max), x_max]


def next_measurement(dataset_id: str, x_column: str, y_column: str, where: dict | None = None, candidates: list[float] | None = None,
                     allow_extrapolation: bool = False) -> dict[str, Any]:
    entry = data_catalog.get_entry(dataset_id)
    xs = data_catalog.column_values(entry, x_column, where or {})
    ys = data_catalog.column_values(entry, y_column, where or {})
    fit = fitting.fit({"model": "michaelis_menten", "x": xs, "y": ys})
    vm, k = fit["parameters"]["Vm"]["value"], fit["parameters"]["K"]["value"]
    x_max = max(xs)
    candidates = candidates or sorted({round(x_max * f, 6) for f in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0)})
    base = _det2(xs, vm, k)
    table = [{"x": c, "det_gain": _det2(xs + [c], vm, k) / base, "extrapolation": not min(xs) <= c <= x_max} for c in candidates]
    eligible = [r for r in table if allow_extrapolation or not r["extrapolation"]]
    if not eligible:
        raise ValueError("No candidate inside the measured range; allow extrapolation explicitly to consider the others.")
    best = max(eligible, key=lambda r: r["det_gain"])
    return {"objective": "estimate Vm and K precisely", "criterion": "D-optimality: maximise det(JᵀJ) of the design including the new point (linear approximation)",
            "current_estimates": {"Vm": vm, "K": k}, "current_points": len(xs), "candidates": table, "allow_extrapolation": allow_extrapolation, "proposal": best,
            "theoretical_two_point_design": duggleby_two_point_design(k, x_max),
            "caveat": "The design depends on the current estimates (local optimality); a proposal outside the measured range is an extrapolation of the model."}


def reach_target(question: str, target: float, lower: float | None = None, upper: float | None = None, tolerance: float = 1e-9) -> dict[str, Any]:
    f = research_question.formulate(question)
    if f.get("status") != "formulated":
        return {"status": "not_planned", "reason": f.get("message", "question not formulated"), "formulation": f}
    model_id, x, y = f["model_id"], f["independent_variable"], f["dependent_variable"]
    lo = lower if lower is not None else (x["minimum"] if x["minimum"] is not None else x["reference_value"] / 100)
    hi = upper if upper is not None else (x["maximum"] if x["maximum"] is not None else x["reference_value"] * 100)
    if x["minimum"] is not None and lo <= x["minimum"]:
        lo = x["minimum"] if x["minimum"] > 0 else lo
        lo = lo * (1 + 1e-9) if lo > 0 else lo + 1e-9
    evaluate = lambda v: model_registry.run_model(model_id, {x["name"]: v})["outputs"][y["name"]]["value"]
    f_lo, f_hi = evaluate(lo) - target, evaluate(hi) - target
    runs = 2
    if f_lo * f_hi > 0:
        return {"status": "unreachable", "model_id": model_id, "reason": f"The target {target} {y['unit']} is outside the range [{min(f_lo, f_hi) + target:.6g}, {max(f_lo, f_hi) + target:.6g}] "
                f"obtained for {x['name']} in [{lo:.6g}, {hi:.6g}] {x['unit']}.", "constraints": {"lower": lo, "upper": hi}, "model_runs": runs}
    a, b = lo, hi
    for _ in range(200):
        mid = (a + b) / 2
        f_mid = evaluate(mid) - target
        runs += 1
        if f_lo * f_mid <= 0:
            b = mid
        else:
            a, f_lo = mid, f_mid
        if abs(b - a) <= tolerance * max(abs(mid), 1e-300):
            break
    solution = (a + b) / 2
    return {"status": "found", "model_id": model_id, "objective": f"{y['name']} = {target} {y['unit']}", "criterion": "bisection on the model output (assumes a monotonic output on the interval)",
            "parameter": x["name"], "value": solution, "unit": x["unit"], "achieved": evaluate(solution), "constraints": {"lower": lo, "upper": hi}, "model_runs": runs + 1}


def compare_plans(plans: list[dict[str, Any]], criterion: str) -> list[dict[str, Any]]:
    """Rank alternative plans by a stated numeric criterion (higher is better); ties keep the given order."""
    if not plans or any(criterion not in p for p in plans):
        raise ValueError(f"Every plan must state the criterion '{criterion}'.")
    return sorted(plans, key=lambda p: -p[criterion])


def _connect():
    conn = history._connect()
    conn.execute("""CREATE TABLE IF NOT EXISTS research_decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, at_utc TEXT NOT NULL,
                    objective TEXT NOT NULL, alternatives_json TEXT NOT NULL, chosen TEXT NOT NULL, rationale TEXT NOT NULL)""")
    return conn


def record_decision(objective: str, alternatives: list[Any], chosen: str, rationale: str = "") -> dict[str, Any]:
    if not isinstance(objective, str) or not objective.strip() or not isinstance(chosen, str) or not chosen.strip():
        raise ValueError("objective and chosen are required.")
    if not isinstance(alternatives, list) or not alternatives:
        raise ValueError("alternatives must be a non-empty list.")
    names = [a.get("name") if isinstance(a, dict) else str(a) for a in alternatives]
    if chosen not in names:
        raise ValueError(f"The chosen plan '{chosen}' is not one of the alternatives.")
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_connect()) as conn, conn:
        cur = conn.execute("INSERT INTO research_decisions (at_utc, objective, alternatives_json, chosen, rationale) VALUES (?,?,?,?,?)",
                           (at, objective[:500], json.dumps(alternatives, ensure_ascii=False)[:20000], chosen[:200], str(rationale)[:2000]))
        return {"id": cur.lastrowid, "at_utc": at, "objective": objective, "chosen": chosen}


def decisions() -> list[dict[str, Any]]:
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT * FROM research_decisions ORDER BY id").fetchall()
    return [{"id": r["id"], "at_utc": r["at_utc"], "objective": r["objective"], "alternatives": json.loads(r["alternatives_json"]), "chosen": r["chosen"], "rationale": r["rationale"]}
            for r in rows]
