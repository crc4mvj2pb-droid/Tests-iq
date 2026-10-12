"""Parameter sweeps, local sensitivity and Monte Carlo uncertainty for any registered model (v5.5).

Every evaluation goes through model_registry.run_model, so inputs are contract-validated and
outputs carry their units. Long analyses accept a `control` object (see jobs.py) that reports
progress and is checked between evaluations: cancellation is real at the granularity of one
model run (a run already started finishes, nothing after it starts).

Interpretation: a sweep, a sensitivity coefficient or a correlation describes the behaviour of
the model as written. It is not evidence of a causal mechanism in the real system.
"""
from __future__ import annotations

import csv
import io
import math
import random
from typing import Any

import model_registry
from contracts import ContractError

INTERPRETATION = ("These results describe the model as written, under its assumptions and parameter ranges. "
                  "A sweep, a sensitivity coefficient, a correlation or a good fit is not evidence of a causal mechanism in the real system.")
MAX_EVALUATIONS = 5000


class AnalysisError(ValueError):
    def __init__(self, message: str, code: str = "invalid_analysis", **params):
        super().__init__(message)
        self.code = code
        self.params = params


class Cancelled(Exception):
    pass


class _NoControl:
    def check(self, done: int, total: int) -> None:
        return None


def _numeric_parameter(model_id: str, name: str) -> dict:
    contract = model_registry.get_contract(model_id)
    spec = next((p for p in contract["parameters"] if p["name"] == name), None)
    if spec is None or spec["type"] not in ("number", "integer"):
        raise AnalysisError(f"'{name}' is not a numeric parameter of {model_id}.", "invalid_parameter", name=name)
    return spec


def _outputs(model_id: str, names: list[str] | None) -> list[dict]:
    declared = model_registry.get_contract(model_id)["outputs"]
    if not names:
        return declared
    unknown = [n for n in names if n not in {o["name"] for o in declared}]
    if unknown:
        raise AnalysisError(f"Unknown output(s) {', '.join(unknown)} for {model_id}.", "unknown_output", names=unknown)
    return [o for o in declared if o["name"] in names]


def _evaluate(model_id: str, inputs: dict, outputs: list[dict]) -> dict[str, Any]:
    env = model_registry.run_model(model_id, inputs)
    values = {}
    for out in outputs:
        value = env["outputs"][out["name"]]["value"]
        values[out["name"]] = value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None
    numerical = None
    summary = env["result"].get("summary", {}) if isinstance(env["result"], dict) else {}
    if isinstance(summary.get("estimated_final_error"), dict):
        numerical = max(summary["estimated_final_error"].values(), default=None)
    return {"values": values, "numerical_error": numerical, "warnings": [w.get("code") for w in env.get("warnings", [])]}


def sweep_values(spec: dict[str, Any]) -> list[float]:
    """values: explicit list, or {start, stop, count, spacing: linear|log}."""
    if isinstance(spec, list):
        values = spec
    elif isinstance(spec, dict):
        start, stop, count, spacing = spec.get("start"), spec.get("stop"), spec.get("count", 11), spec.get("spacing", "linear")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (start, stop)):
            raise AnalysisError("start and stop must be finite numbers.")
        if isinstance(count, bool) or not isinstance(count, int) or not 2 <= count <= 1000:
            raise AnalysisError("count must be an integer between 2 and 1000.")
        if spacing == "log":
            if start <= 0 or stop <= 0:
                raise AnalysisError("Logarithmic spacing needs positive start and stop.")
            values = [start * (stop / start) ** (i / (count - 1)) for i in range(count)]
        elif spacing == "linear":
            values = [start + (stop - start) * i / (count - 1) for i in range(count)]
        else:
            raise AnalysisError("spacing must be 'linear' or 'log'.")
    else:
        raise AnalysisError("values must be a list or {start, stop, count, spacing}.")
    if not 2 <= len(values) <= 1000:
        raise AnalysisError("A sweep needs between 2 and 1000 values.")
    return [float(v) for v in values]


