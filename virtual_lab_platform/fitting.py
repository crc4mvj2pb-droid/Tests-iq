"""Nonlinear least-squares model fitting with diagnostics (v6.3).

Levenberg–Marquardt on closed-form models with units derived from the data units. Reported:
estimates, standard errors and 95 % confidence intervals from the linear approximation
s²·(JᵀJ)⁻¹ (Bates & Watts, 1988), correlation matrix, residuals, R², RMSE, AIC, Durbin–Watson
statistic and a runs test on residual signs. Fitting and validation data are kept separate when a
split is requested, and every prediction outside the fitted x-range is flagged as extrapolation.

Assumptions stated with each result: independent errors, constant variance, correct model form.
A good fit is not evidence that the model is mechanistically correct.
"""
from __future__ import annotations

import math
import random
from typing import Any, Callable

import units
from constants import GAS_CONSTANT

ENGINE_ID = "nonlinear_least_squares"
ENGINE_VERSION = "1.0"


class FitError(ValueError):
    def __init__(self, message: str, code: str = "invalid_fit_request", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def _mm(x, p): return p[0] * x / (p[1] + x)
def _rise(x, p): return p[0] * (1 - math.exp(-p[1] * x))
def _decay(x, p): return p[0] * math.exp(-p[1] * x)
def _linear(x, p): return p[0] + p[1] * x
def _logistic(x, p): return p[0] / (1 + (p[0] - p[1]) / p[1] * math.exp(-p[2] * x))
def _arrhenius(x, p): return p[0] * math.exp(-p[1] / (GAS_CONSTANT * x))
def _power(x, p): return p[0] * x ** p[1]


def _start_mm(xs, ys):
    vmax = max(ys)
    half = min(zip(xs, ys), key=lambda t: abs(t[1] - vmax / 2))[0]
    return [vmax, max(half, 1e-12)]


def _start_rise(xs, ys):
    a = max(ys)
    x_half = min(zip(xs, ys), key=lambda t: abs(t[1] - a / 2))[0]
    return [a, math.log(2) / max(x_half, 1e-12)]


def _start_decay(xs, ys):
    pts = [(x, y) for x, y in zip(xs, ys) if y > 0]
    if len(pts) < 2:
        return [max(ys), 1.0]
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    return [y0, max(math.log(y0 / y1) / (x1 - x0), 1e-12) if x1 != x0 and y1 > 0 else 1.0]


def _start_linear(xs, ys):
    n, mx, my = len(xs), sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    return [my - b * mx, b]


def _start_logistic(xs, ys):
    k = max(ys) * 1.05
    n0 = max(min(ys), k * 1e-6)
    return [k, n0, 4.0 / max(max(xs) - min(xs), 1e-12)]


def _start_arrhenius(xs, ys):
    pts = [(1 / x, math.log(y)) for x, y in zip(xs, ys) if y > 0 and x > 0]
    a, b = _start_linear([p[0] for p in pts], [p[1] for p in pts])
    return [math.exp(a), -b * GAS_CONSTANT]


def _start_power(xs, ys):
    pts = [(math.log(x), math.log(y)) for x, y in zip(xs, ys) if y > 0 and x > 0]
    a, b = _start_linear([p[0] for p in pts], [p[1] for p in pts])
    return [math.exp(a), b]


# name: (function, parameter names, parameter unit templates, equation, start heuristic). {x}/{y} = data units.
MODELS: dict[str, dict[str, Any]] = {
    "michaelis_menten": {"f": _mm, "params": ["Vm", "K"], "units": ["{y}", "{x}"], "equation": "y = Vm·x/(K + x)", "start": _start_mm},
    "first_order_rise": {"f": _rise, "params": ["A", "k"], "units": ["{y}", "1/({x})"], "equation": "y = A·(1 − e^(−k·x))", "start": _start_rise},
    "exponential_decay": {"f": _decay, "params": ["y0", "k"], "units": ["{y}", "1/({x})"], "equation": "y = y0·e^(−k·x)", "start": _start_decay},
    "linear": {"f": _linear, "params": ["a", "b"], "units": ["{y}", "({y})/({x})"], "equation": "y = a + b·x", "start": _start_linear},
    "logistic": {"f": _logistic, "params": ["K", "N0", "r"], "units": ["{y}", "{y}", "1/({x})"], "equation": "y = K/(1 + ((K − N0)/N0)·e^(−r·x))", "start": _start_logistic},
    "arrhenius": {"f": _arrhenius, "params": ["A", "Ea"], "units": ["{y}", "J/mol"], "equation": "y = A·e^(−Ea/(R·x)), x = T in K", "start": _start_arrhenius, "x_unit": "K"},
    "power_law": {"f": _power, "params": ["a", "b"], "units": ["{y}·({x})^-b", "1"], "equation": "y = a·x^b", "start": _start_power},
}


# ---- small linear algebra and Student's t ----------------------------------------------------

def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-300:
            raise FitError("Singular normal equations: the parameters are not identifiable from these data.", "not_identifiable")
        m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            for c in range(col, n + 1):
                m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][c] * x[c] for c in range(r + 1, n))) / m[r][r]
    return x


