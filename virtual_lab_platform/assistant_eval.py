"""Evaluation of the rule-based assistant (v8.6).

The evaluation set (evaluation/assistant_eval_set.json) was written before the first run. For each case
the expected outcome is a status (answered, clarification_needed, tool_failed, out_of_scope, unknown),
the tool that must be called, and — for numeric questions — a value computed here from a closed form,
independently of the assistant. Measured:
  - accuracy per category and overall;
  - hallucination rate: answers containing a number that appears in no tool output (untraced_numbers);
  - traceability: every reported value names an existing tool call;
  - abstention correctness: on out-of-scope and unknown questions, no value and no model run;
  - tool-call correctness: the expected tool was called.
No claim of general scientific autonomy is made from these numbers.
"""
from __future__ import annotations

import cmath
import json
import math
from pathlib import Path
from typing import Any

import assistant
import critical_analysis
import research_question

SET_PATH = Path(__file__).resolve().parent / "evaluation" / "assistant_eval_set.json"
R_GAS = 6.02214076e23 * 1.380649e-23


def _weak_acid_ph(c: float, pka: float, kw: float = 1e-14) -> float:
    ka, h = 10 ** -pka, math.sqrt(10 ** -pka * c)
    for _ in range(100):
        h -= (h ** 3 + ka * h ** 2 - (kw + ka * c) * h - ka * kw) / (3 * h ** 2 + 2 * ka * h - (kw + ka * c))
    return -math.log10(h)


FORMULAS = {
    "rc_tau": lambda r, c: r * c,
    "arrhenius_default": lambda t: 1.0 * math.exp(-40000.0 / (R_GAS * t)),  # contract defaults: A = 1 s⁻¹, Ea = 40 kJ/mol
    "rlc_current": lambda v, r, l, c, f: v / abs(complex(r, 2 * math.pi * f * l - 1 / (2 * math.pi * f * c))),
    "heating_default": lambda p: 298.15 + p * 4.0,  # contract defaults: T_amb = 298.15 K, R_th = 4 K/W
    "weak_acid_ph": _weak_acid_ph,
}


def load_set() -> dict[str, Any]:
    return json.loads(SET_PATH.read_text(encoding="utf-8"))


def _value(result: dict, name: str):
    return next((v for s in result["statements"] for v in s.get("values", []) if v.get("name") == name), None)


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    exp = case["expect"]
    row = {"id": case["id"], "category": case["category"], "question": case["question"]}
    if "formulation" in exp:
        f = research_question.formulate(case["question"])
        want = exp["formulation"]
        ok = f["status"] == want["status"] and all(
            [f.get("model_id") == want.get("model_id") if "model_id" in want else True,
             (f.get("independent_variable") or {}).get("name") == want.get("x") if "x" in want else True,
             (f.get("dependent_variable") or {}).get("name") == want.get("y") if "y" in want else True])
        return {**row, "passed": ok, "observed": {"status": f["status"], "model_id": f.get("model_id")}, "hallucination": False, "traceable": True}
    if "hypothesis" in exp:
        a = critical_analysis.analyze_question(case["question"])
        got = (a.get("hypothesis_evaluation") or {}).get("supported")
        return {**row, "passed": got == exp["hypothesis"], "observed": {"status": a["status"], "hypothesis": got}, "hallucination": False, "traceable": True}
    r = assistant.answer(case["question"])
    reasons = []
    if r["status"] != exp["status"]:
        reasons.append(f"status {r['status']} ≠ {exp['status']}")
    tools = [c["tool"] for c in r["tool_calls"]]
    if exp.get("tool") and exp["tool"] not in tools:
        reasons.append(f"tool {exp['tool']} not called ({tools})")
    if "value" in exp and not reasons:
        spec = exp["value"]
        reference = FORMULAS[spec["formula"]](*spec["args"])
        got = _value(r, spec["name"])
        if got is None:
            reasons.append(f"no value {spec['name']}")
        else:
            err = abs(got["value"] - reference)
            tol = spec.get("abs_tol", 0.0) or spec.get("rel_tol", 0.0) * abs(reference)
            if err > tol:
                reasons.append(f"{spec['name']} = {got['value']!r}, expected {reference!r} (error {err:.3g} > {tol:.3g})")
    if exp.get("contains") and exp["contains"] not in r["text"]:
        reasons.append(f"text lacks '{exp['contains']}'")
    abstain = exp["status"] in ("out_of_scope", "unknown", "clarification_needed", "tool_failed")
    gave_value = any(s.get("values") for s in r["statements"] if s["kind"] == "tool_result" and s.get("values") and
                     any(v.get("name") for v in s["values"]))
    if abstain and exp["status"] in ("out_of_scope", "unknown") and (gave_value or any(c["tool"] == "run_model" for c in r["tool_calls"])):
        reasons.append("a value or a model run was produced for a question that must not be answered")
    call_ids = {c["id"] for c in r["tool_calls"]}
    traceable = all(v.get("source") in call_ids for s in r["statements"] for v in s.get("values", []))
    untraced = assistant.untraced_numbers(r)
    return {**row, "passed": not reasons, "reasons": reasons, "observed": {"status": r["status"], "tools": tools},
            "hallucination": bool(untraced), "untraced_numbers": untraced, "traceable": traceable}


def run() -> dict[str, Any]:
    data = load_set()
    rows = [evaluate_case(c) for c in data["cases"]]
    categories = sorted({r["category"] for r in rows})
    per_cat = {c: {"cases": sum(r["category"] == c for r in rows), "passed": sum(r["passed"] for r in rows if r["category"] == c)} for c in categories}
    abstention = [r for r in rows if r["category"] in ("out_of_scope", "unknown")]
    return {"set_version": data["version"], "cases": len(rows), "passed": sum(r["passed"] for r in rows), "accuracy": sum(r["passed"] for r in rows) / len(rows),
            "per_category": per_cat, "hallucination_rate": sum(r["hallucination"] for r in rows) / len(rows),
            "traceability_rate": sum(r["traceable"] for r in rows) / len(rows),
            "abstention_correct": sum(r["passed"] for r in abstention) / len(abstention) if abstention else None,
            "failures": [r for r in rows if not r["passed"]], "rows": rows,
            "statement": "These rates measure this rule-based assistant on this fixed set only; they do not support any claim of general scientific autonomy."}