def parameter_sweep(model_id: str, base_inputs: dict, parameter: str, values: Any, outputs: list[str] | None = None, control=None) -> dict:
    control = control or _NoControl()
    spec = _numeric_parameter(model_id, parameter)
    outs = _outputs(model_id, outputs)
    grid = sweep_values(values)
    rows = []
    for k, value in enumerate(grid):
        control.check(k, len(grid))
        point = int(round(value)) if spec["type"] == "integer" else value
        try:
            ev = _evaluate(model_id, {**base_inputs, parameter: point}, outs)
            rows.append({"parameter_value": point, **ev["values"], "status": "ok", "warnings": ev["warnings"]})
        except (ContractError, ValueError) as exc:  # a failed point is recorded, the sweep continues
            rows.append({"parameter_value": point, **{o["name"]: None for o in outs}, "status": "failed",
                         "error_code": getattr(exc, "code", "invalid_parameter"), "error": str(exc)})
    control.check(len(grid), len(grid))
    return {"analysis": "parameter_sweep", "model_id": model_id, "model_version": model_registry.get_contract(model_id)["version"],
            "parameter": {"name": parameter, "unit": spec.get("unit") or spec.get("unit_from")}, "outputs": outs, "base_inputs": base_inputs,
            "rows": rows, "failed_points": sum(r["status"] == "failed" for r in rows), "interpretation": INTERPRETATION}


def local_sensitivity(model_id: str, base_inputs: dict, parameters: list[str] | None = None, outputs: list[str] | None = None,
                      relative_step: float = 1e-3, control=None) -> dict:
    """Normalised coefficients S = (∂y/∂p)·(p/y) by central differences at h and h/2 (Richardson-combined)."""
    control = control or _NoControl()
    if not (1e-8 <= relative_step <= 0.1):
        raise AnalysisError("relative_step must lie between 1e-8 and 0.1.")
    contract = model_registry.get_contract(model_id)
    normalized = model_registry.run_model(model_id, base_inputs)["inputs"]
    names = parameters or [p["name"] for p in contract["parameters"] if p["type"] == "number" and isinstance(normalized.get(p["name"]), (int, float))]
    outs = _outputs(model_id, outputs)
    base = _evaluate(model_id, base_inputs, outs)["values"]
    total, done, table = len(names) * 4, 0, []
    for name in names:
        _numeric_parameter(model_id, name)
        p0 = normalized.get(name)
        if not isinstance(p0, (int, float)) or p0 == 0:
            table.append({"parameter": name, "status": "skipped", "reason": "parameter is zero or not set: normalised coefficient undefined"})
            done += 4; continue
        estimates = {}
        try:
            for factor in (1.0, 0.5):
                h = abs(p0) * relative_step * factor
                control.check(done, total); up = _evaluate(model_id, {**base_inputs, name: p0 + h}, outs)["values"]; done += 1
                control.check(done, total); down = _evaluate(model_id, {**base_inputs, name: p0 - h}, outs)["values"]; done += 1
                estimates[factor] = {o["name"]: (None if up[o["name"]] is None or down[o["name"]] is None else (up[o["name"]] - down[o["name"]]) / (2 * h)) for o in outs}
        except (ContractError, ValueError) as exc:
            table.append({"parameter": name, "status": "failed", "error_code": getattr(exc, "code", "invalid_parameter"), "error": str(exc)})
            continue
        for o in outs:
            d1, d2, y = estimates[1.0][o["name"]], estimates[0.5][o["name"]], base[o["name"]]
            if d1 is None or d2 is None or not y:
                table.append({"parameter": name, "output": o["name"], "status": "undefined"}); continue
            derivative = (4 * d2 - d1) / 3  # Richardson extrapolation of the central difference (error O(h⁴))
            agreement = abs(d1 - d2) / max(abs(derivative), 1e-300)
            table.append({"parameter": name, "output": o["name"], "derivative": derivative, "normalised_coefficient": derivative * p0 / y,
                          "units": f"{o['unit']} per {(_numeric_parameter(model_id, name).get('unit') or 'unit')}",
                          "step_agreement": agreement, "converged": agreement < 1e-2, "status": "ok"})
    return {"analysis": "local_sensitivity", "model_id": model_id, "base_inputs": base_inputs, "base_outputs": base,
            "relative_step": relative_step, "rows": table,
            "method": "central differences at h and h/2, Richardson-combined; 'converged' when the two estimates agree within 1 %",
            "interpretation": INTERPRETATION + " A local coefficient is valid only near the base point."}


