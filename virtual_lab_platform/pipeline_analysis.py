"""Interdisciplinary comparison (v7.6): uncertainty propagated through a multi-model chain, and the effect of each hypothesis.

monte_carlo(spec, distributions, outputs, samples, seed)
    draws the uncertain inputs ("step.input.path": distribution), runs the whole chain for every draw and
    reports mean, standard deviation, 2.5–97.5 % interval and failures for each reported output.
    Only parametric uncertainty is propagated: the uncertainty of the model forms themselves is not.
hypothesis_effects(spec, hypotheses, outputs)
    reruns the chain with each alternative assumption (a set of input changes) and reports the change of every
    output relative to the baseline, so the weight of each assumption is visible.
"""
from __future__ import annotations

import copy
import math
import random
import statistics
from typing import Any

import pipelines
from pipelines import PipelineError

MAX_SAMPLES = 5000


def _apply(spec: dict, path: str, value: Any) -> None:
    step_id, _, target = path.partition(".")
    step = next((s for s in spec["steps"] if s.get("id") == step_id), None)
    if step is None or not target:
        raise PipelineError(f"Unknown uncertain input '{path}' (expected step_id.input_path).", "invalid_uncertain_input", path=path)
    step.setdefault("inputs", {})
    pipelines._set_path(step["inputs"], target, value)


def _draw(rng: random.Random, dist: dict[str, Any]) -> float:
    kind = dist.get("distribution")
    if kind == "normal":
        return rng.gauss(float(dist["mean"]), float(dist["sd"]))
    if kind == "uniform":
        return rng.uniform(float(dist["low"]), float(dist["high"]))
    if kind == "lognormal":
        return rng.lognormvariate(float(dist["mu"]), float(dist["sigma"]))
    if kind == "triangular":
        return rng.triangular(float(dist["low"]), float(dist["high"]), float(dist["mode"]))
    raise PipelineError(f"Unknown distribution '{kind}' (normal, uniform, lognormal, triangular).", "invalid_distribution")


def _value(result: dict, ref: str) -> float:
    out = result["final_outputs"].get(ref)
    if out is None:
        raise PipelineError(f"Output '{ref}' is not in the chain's report list.", "unknown_output", output=ref)
    return out["value"]


def monte_carlo(spec: dict, distributions: dict[str, dict], outputs: list[str], samples: int = 1000, seed: int = 1) -> dict[str, Any]:
    if not isinstance(distributions, dict) or not distributions:
        raise PipelineError("Give at least one uncertain input.", "invalid_uncertain_input")
    if not isinstance(samples, int) or not 20 <= samples <= MAX_SAMPLES:
        raise PipelineError(f"samples must be an integer between 20 and {MAX_SAMPLES}.", "invalid_samples")
    base = pipelines.run_pipeline(copy.deepcopy(spec))
    for ref in outputs:
        _value(base, ref)
    rng = random.Random(seed)
    values = {ref: [] for ref in outputs}
    failures: list[dict] = []
    for i in range(samples):
        trial = copy.deepcopy(spec)
        drawn = {path: _draw(rng, dist) for path, dist in sorted(distributions.items())}
        try:
            for path, value in drawn.items():
                _apply(trial, path, value)
            result = pipelines.run_pipeline(trial)
        except PipelineError as exc:
            if exc.code in ("invalid_uncertain_input", "invalid_binding"):
                raise
            failures.append({"sample": i, "code": exc.code, "inputs": drawn})
            continue
        for ref in outputs:
            values[ref].append(_value(result, ref))
    stats = {}
    for ref, vals in values.items():
        vals_sorted = sorted(vals)
        q = lambda p: vals_sorted[min(len(vals_sorted) - 1, max(0, int(round(p * (len(vals_sorted) - 1)))))]
        stats[ref] = {"unit": base["final_outputs"][ref]["unit"], "baseline": _value(base, ref), "mean": statistics.fmean(vals) if vals else None,
                      "sd": statistics.stdev(vals) if len(vals) > 1 else None, "p2_5": q(0.025) if vals else None, "p97_5": q(0.975) if vals else None,
                      "samples": len(vals)}
    return {"analysis": "pipeline_monte_carlo", "seed": seed, "samples_requested": samples, "failures": len(failures), "failure_examples": failures[:5],
            "distributions": distributions, "statistics": stats, "maturity": base["maturity"],
            "scope": "Parametric uncertainty only: the uncertainty of the model forms (assumptions) is not included; see hypothesis effects."}


def hypothesis_effects(spec: dict, hypotheses: list[dict], outputs: list[str]) -> dict[str, Any]:
    if not isinstance(hypotheses, list) or not hypotheses:
        raise PipelineError("Give at least one alternative hypothesis {name, description, changes}.", "invalid_hypothesis")
    base = pipelines.run_pipeline(copy.deepcopy(spec))
    baseline = {ref: _value(base, ref) for ref in outputs}
    rows = []
    for h in hypotheses:
        trial = copy.deepcopy(spec)
        for path, value in (h.get("changes") or {}).items():
            _apply(trial, path, value)
        result = pipelines.run_pipeline(trial)
        effects = {}
        for ref in outputs:
            v = _value(result, ref)
            effects[ref] = {"value": v, "change": v - baseline[ref], "relative_change": (v - baseline[ref]) / baseline[ref] if baseline[ref] else None}
        rows.append({"name": h.get("name"), "description": h.get("description", ""), "changes": h.get("changes", {}), "effects": effects,
                     "warnings": [w["code"] for w in result["warnings"]]})
    largest = {ref: max(rows, key=lambda r: abs(r["effects"][ref]["relative_change"] or 0))["name"] for ref in outputs}
    return {"analysis": "hypothesis_effects", "baseline": baseline, "hypotheses": rows, "largest_effect": largest,
            "note": "Each alternative changes only the listed inputs; effects are not additive in general."}


def joule_uncertainty_example() -> dict[str, Any]:
    """Documented example on the Joule-heating chain: uncertain inputs, outputs and alternative hypotheses."""
    return {"pipeline": "joule_heating_kinetics",
            "distributions": {"circuit.resistors[0].resistance_ohm": {"distribution": "normal", "mean": 48.0, "sd": 0.5},
                              "heating.thermal_resistance_k_per_w": {"distribution": "normal", "mean": 4.0, "sd": 0.4},
                              "arrhenius.activation_energy_j_mol": {"distribution": "normal", "mean": 60000.0, "sd": 1500.0}},
            "outputs": ["heating.temperature_k", "arrhenius.rate_constant", "kinetics.result:summary.final_concentrations.B|{concentration_unit}"],
            "hypotheses": [{"name": "ambient 20 °C", "description": "Ambient temperature 293.15 K instead of 298.15 K", "changes": {"heating.ambient_temperature_k": 293.15}},
                           {"name": "no self-heating", "description": "Heater switched off: the reaction runs at ambient temperature",
                            "changes": {"circuit.source_voltage": 0.0}},
                           {"name": "better insulation", "description": "Thermal resistance doubled (8 K/W)", "changes": {"heating.thermal_resistance_k_per_w": 8.0}}]}
