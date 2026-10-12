"""Critical analysis of an executed research plan (v8.4).

Three kinds of statements are kept apart and labelled:
  computed_results      numbers produced by the engines (with the task-graph node they come from);
  model_interpretation  rule-based reading of those numbers against the hypotheses (H1, H2, H0, inconclusive);
  generated_explanation template sentences written by rules (not a language model), to be checked by the researcher.
It also lists what is missing to draw a conclusion about the real system (data, validation, uncertainty).
"""
from __future__ import annotations

import math
from typing import Any

import analysis
import maturity
import research_question
import task_graph


def evaluate_hypotheses(sensitivity: float | None, monotonicity: str, threshold: float = research_question.EFFECT_THRESHOLD) -> dict[str, Any]:
    if sensitivity is None or not math.isfinite(sensitivity):
        return {"supported": None, "verdict": "inconclusive", "reason": "the sensitivity could not be computed"}
    if abs(sensitivity) < threshold and monotonicity in ("constant", "increasing", "decreasing"):
        return {"supported": "H0", "verdict": "H0 supported in the model", "reason": f"|S| = {abs(sensitivity):.3g} < {threshold}"}
    if sensitivity >= threshold and monotonicity == "increasing":
        return {"supported": "H1", "verdict": "H1 supported in the model", "reason": f"S = {sensitivity:.3g} ≥ {threshold} and the output increases over the whole sweep"}
    if sensitivity <= -threshold and monotonicity == "decreasing":
        return {"supported": "H2", "verdict": "H2 supported in the model", "reason": f"S = {sensitivity:.3g} ≤ −{threshold} and the output decreases over the whole sweep"}
    return {"supported": None, "verdict": "inconclusive", "reason": f"local sensitivity S = {sensitivity:.3g} and global behaviour '{monotonicity}' do not agree with a single hypothesis"}


def analyze(plan: dict[str, Any], parameter_relative_sd: float | None = None, samples: int = 300, seed: int = 1) -> dict[str, Any]:
    if plan.get("status") != "completed":
        return {"status": "not_analyzed", "reason": f"The plan did not complete (status {plan.get('status')}); no analysis is made on partial results."}
    f = plan["formulation"]
    x, y = f["independent_variable"], f["dependent_variable"]
    res = plan["results"]
    s = res["sensitivity"].get("normalised_coefficient")
    mono = res["analysis"]["monotonicity"]
    computed = [
        {"quantity": f"normalised sensitivity of {y['name']} to {x['name']}", "value": s, "unit": "1", "source_node": "sensitivity",
         "numerical_check": "converged" if res["sensitivity"].get("converged") else "not converged (Richardson estimate unreliable)"},
        {"quantity": f"{y['name']} over the sweep", "value": [res["analysis"]["y_min"], res["analysis"]["y_max"]], "unit": y["unit"], "source_node": "analysis"},
        {"quantity": "behaviour over the sweep", "value": mono, "unit": None, "source_node": "analysis"},
        {"quantity": f"{y['name']} at the reference value", "value": res["reference"][y["name"]]["value"], "unit": y["unit"], "source_node": "reference"}]
    verdict = evaluate_hypotheses(s, mono)
    uncertainty = {"numerical": computed[0]["numerical_check"]}
    if parameter_relative_sd:
        ref = x["reference_value"]
        mc = analysis.monte_carlo(plan["model_id"], {}, {x["name"]: {"distribution": "normal", "mean": ref, "sd": abs(ref) * parameter_relative_sd}}, [y["name"]], samples=samples, seed=seed)
        st = mc["statistics"][y["name"]]
        uncertainty["parametric"] = {"input": f"{x['name']} ~ normal(mean {ref}, relative sd {parameter_relative_sd})", "mean": st["mean"], "sd": st["sd"],
                                     "interval_95": [st["q025"], st["q975"]], "samples": mc["samples_accepted"], "seed": seed}
    else:
        uncertainty["parametric"] = "not evaluated: no input uncertainty was given"
    level = maturity.maturity_of(plan["model_id"])["level"]
    missing = []
    if level != "validated_on_data":
        missing.append("The model is not validated on measured data: the result describes the model, not the real system.")
    illustrative = [c["name"] for c in f["controlled_variables"] if c.get("provenance") == "illustrative"]
    if illustrative:
        missing.append(f"Controlled variables at illustrative default values ({', '.join(illustrative[:6])}{'…' if len(illustrative) > 6 else ''}): conclusions may change with sourced values.")
    if not parameter_relative_sd:
        missing.append("No input uncertainty given: the robustness of the conclusion to parameter uncertainty is unknown.")
    interpretation = [f"{verdict['verdict']} ({verdict['reason']})."]
    if verdict["supported"] is None:
        interpretation.append("No hypothesis can be retained from these runs.")
    explanation = ("[Texte généré par règles, à vérifier] "
                   + {"H1": f"Dans ce modèle, augmenter {x['name']} augmente {y['name']} sur toute la plage étudiée.",
                      "H2": f"Dans ce modèle, augmenter {x['name']} diminue {y['name']} sur toute la plage étudiée.",
                      "H0": f"Dans ce modèle, {x['name']} n'a pas d'effet notable sur {y['name']} au voisinage de la valeur de référence.",
                      None: "Les essais ne permettent pas de trancher entre les hypothèses."}[verdict["supported"]])
    return {"status": "analyzed", "question": f["question"], "model_id": plan["model_id"], "model_maturity": level,
            "computed_results": computed, "hypothesis_evaluation": verdict, "uncertainty": uncertainty,
            "model_interpretation": interpretation, "generated_explanation": explanation, "missing_for_conclusion": missing,
            "conclusion_scope": "model only" if level != "validated_on_data" else "model validated on one dataset; conclusions limited to its conditions"}


def analyze_question(question: str, parameter_relative_sd: float | None = None, time_limit_s: float = 60.0) -> dict[str, Any]:
    plan = task_graph.run_question(question, time_limit_s=time_limit_s)
    if plan.get("status") == "not_executed":
        return {"status": "not_analyzed", "reason": plan.get("protocol", {}).get("reason") or "The question could not be formulated.", "formulation": plan.get("formulation")}
    result = analyze(plan, parameter_relative_sd)
    result["plan_nodes"] = [{k: n.get(k) for k in ("name", "status", "duration_ms")} for n in plan["nodes"]]
    return result