_DISTRIBUTIONS = ("normal", "uniform", "lognormal", "triangular")


def _sampler(name: str, spec: dict):
    kind = spec.get("distribution")
    if kind not in _DISTRIBUTIONS:
        raise AnalysisError(f"{name}: distribution must be one of {', '.join(_DISTRIBUTIONS)}.")
    num = lambda key: spec.get(key) if isinstance(spec.get(key), (int, float)) and not isinstance(spec.get(key), bool) and math.isfinite(spec.get(key)) else None
    if kind == "normal":
        mean, sd = num("mean"), num("sd")
        if mean is None or sd is None or sd < 0:
            raise AnalysisError(f"{name}: normal needs mean and sd ≥ 0.")
        return lambda rng: rng.gauss(mean, sd)
    if kind == "uniform":
        low, high = num("low"), num("high")
        if low is None or high is None or high <= low:
            raise AnalysisError(f"{name}: uniform needs low < high.")
        return lambda rng: rng.uniform(low, high)
    if kind == "lognormal":
        median, gsd = num("median"), num("geometric_sd")
        if median is None or gsd is None or median <= 0 or gsd < 1:
            raise AnalysisError(f"{name}: lognormal needs median > 0 and geometric_sd ≥ 1.")
        return lambda rng: rng.lognormvariate(math.log(median), math.log(gsd))
    low, mode, high = num("low"), num("mode"), num("high")
    if low is None or mode is None or high is None or not low <= mode <= high or low == high:
        raise AnalysisError(f"{name}: triangular needs low ≤ mode ≤ high with low < high.")
    return lambda rng: rng.triangular(low, high, mode)


def _quantile(ordered, q):
    idx = (len(ordered) - 1) * q
    lo, hi = math.floor(idx), math.ceil(idx)
    return ordered[lo] if lo == hi else ordered[lo] * (hi - idx) + ordered[hi] * (idx - lo)


