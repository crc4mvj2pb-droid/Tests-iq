"""Planned, safe execution of a research protocol as a traceable task graph (v8.3).

Nodes (with dependencies): validate → reference → duplicate → sweep → sensitivity → analysis.
Rules:
  - inputs are validated against the model contract before every model run;
  - limits: a wall-clock budget and a maximum number of model runs per plan; when a limit is hit the
    running node stops, its dependents are marked "skipped", and the plan status says which limit;
  - cancellation is real: the plan checks the cancellation flag between runs (jobs manager control);
    nothing keeps running in the background after "cancelled" is reported;
  - a failed node never produces results; its dependents are skipped, not guessed.
"""
from __future__ import annotations

import time
from typing import Any

import analysis
import model_registry
import protocol_design
import research_question
import units
from contracts import validate_inputs

DEFAULT_TIME_LIMIT_S = 120.0
DEFAULT_MAX_RUNS = 200
NODES = [("validate", []), ("reference", ["validate"]), ("duplicate", ["reference"]), ("sweep", ["duplicate"]),
         ("sensitivity", ["reference"]), ("analysis", ["sweep", "sensitivity"])]


class LimitReached(Exception):
    def __init__(self, which: str):
        super().__init__(which)
        self.which = which


class _Budget:
    def __init__(self, time_limit_s: float, max_runs: int, control):
        self.start, self.time_limit_s, self.max_runs, self.runs, self.control = time.perf_counter(), time_limit_s, max_runs, 0, control

    def charge(self, done: int, total: int) -> None:
        if self.control is not None:
            self.control.check(done, total)  # raises analysis.Cancelled when the user cancels
        if time.perf_counter() - self.start > self.time_limit_s:
            raise LimitReached("time_limit")
        if self.runs >= self.max_runs:
            raise LimitReached("max_runs")
        self.runs += 1


def _run(model_id: str, inputs: dict, budget: _Budget, done: int, total: int) -> dict:
    contract = model_registry.get_contract(model_id)
    validate_inputs(contract, inputs, converter=units.contract_converter)  # checked before every run
    budget.charge(done, total)
    return model_registry.run_model(model_id, inputs)["outputs"]


def execute(protocol: dict[str, Any], time_limit_s: float = DEFAULT_TIME_LIMIT_S, max_runs: int = DEFAULT_MAX_RUNS, control=None) -> dict[str, Any]:
    if protocol.get("status") != "designed":
        return {"status": "not_executed", "reason": "No designed protocol to execute.", "protocol": protocol}
    model_id = protocol["model_id"]
    f = protocol["formulation"]
    x, y = f["independent_variable"]["name"], f["dependent_variable"]["name"]
    budget = _Budget(float(time_limit_s), int(max_runs), control)
    nodes = {name: {"name": name, "depends_on": deps, "status": "pending"} for name, deps in NODES}
    total = len(protocol["runs"]) + 4
    results: dict[str, Any] = {}
    plan_status = "completed"

    def blocked(name):
        return any(nodes[d]["status"] != "done" for d in nodes[name]["depends_on"])

    for name, _ in NODES:
        node = nodes[name]
        if blocked(name):
            node["status"] = "skipped"
            node["reason"] = "a prerequisite did not complete"
            continue
        node["status"], node["started"] = "running", time.perf_counter()
        try:
            if name == "validate":
                contract = model_registry.get_contract(model_id)
                for run in protocol["runs"]:
                    validate_inputs(contract, run["inputs"], converter=units.contract_converter)
                node["output"] = {"checked_runs": len(protocol["runs"])}
            elif name == "reference":
                results["reference"] = _run(model_id, protocol["runs"][0]["inputs"], budget, budget.runs, total)
                node["output"] = {y: results["reference"][y]}
            elif name == "duplicate":
                dup = _run(model_id, protocol["runs"][1]["inputs"], budget, budget.runs, total)
                if dup != results["reference"]:
                    raise ValueError("The duplicate reference run differs from the reference run: the engine is not deterministic.")
                node["output"] = {"identical_to_reference": True}
            elif name == "sweep":
                rows = []
                for run in protocol["runs"][2:]:
                    out = _run(model_id, run["inputs"], budget, budget.runs, total)
                    rows.append({"x": run["inputs"][x], "y": out[y]["value"], "unit": out[y]["unit"]})
                results["sweep"] = rows
                node["output"] = {"points": len(rows)}
            elif name == "sensitivity":
                for _ in range(5):  # central differences at h and h/2 plus the reference: 5 model runs
                    budget.charge(budget.runs, total)
                s = analysis.local_sensitivity(model_id, {x: f["independent_variable"]["reference_value"]}, [x], [y])
                results["sensitivity"] = s["rows"][0]
                node["output"] = {"normalised_coefficient": s["rows"][0].get("normalised_coefficient"), "converged": s["rows"][0].get("converged")}
            elif name == "analysis":
                ys = [r["y"] for r in results["sweep"]]
                diffs = [b - a for a, b in zip(ys, ys[1:])]
                monotonic = "increasing" if all(d > 0 for d in diffs) else "decreasing" if all(d < 0 for d in diffs) else \
                    "constant" if all(d == 0 for d in diffs) else "non-monotonic"
                results["analysis"] = {"monotonicity": monotonic, "y_min": min(ys), "y_max": max(ys)}
                node["output"] = results["analysis"]
            node["status"] = "done"
        except analysis.Cancelled:
            node["status"], plan_status = "cancelled", "cancelled"
        except LimitReached as exc:
            node["status"], node["reason"], plan_status = "stopped", exc.which, f"stopped_{exc.which}"
        except Exception as exc:
            node["status"], node["error"] = "failed", {"type": type(exc).__name__, "message": str(exc)[:300], "code": getattr(exc, "code", None)}
            plan_status = "failed"
        node["duration_ms"] = round((time.perf_counter() - node.pop("started")) * 1000, 3)
        if plan_status == "cancelled" or plan_status.startswith("stopped_"):
            for later, _ in NODES:
                if nodes[later]["status"] == "pending":
                    nodes[later]["status"] = "cancelled" if plan_status == "cancelled" else "skipped"
                    nodes[later]["reason"] = "plan cancelled" if plan_status == "cancelled" else f"limit reached ({plan_status[8:]})"
            break
    if plan_status == "cancelled" and control is not None:
        raise analysis.Cancelled()  # the jobs manager reports "cancelled" and publishes no partial result
    return {"status": plan_status, "model_id": model_id, "question": f["question"], "nodes": list(nodes.values()),
            "model_runs": budget.runs, "limits": {"time_limit_s": time_limit_s, "max_runs": max_runs},
            "results": results if plan_status == "completed" else {k: v for k, v in results.items()},
            "note": "Results of skipped, stopped or failed nodes are absent; nothing is extrapolated."}


def run_question(question: str, points: int = protocol_design.DEFAULT_POINTS, time_limit_s: float = DEFAULT_TIME_LIMIT_S,
                 max_runs: int = DEFAULT_MAX_RUNS, control=None) -> dict[str, Any]:
    """Formulate → design → execute, as one job (used by the jobs manager)."""
    formulation = research_question.formulate(question)
    protocol = protocol_design.design(formulation, points)
    result = execute(protocol, time_limit_s, max_runs, control)
    result["formulation"] = formulation
    result["protocol"] = {k: protocol.get(k) for k in ("status", "sweep", "runs", "replicates_per_point", "not_simulated", "reason")}
    return result