def _inverse(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    cols = [_solve(a, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    return [[cols[j][i] for j in range(n)] for i in range(n)]


def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return h


def _betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    return bt * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * _betacf(b, a, 1 - x) / b


def t_cdf(t: float, df: float) -> float:
    """Student's t cumulative distribution (regularized incomplete beta, Numerical Recipes §6.4)."""
    x = df / (df + t * t)
    tail = 0.5 * _betai(df / 2, 0.5, x)
    return 1 - tail if t > 0 else tail


def t_quantile(p: float, df: float) -> float:
    lo, hi = -1e3, 1e3
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---- fitting ---------------------------------------------------------------------------------

def _jacobian(f, xs, p):
    jac = []
    for x in xs:
        row = []
        for k in range(len(p)):
            h = 1e-6 * max(abs(p[k]), 1e-8)
            up, dn = list(p), list(p)
            up[k] += h; dn[k] -= h
            row.append((f(x, up) - f(x, dn)) / (2 * h))
        jac.append(row)
    return jac


def _sse(f, xs, ys, p):
    try:
        return sum((y - f(x, p)) ** 2 for x, y in zip(xs, ys))
    except (OverflowError, ZeroDivisionError, ValueError):
        return math.inf


def levenberg_marquardt(f: Callable, xs: list[float], ys: list[float], p0: list[float], max_iter: int = 500) -> tuple[list[float], dict[str, Any]]:
    p, lam = list(p0), 1e-3
    sse = _sse(f, xs, ys, p)
    if not math.isfinite(sse):
        raise FitError("The model cannot be evaluated at the starting values.", "invalid_start")
    for iteration in range(1, max_iter + 1):
        jac = _jacobian(f, xs, p)
        r = [y - f(x, p) for x, y in zip(xs, ys)]
        jtj = [[sum(jac[i][a] * jac[i][b] for i in range(len(xs))) for b in range(len(p))] for a in range(len(p))]
        jtr = [sum(jac[i][a] * r[i] for i in range(len(xs))) for a in range(len(p))]
        while True:
            damped = [[jtj[a][b] * (1 + lam if a == b else 1) for b in range(len(p))] for a in range(len(p))]
            try:
                step = _solve(damped, jtr)
            except FitError:
                lam *= 10
                if lam > 1e16:
                    raise
                continue
            trial = [a + b for a, b in zip(p, step)]
            trial_sse = _sse(f, xs, ys, trial)
            if trial_sse < sse:
                converged = abs(sse - trial_sse) <= 1e-14 * max(sse, 1e-300) or max(abs(s) / max(abs(v), 1e-12) for s, v in zip(step, trial)) < 1e-10
                p, sse, lam = trial, trial_sse, max(lam / 10, 1e-12)
                if converged:
                    return p, {"iterations": iteration, "converged": True, "sse": sse}
                break
            lam *= 10
            if lam > 1e16:
                return p, {"iterations": iteration, "converged": True, "sse": sse, "note": "no further decrease of the sum of squares"}
    return p, {"iterations": max_iter, "converged": False, "sse": sse}


def _diagnostics(residuals: list[float]) -> dict[str, Any]:
    n = len(residuals)
    ss = sum(r * r for r in residuals)
    dw = sum((residuals[i] - residuals[i - 1]) ** 2 for i in range(1, n)) / ss if ss > 0 else None
    signs = [r > 0 for r in residuals if r != 0]
    n_pos, n_neg = sum(signs), len(signs) - sum(signs)
    runs = 1 + sum(signs[i] != signs[i - 1] for i in range(1, len(signs))) if signs else 0
    runs_test = None
    if n_pos and n_neg:
        expected = 2 * n_pos * n_neg / (n_pos + n_neg) + 1
        variance = 2 * n_pos * n_neg * (2 * n_pos * n_neg - n_pos - n_neg) / ((n_pos + n_neg) ** 2 * (n_pos + n_neg - 1)) if n_pos + n_neg > 1 else 0
        z = (runs - expected) / math.sqrt(variance) if variance > 0 else None
        runs_test = {"runs": runs, "expected": expected, "z": z, "note": "|z| > 2 suggests systematic residual structure (wrong model form or correlated errors)"}
    return {"durbin_watson": dw, "runs_test": runs_test,
            "durbin_watson_note": "≈ 2 for uncorrelated residuals in x order; values far below 2 indicate positive autocorrelation"}


def _split(n: int, validation: dict[str, Any] | None) -> tuple[list[int], list[int]]:
    if not validation:
        return list(range(n)), []
    method = validation.get("method")
    if method == "indices":
        held = sorted({int(i) for i in validation.get("indices", [])})
        if not held or any(not 0 <= i < n for i in held):
            raise FitError("Validation indices must be valid row numbers (0-based).", "invalid_split")
    elif method == "alternate":  # every second point (in data order) held out, e.g. the second of each replicate pair
        held = list(range(1, n, 2))
    elif method == "holdout":
        fraction = validation.get("fraction", 0.25)
        if not isinstance(fraction, (int, float)) or not 0 < fraction < 0.9:
            raise FitError("Holdout fraction must be in (0, 0.9).", "invalid_split")
        rng = random.Random(int(validation.get("seed", 1)))
        held = sorted(rng.sample(range(n), max(1, round(fraction * n))))
    else:
        raise FitError("validation.method must be 'indices', 'alternate' or 'holdout'.", "invalid_split")
    fit = [i for i in range(n) if i not in held]
    return fit, held


def _unit_text(template: str, x_unit: str, y_unit: str) -> str:
    """Substitute data units into a parameter unit template; parentheses only around compound units."""
    wrap = lambda u: f"({u})" if any(c in u for c in "/·* ") else u
    out = template.replace("({x})", wrap(x_unit)).replace("({y})", wrap(y_unit))
    return out.replace("{x}", x_unit).replace("{y}", y_unit)


def fit(request: dict[str, Any]) -> dict[str, Any]:
    model_name = request.get("model")
    if model_name not in MODELS:
        raise FitError(f"Unknown model. Available: {', '.join(MODELS)}.", "unknown_model")
    model = MODELS[model_name]
    xs_all, ys_all = request.get("x"), request.get("y")
    if not isinstance(xs_all, list) or not isinstance(ys_all, list) or len(xs_all) != len(ys_all):
        raise FitError("x and y must be lists of the same length.", "invalid_data")
    pairs = [(float(x), float(y)) for x, y in zip(xs_all, ys_all) if isinstance(x, (int, float)) and isinstance(y, (int, float))
             and not isinstance(x, bool) and not isinstance(y, bool) and math.isfinite(x) and math.isfinite(y)]
    if len(pairs) != len(xs_all):
        raise FitError("x and y must contain finite numbers only (remove or impute missing values explicitly first).", "invalid_data")
    x_unit, y_unit = request.get("x_unit") or "1", request.get("y_unit") or "1"
    for u in (x_unit, y_unit):
        try:
            units.parse(u)
        except units.UnitError as exc:
            raise FitError(f"Unit '{u}' not understood: {exc}", "invalid_unit") from exc
    if model.get("x_unit") and not units.compatible(x_unit, model["x_unit"]):
        raise FitError(f"Model {model_name} needs x in {model['x_unit']} (got {x_unit}).", "incompatible_unit")
    if model.get("x_unit"):
        pairs = [(units.convert(x, x_unit, model["x_unit"]), y) for x, y in pairs]
    fit_idx, held_idx = _split(len(pairs), request.get("validation"))
    xs, ys = [pairs[i][0] for i in fit_idx], [pairs[i][1] for i in fit_idx]
    p_count = len(model["params"])
    if len(xs) <= p_count:
        raise FitError(f"At least {p_count + 1} fitting points are needed for {p_count} parameters.", "too_few_points")
    start = request.get("start") or model["start"](xs, ys)
    if not isinstance(start, list) or len(start) != p_count:
        raise FitError(f"start must give {p_count} values ({', '.join(model['params'])}).", "invalid_start")
    estimates, info = levenberg_marquardt(model["f"], xs, ys, [float(v) for v in start])
    f = model["f"]
    fitted = [f(x, estimates) for x in xs]
    residuals = [y - yhat for y, yhat in zip(ys, fitted)]
    n, dof = len(xs), len(xs) - p_count
    sse = sum(r * r for r in residuals)
    s2 = sse / dof
    jac = _jacobian(f, xs, estimates)
    jtj = [[sum(jac[i][a] * jac[i][b] for i in range(n)) for b in range(p_count)] for a in range(p_count)]
    inverse = _inverse(jtj)
    cov = [[s2 * v for v in row] for row in inverse]
    t975 = t_quantile(0.975, dof)
    unit_of = {"{x}": model.get("x_unit") or x_unit, "{y}": y_unit}
    params = {}
    for k, name in enumerate(model["params"]):
        se = math.sqrt(cov[k][k]) if cov[k][k] > 0 else float("nan")
        unit = _unit_text(model["units"][k], unit_of["{x}"], unit_of["{y}"])
        params[name] = {"value": estimates[k], "standard_error": se, "ci95": [estimates[k] - t975 * se, estimates[k] + t975 * se], "unit": unit,
                        "relative_standard_error": se / abs(estimates[k]) if estimates[k] else None}
    corr = [[inverse[a][b] / math.sqrt(inverse[a][a] * inverse[b][b]) for b in range(p_count)] for a in range(p_count)]  # independent of s²
    mean_y = sum(ys) / n
    sst = sum((y - mean_y) ** 2 for y in ys)
    order = sorted(range(n), key=lambda i: xs[i])
    result = {"engine": {"id": ENGINE_ID, "version": ENGINE_VERSION}, "model": model_name, "equation": model["equation"],
              "x_unit": unit_of["{x}"], "y_unit": y_unit, "parameters": params, "correlation": {"names": model["params"], "matrix": corr},
              "fit_points": n, "degrees_of_freedom": dof, "residual_standard_error": math.sqrt(s2), "sse": sse,
              "r_squared": 1 - sse / sst if sst > 0 else None, "rmse": math.sqrt(sse / n), "aic": n * math.log(sse / n) + 2 * p_count if sse > 0 else None,
              "residuals": [{"x": xs[i], "observed": ys[i], "fitted": fitted[i], "residual": residuals[i], "standardized": residuals[i] / math.sqrt(s2) if s2 > 0 else None} for i in order],
              "diagnostics": _diagnostics([residuals[i] for i in order]), "optimizer": {"method": "Levenberg–Marquardt", "start": start, **info},
              "fit_range": {"x_min": min(xs), "x_max": max(xs)},
              "assumptions": ["Independent errors with constant variance (unweighted least squares).", "The model form is correct over the fitted range.",
                              "Confidence intervals use the linear approximation s²(JᵀJ)⁻¹; they can be inaccurate for strongly nonlinear parameters or small samples."],
              "limitations": ["A good fit does not prove the mechanism.", "Predictions outside the fitted x-range are extrapolations and are flagged as such."]}
    high = [f"{model['params'][a]}–{model['params'][b]}" for a in range(p_count) for b in range(a + 1, p_count) if abs(corr[a][b]) > 0.95]
    if high:
        result["warnings"] = [{"code": "highly_correlated_parameters", "pairs": high, "message": "Parameters are strongly correlated (|r| > 0.95): individual values are poorly determined."}]
    if held_idx:
        vx, vy = [pairs[i][0] for i in held_idx], [pairs[i][1] for i in held_idx]
        pred = [f(x, estimates) for x in vx]
        vres = [y - p for y, p in zip(vy, pred)]
        rmse_v = math.sqrt(sum(r * r for r in vres) / len(vres))
        result["validation"] = {"points": len(vx), "indices": held_idx, "rmse": rmse_v, "bias": sum(vres) / len(vres),
                                "rmse_over_residual_standard_error": rmse_v / math.sqrt(s2) if s2 > 0 else None,
                                "extrapolated_points": sum(not result["fit_range"]["x_min"] <= x <= result["fit_range"]["x_max"] for x in vx),
                                "rows": [{"x": x, "observed": y, "predicted": p, "residual": y - p} for x, y, p in zip(vx, vy, pred)],
                                "note": "Validation points were not used to estimate the parameters."}
    return result


def predict(fit_result: dict[str, Any], xs: list[float]) -> list[dict[str, Any]]:
    model = MODELS[fit_result["model"]]
    p = [fit_result["parameters"][n]["value"] for n in model["params"]]
    lo, hi = fit_result["fit_range"]["x_min"], fit_result["fit_range"]["x_max"]
    return [{"x": x, "y": model["f"](x, p), "extrapolation": not lo <= x <= hi} for x in xs]