def monte_carlo(model_id: str, base_inputs: dict, distributions: dict, outputs: list[str] | None = None, samples: int = 500, seed: int = 7,
                instrument_sd: dict | None = None, bootstrap: int = 500, control=None) -> dict:
    """Propagate parameter uncertainty; report numerical and (optional) instrument uncertainty separately."""
    control = control or _NoControl()
    if isinstance(samples, bool) or not isinstance(samples, int) or not 20 <= samples <= MAX_EVALUATIONS:
        raise AnalysisError(f"samples must be an integer between 20 and {MAX_EVALUATIONS}.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise AnalysisError("seed must be an integer.")
    if not isinstance(distributions, dict) or not distributions:
        raise AnalysisError("Provide at least one parameter distribution.")
    samplers = {}
    for name, spec in distributions.items():
        _numeric_parameter(model_id, name)
        samplers[name] = _sampler(name, spec if isinstance(spec, dict) else {})
    outs = _outputs(model_id, outputs)
    rng = random.Random(seed)
    values = {o["name"]: [] for o in outs}
    rejected, rejection_codes, numerical = 0, {}, []
    for k in range(samples):
        control.check(k, samples)
        draw = {name: sampler(rng) for name, sampler in samplers.items()}
        try:
            ev = _evaluate(model_id, {**base_inputs, **draw}, outs)
        except (ContractError, ValueError) as exc:  # e.g. a draw outside the contract bounds
            rejected += 1
            code = getattr(exc, "code", "invalid_parameter")
            rejection_codes[code] = rejection_codes.get(code, 0) + 1
            continue
        if any(v is None for v in ev["values"].values()):
            rejected += 1; rejection_codes["non_numeric_output"] = rejection_codes.get("non_numeric_output", 0) + 1
            continue
        for name, v in ev["values"].items():
            values[name].append(v)
        if ev["numerical_error"] is not None:
            numerical.append(ev["numerical_error"])
    control.check(samples, samples)
    accepted = len(next(iter(values.values()))) if values else 0
    if accepted < max(20, samples // 2):
        raise AnalysisError(f"Only {accepted} of {samples} samples were valid: narrow the distributions or check the contract bounds.", "too_few_samples",
                            rejection_codes=rejection_codes)
    stats = {}
    boot_rng = random.Random(seed + 1)
    for o in outs:
        data = values[o["name"]]
        ordered = sorted(data)
        n = len(data)
        mean = sum(data) / n
        sd = math.sqrt(sum((v - mean) ** 2 for v in data) / (n - 1))
        means = sorted(sum(boot_rng.choice(data) for _ in range(n)) / n for _ in range(bootstrap))
        half = data[: n // 2]
        half_mean = sum(half) / len(half)
        entry = {"unit": o["unit"], "mean": mean, "sd": sd, "standard_error_of_mean": sd / math.sqrt(n), "median": _quantile(ordered, 0.5),
                 "q025": _quantile(ordered, 0.025), "q975": _quantile(ordered, 0.975), "min": ordered[0], "max": ordered[-1],
                 "mean_ci95_bootstrap": [_quantile(means, 0.025), _quantile(means, 0.975)],
                 "convergence": {"first_half_mean": half_mean, "relative_change": abs(mean - half_mean) / max(abs(mean), 1e-300),
                                 "stable": abs(mean - half_mean) <= 3 * sd / math.sqrt(len(half)) if sd > 0 else True}}
        if instrument_sd and o["name"] in instrument_sd:
            s_inst = float(instrument_sd[o["name"]])
            entry["combined_with_instrument"] = {"instrument_sd": s_inst, "combined_sd": math.sqrt(sd ** 2 + s_inst ** 2),
                                                 "method": "root-sum-square of independent parameter and instrument components"}
        stats[o["name"]] = entry
    return {"analysis": "monte_carlo", "model_id": model_id, "samples_requested": samples, "samples_accepted": accepted, "samples_rejected": rejected,
            "rejection_codes": rejection_codes, "seed": seed, "distributions": distributions, "statistics": stats,
            "uncertainty_breakdown": {
                "parameter": "statistics above: spread caused by the sampled parameter distributions",
                "numerical": {"max_estimated_solver_error": max(numerical) if numerical else None,
                              "note": "solver error estimates reported by the engine for the sampled runs (when available)"},
                "measurement": "combined_with_instrument entries, only when instrument_sd is supplied (simulated instruments)"},
            "assumptions": ["Parameters are sampled independently; correlations between parameters are not modelled.",
                            "Draws outside the contract bounds are rejected and counted; the distributions are therefore truncated."],
            "interpretation": INTERPRETATION}


def to_csv(result: dict) -> str:
    """CSV export of a sweep or Monte Carlo summary, or of a sensitivity table."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if result.get("analysis") == "parameter_sweep":
        names = [o["name"] for o in result["outputs"]]
        writer.writerow([f"{result['parameter']['name']} ({result['parameter']['unit']})"] + [f"{o['name']} ({o['unit']})" for o in result["outputs"]] + ["status", "error"])
        for row in result["rows"]:
            writer.writerow([row["parameter_value"]] + [row.get(n) for n in names] + [row["status"], row.get("error", "")])
    elif result.get("analysis") == "local_sensitivity":
        writer.writerow(["parameter", "output", "derivative", "normalised_coefficient", "units", "converged", "status"])
        for row in result["rows"]:
            writer.writerow([row.get("parameter"), row.get("output"), row.get("derivative"), row.get("normalised_coefficient"), row.get("units"), row.get("converged"), row.get("status")])
    elif result.get("analysis") == "monte_carlo":
        writer.writerow(["output", "unit", "mean", "sd", "median", "q025", "q975", "mean_ci95_low", "mean_ci95_high"])
        for name, s in result["statistics"].items():
            writer.writerow([name, s["unit"], s["mean"], s["sd"], s["median"], s["q025"], s["q975"], *s["mean_ci95_bootstrap"]])
    else:
        raise AnalysisError("Nothing to export for this result.")
    return buffer.getvalue()
