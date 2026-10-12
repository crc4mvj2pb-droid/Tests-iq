"""Numerical integration with explicit tolerances, stopping criteria and diagnostics (v5.2).

Two adaptive integrators for y' = f(t, y):
- `dopri5`: explicit Dormand–Prince 5(4) with embedded error estimate (non-stiff problems);
- `implicit_euler`: backward Euler with Newton iterations and step-doubling error control
  (L-stable, first order) for stiff problems such as fast/slow reaction networks.

Every failure raises NumericalError with a stable code and the diagnostics gathered so far,
so a caller never receives a silently wrong result.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

Vector = list[float]


class NumericalError(ValueError):
    def __init__(self, message: str, code: str, diagnostics: dict | None = None):
        super().__init__(message)
        self.code = code
        self.params = {"diagnostics": diagnostics or {}}


@dataclass
class Tolerances:
    rtol: float = 1e-8
    atol: float = 1e-12
    max_steps: int = 100_000
    min_step_fraction: float = 1e-14  # minimum step relative to the integration interval

    def validate(self) -> "Tolerances":
        if not (1e-14 <= self.rtol <= 1e-2):
            raise NumericalError("rtol must lie between 1e-14 and 1e-2.", "invalid_tolerance")
        if not (0 < self.atol <= 1.0):
            raise NumericalError("atol must lie in (0, 1].", "invalid_tolerance")
        if not (10 <= self.max_steps <= 2_000_000):
            raise NumericalError("max_steps must lie between 10 and 2,000,000.", "invalid_tolerance")
        return self


@dataclass
class Diagnostics:
    method: str
    accepted_steps: int = 0
    rejected_steps: int = 0
    function_evaluations: int = 0
    newton_iterations: int = 0
    jacobian_evaluations: int = 0
    smallest_step: float = math.inf
    largest_step: float = 0.0
    status: str = "running"
    notes: list = field(default_factory=list)
    # Sum over accepted steps of |local error estimate| per component: a propagation-free indicator of the global error.
    accumulated_local_error: list = field(default_factory=list)

    def accumulate(self, err) -> None:
        if not self.accumulated_local_error:
            self.accumulated_local_error = [0.0] * len(err)
        self.accumulated_local_error = [a + abs(e) for a, e in zip(self.accumulated_local_error, err)]

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["smallest_step"] = None if math.isinf(self.smallest_step) else self.smallest_step
        return d


def _norm(err: Sequence[float], y_old: Sequence[float], y_new: Sequence[float], tol: Tolerances) -> float:
    """RMS of the error scaled by atol + rtol·|y| (Hairer–Wanner); ≤ 1 means the step meets the tolerance."""
    total = 0.0
    for e, a, b in zip(err, y_old, y_new):
        scale = tol.atol + tol.rtol * max(abs(a), abs(b))
        total += (e / scale) ** 2
    return math.sqrt(total / max(1, len(err)))


def _check_finite(y: Sequence[float], t: float, diag: Diagnostics) -> None:
    if not all(math.isfinite(v) for v in y):
        diag.status = "failed"
        raise NumericalError(f"The solution became non-finite near t = {t:.6g} (blow-up or divergent model).", "non_finite", diag.as_dict())


# Dormand–Prince 5(4) coefficients
_C = (0, 1/5, 3/10, 4/5, 8/9, 1, 1)
_A = ((), (1/5,), (3/40, 9/40), (44/45, -56/15, 32/9), (19372/6561, -25360/2187, 64448/6561, -212/729),
      (9017/3168, -355/33, 46732/5247, 49/176, -5103/18656), (35/384, 0, 500/1113, 125/192, -2187/6784, 11/84))
_B5 = (35/384, 0, 500/1113, 125/192, -2187/6784, 11/84, 0)
_B4 = (5179/57600, 0, 7571/16695, 393/640, -92097/339200, 187/2100, 1/40)


def dopri5(f: Callable[[float, Vector], Vector], t0: float, y0: Sequence[float], t_end: float, output_times: Sequence[float],
           tol: Tolerances | None = None) -> tuple[list[Vector], dict]:
    """Adaptive explicit integration; returns the solution at each output time and diagnostics."""
    tol = (tol or Tolerances()).validate()
    diag = Diagnostics("dopri5")
    span = t_end - t0
    h_min = tol.min_step_fraction * abs(span)
    t, y = t0, [float(v) for v in y0]
    k1 = f(t, y); diag.function_evaluations += 1
    h = _initial_step(f, t, y, k1, tol, span, diag)
    outputs, targets, idx = [], list(output_times), 0
    while idx < len(targets) and targets[idx] <= t0:
        outputs.append(y[:]); idx += 1
    while idx < len(targets):
        if diag.accepted_steps + diag.rejected_steps >= tol.max_steps:
            diag.status = "failed"
            raise NumericalError(f"Maximum number of steps ({tol.max_steps}) reached at t = {t:.6g}. If the step size became very small, "
                                 "the problem is probably stiff: use method 'implicit_euler'.", "max_steps_exceeded", diag.as_dict())
        if targets[idx] - t <= 1e-12 * max(1.0, abs(t)):  # already at the output time (round-off)
            outputs.append(y[:]); idx += 1
            continue
        h = min(h, targets[idx] - t)
        ks = [k1]
        for stage in range(1, 7):
            yi = [y[j] + h * sum(_A[stage][m] * ks[m][j] for m in range(stage)) for j in range(len(y))]
            ks.append(f(t + _C[stage] * h, yi)); diag.function_evaluations += 1
        y5 = [y[j] + h * sum(_B5[m] * ks[m][j] for m in range(7)) for j in range(len(y))]
        err = [h * sum((_B5[m] - _B4[m]) * ks[m][j] for m in range(7)) for j in range(len(y))]
        _check_finite(y5, t + h, diag)
        en = _norm(err, y, y5, tol)
        if en <= 1.0:
            diag.accumulate(err)
            t += h; y = y5; k1 = ks[6]  # FSAL
            diag.accepted_steps += 1; diag.smallest_step = min(diag.smallest_step, h); diag.largest_step = max(diag.largest_step, h)
            while idx < len(targets) and abs(targets[idx] - t) <= 1e-12 * max(1.0, abs(t)):
                outputs.append(y[:]); idx += 1
        else:
            diag.rejected_steps += 1
        h *= min(5.0, max(0.2, 0.9 * (1.0 / max(en, 1e-10)) ** 0.2))
        if h < h_min and idx < len(targets):
            diag.status = "failed"
            raise NumericalError(f"Step size underflow at t = {t:.6g}: the tolerance cannot be met (stiff or singular problem).", "step_size_underflow", diag.as_dict())
    diag.status = "converged"
    return outputs, diag.as_dict()


def _initial_step(f, t, y, f0, tol, span, diag) -> float:
    d0 = math.sqrt(sum((v / (tol.atol + tol.rtol * abs(v))) ** 2 for v in y) / max(1, len(y)))
    d1 = math.sqrt(sum((v / (tol.atol + tol.rtol * abs(w))) ** 2 for v, w in zip(f0, y)) / max(1, len(y)))
    h = 0.01 * d0 / d1 if d0 > 1e-5 and d1 > 1e-5 else 1e-6 * abs(span)
    return min(h, abs(span))


def _solve(a: list[Vector], b: Vector) -> Vector:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    scale = max((abs(v) for row in a for v in row), default=1.0) or 1.0
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) <= 1e-15 * scale:
            raise ZeroDivisionError
        m[col], m[piv] = m[piv], m[col]
        for r in range(n):
            if r != col and m[r][col]:
                factor = m[r][col] / m[col][col]
                m[r] = [x - factor * yv for x, yv in zip(m[r], m[col])]
    return [m[i][n] / m[i][i] for i in range(n)]


def _jacobian(f, t, y, fy, diag) -> list[Vector]:
    n = len(y)
    jac = [[0.0] * n for _ in range(n)]
    for j in range(n):
        step = 1e-8 * max(1.0, abs(y[j]))
        yp = y[:]; yp[j] += step
        fp = f(t, yp); diag.function_evaluations += 1
        for i in range(n):
            jac[i][j] = (fp[i] - fy[i]) / step
    diag.jacobian_evaluations += 1
    return jac


def _backward_euler_step(f, t, y, h, diag, tol) -> Vector:
    """Solve z = y + h·f(t+h, z) by Newton iterations; raises ArithmeticError when Newton does not converge."""
    z = y[:]
    fz = f(t + h, z); diag.function_evaluations += 1
    jac = _jacobian(f, t + h, z, fz, diag)
    n = len(y)
    matrix = [[(1.0 if i == j else 0.0) - h * jac[i][j] for j in range(n)] for i in range(n)]
    for _ in range(12):
        residual = [z[i] - y[i] - h * fz[i] for i in range(n)]
        try:
            delta = _solve(matrix, [-r for r in residual])
        except ZeroDivisionError:
            raise ArithmeticError("singular Newton matrix")
        z = [z[i] + delta[i] for i in range(n)]
        diag.newton_iterations += 1
        fz = f(t + h, z); diag.function_evaluations += 1
        if not all(math.isfinite(v) for v in z):
            raise ArithmeticError("non-finite Newton iterate")
        if _norm(delta, y, z, Tolerances(rtol=tol.rtol * 1e-2, atol=tol.atol * 1e-2)) <= 1.0:
            return z
    raise ArithmeticError("Newton iterations did not converge")


def implicit_euler(f: Callable[[float, Vector], Vector], t0: float, y0: Sequence[float], t_end: float, output_times: Sequence[float],
                   tol: Tolerances | None = None) -> tuple[list[Vector], dict]:
    """Adaptive extrapolated backward Euler (order 2, L-stable) with step-doubling error control, for stiff systems."""
    tol = (tol or Tolerances(rtol=1e-6, atol=1e-10)).validate()
    diag = Diagnostics("implicit_euler")
    span = t_end - t0
    h_min = tol.min_step_fraction * abs(span)
    t, y = t0, [float(v) for v in y0]
    h = 1e-6 * abs(span) if span else 0.0
    outputs, targets, idx = [], list(output_times), 0
    while idx < len(targets) and targets[idx] <= t0:
        outputs.append(y[:]); idx += 1
    while idx < len(targets):
        if diag.accepted_steps + diag.rejected_steps >= tol.max_steps:
            diag.status = "failed"
            raise NumericalError(f"Maximum number of steps ({tol.max_steps}) reached at t = {t:.6g}.", "max_steps_exceeded", diag.as_dict())
        if targets[idx] - t <= 1e-12 * max(1.0, abs(t)):  # already at the output time (round-off)
            outputs.append(y[:]); idx += 1
            continue
        h = min(h, targets[idx] - t)
        try:
            full = _backward_euler_step(f, t, y, h, diag, tol)
            half = _backward_euler_step(f, t, y, h / 2, diag, tol)
            half = _backward_euler_step(f, t + h / 2, half, h / 2, diag, tol)
        except ArithmeticError as exc:
            diag.rejected_steps += 1
            diag.notes.append(f"t={t:.4g}: {exc}; step reduced")
            h /= 4
            if h < h_min:
                diag.status = "failed"
                raise NumericalError(f"Newton iterations do not converge at t = {t:.6g} even with tiny steps.", "non_convergence", diag.as_dict())
            continue
        # Richardson extrapolation of implicit Euler (one step vs two half steps): second order and still
        # L-stable (Hairer & Wanner II, §IV.9). The difference half − full is a conservative error estimate.
        err = [a - b for a, b in zip(half, full)]
        extrapolated = [2 * a - b for a, b in zip(half, full)]
        en = _norm(err, y, extrapolated, tol)
        if en <= 1.0:
            diag.accumulate(err)
            t += h; y = extrapolated
            diag.accepted_steps += 1; diag.smallest_step = min(diag.smallest_step, h); diag.largest_step = max(diag.largest_step, h)
            while idx < len(targets) and abs(targets[idx] - t) <= 1e-12 * max(1.0, abs(t)):
                outputs.append(y[:]); idx += 1
        else:
            diag.rejected_steps += 1
        h *= min(4.0, max(0.2, 0.9 / math.sqrt(max(en, 1e-10))))
        if h < h_min and idx < len(targets):
            diag.status = "failed"
            raise NumericalError(f"Step size underflow at t = {t:.6g}.", "step_size_underflow", diag.as_dict())
    diag.status = "converged"
    return outputs, diag.as_dict()


UNCERTAINTY_KINDS = {
    "numerical": "error of the solver (discretisation, round-off), estimated by the method",
    "parameter": "propagation of the uncertainty of the input parameters (Monte Carlo, v5.5)",
    "measurement": "uncertainty of an instrument reading (simulated measurements only, v4.7)",
}
