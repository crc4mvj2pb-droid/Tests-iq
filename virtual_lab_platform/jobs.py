"""Background analysis jobs with progress and cooperative cancellation (v5.5).

Jobs run in worker threads. The analysis calls control.check(done, total) between model
evaluations: progress is updated and, when cancellation was requested, the job stops there.
A model evaluation that has already started is allowed to finish (Python threads cannot be
interrupted safely); the job status then says "cancelled" and no partial result is published.
Jobs live in memory only: they disappear when the server stops (results worth keeping are saved
as dossiers or exported).
"""
from __future__ import annotations

import threading
import time
import traceback
import uuid
from typing import Any, Callable

import analysis

MAX_RUNNING = 2
MAX_KEPT = 50


class _Control:
    def __init__(self, job: dict):
        self.job = job

    def check(self, done: int, total: int) -> None:
        self.job["progress"] = {"done": done, "total": total, "fraction": (done / total) if total else 1.0}
        if self.job["cancel_requested"]:
            raise analysis.Cancelled()


class JobManager:
    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._slots = threading.Semaphore(MAX_RUNNING)

    def submit(self, kind: str, func: Callable[..., dict], **kwargs) -> dict:
        job_id = uuid.uuid4().hex[:12]
        job = {"id": job_id, "kind": kind, "status": "queued", "progress": {"done": 0, "total": 0, "fraction": 0.0},
               "created_at": time.time(), "started_at": None, "finished_at": None, "cancel_requested": False, "result": None, "error": None}
        with self._lock:
            self._jobs[job_id] = job
            for old in sorted(self._jobs.values(), key=lambda j: j["created_at"])[:-MAX_KEPT]:
                if old["status"] not in ("queued", "running"):
                    del self._jobs[old["id"]]
        threading.Thread(target=self._run, args=(job, func, kwargs), daemon=True).start()
        return self.public(job_id)

    def _run(self, job, func, kwargs):
        with self._slots:
            if job["cancel_requested"]:
                job.update(status="cancelled", finished_at=time.time()); return
            job.update(status="running", started_at=time.time())
            try:
                job["result"] = func(**kwargs, control=_Control(job))
                job["status"] = "completed"
            except analysis.Cancelled:
                job["status"] = "cancelled"
            except ValueError as exc:
                job.update(status="failed", error={"error": str(exc), "error_code": getattr(exc, "code", "invalid_analysis"), "error_params": getattr(exc, "params", {})})
            except Exception:  # never let a worker die silently
                traceback.print_exc()
                job.update(status="failed", error={"error": "Internal error during the analysis.", "error_code": "internal_error"})
            finally:
                job["finished_at"] = time.time()

    def cancel(self, job_id: str) -> dict:
        job = self._get(job_id)
        if job["status"] in ("queued", "running"):
            job["cancel_requested"] = True
        return self.public(job_id)

    def _get(self, job_id: str) -> dict:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id]

    def public(self, job_id: str) -> dict:
        job = self._get(job_id)
        out = {k: v for k, v in job.items() if k != "result"}
        if job["status"] == "completed":
            out["result"] = job["result"]
        return out

    def result(self, job_id: str) -> dict | None:
        job = self._get(job_id)
        return job["result"] if job["status"] == "completed" else None

    def wait(self, job_id: str, timeout: float = 60.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._get(job_id)["status"] in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.01)
        return self.public(job_id)


MANAGER = JobManager()
KINDS = {"sweep": analysis.parameter_sweep, "sensitivity": analysis.local_sensitivity, "monte_carlo": analysis.monte_carlo}
ARGUMENTS = {"sweep": ("model_id", "base_inputs", "parameter", "values", "outputs"),
             "sensitivity": ("model_id", "base_inputs", "parameters", "outputs", "relative_step"),
             "monte_carlo": ("model_id", "base_inputs", "distributions", "outputs", "samples", "seed", "instrument_sd", "bootstrap")}


def submit_from_request(request: dict) -> dict:
    kind = request.get("kind")
    if kind not in KINDS:
        raise analysis.AnalysisError(f"kind must be one of {', '.join(KINDS)}.", "invalid_analysis")
    kwargs = {k: request[k] for k in ARGUMENTS[kind] if k in request}
    kwargs.setdefault("base_inputs", {})
    if not isinstance(kwargs.get("model_id"), str):
        raise analysis.AnalysisError("model_id is required.", "invalid_analysis")
    import model_registry
    model_registry.get_contract(kwargs["model_id"])  # unknown model → error before starting a job
    return MANAGER.submit(kind, KINDS[kind], **kwargs)
