"""v8.3 — planned execution as a task graph: validation before each run, limits, real cancellation, honest node states."""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import analysis
import app
import jobs
import task_graph as tg


def statuses(result):
    return {n["name"]: n["status"] for n in result["nodes"]}


def test_complete_plan_runs_every_node_in_dependency_order():
    r = tg.run_question("Effet de la résistance sur la constante de temps")
    assert r["status"] == "completed" and set(statuses(r).values()) == {"done"}
    assert [n["name"] for n in r["nodes"]] == ["validate", "reference", "duplicate", "sweep", "sensitivity", "analysis"]
    assert r["results"]["analysis"]["monotonicity"] == "increasing" and r["results"]["sensitivity"]["normalised_coefficient"] == pytest.approx(1.0, abs=1e-6)
    assert all("duration_ms" in n for n in r["nodes"]) and r["model_runs"] == 2 + 7 + 5


def test_null_effect_is_observed_as_constant_output():
    r = tg.run_question("Effet de la puissance sur la constante de temps")  # τ = R·C does not depend on P
    assert r["results"]["analysis"]["monotonicity"] == "constant" and r["results"]["sensitivity"]["normalised_coefficient"] == pytest.approx(0.0, abs=1e-9)


def test_run_limit_stops_the_plan_and_skips_dependents():
    r = tg.run_question("Effet de la résistance sur la constante de temps", max_runs=4)
    s = statuses(r)
    assert r["status"] == "stopped_max_runs" and s["sweep"] == "stopped" and s["sensitivity"] == "skipped" and s["analysis"] == "skipped"
    assert "sweep" not in r["results"] and r["model_runs"] == 4


def test_time_limit_stops_the_plan():
    r = tg.run_question("How does the current affect the firing rate?", time_limit_s=0.0)
    assert r["status"] == "stopped_time_limit" and statuses(r)["reference"] == "stopped"


def test_unformulated_question_is_not_executed():
    assert tg.run_question("Effet de la couleur sur la constante de temps")["status"] == "not_executed"


def test_cancellation_through_the_jobs_manager_is_real():
    job = jobs.MANAGER.submit("research_plan", tg.run_question, question="How does the current affect the firing rate?", points=31)
    for _ in range(200):
        if jobs.MANAGER.public(job["id"])["status"] == "running":
            break
        time.sleep(0.01)
    jobs.MANAGER.cancel(job["id"])
    done = jobs.MANAGER.wait(job["id"], timeout=60)
    assert done["status"] in ("cancelled", "completed")
    if done["status"] == "cancelled":
        assert done.get("result") is None  # no partial result published


def test_api_job():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        req = urllib.request.Request(base + "/api/jobs", data=json.dumps({"kind": "research_plan", "question": "Effet de la température sur la constante de vitesse", "points": 5}).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            job = json.loads(resp.read())
        result = jobs.MANAGER.wait(job["id"], timeout=60)
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert result["status"] == "completed" and result["result"]["results"]["analysis"]["monotonicity"] == "increasing"
