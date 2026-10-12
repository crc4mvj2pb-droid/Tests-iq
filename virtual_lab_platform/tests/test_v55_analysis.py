"""v5.5 — sweeps, local sensitivity, Monte Carlo uncertainty and background jobs."""
from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import analysis
import app
import history
import jobs
from analysis import AnalysisError, local_sensitivity, monte_carlo, parameter_sweep
from constants import GAS_CONSTANT

CHEAP_RC = {"points": 2}


def test_linear_and_log_grids_and_integer_parameters():
    assert analysis.sweep_values({"start": 1, "stop": 3, "count": 3}) == [1.0, 2.0, 3.0]
    assert analysis.sweep_values({"start": 1, "stop": 100, "count": 3, "spacing": "log"}) == pytest.approx([1, 10, 100])
    r = parameter_sweep("rc_rl_step_response", CHEAP_RC, "points", [2.4, 3.6], ["first_time"])
    assert [row["parameter_value"] for row in r["rows"]] == [2, 4]
    for bad in ({"start": 0, "stop": 1, "count": 3, "spacing": "log"}, {"start": 1, "stop": 2, "count": 1}, [1], "x"):
        with pytest.raises(AnalysisError):
            analysis.sweep_values(bad)


def test_a_failed_point_is_recorded_and_the_sweep_continues():
    r = parameter_sweep("rc_rl_step_response", CHEAP_RC, "resistance_ohm", [1000, -5, 2000], ["time_constant"])
    assert [row["status"] for row in r["rows"]] == ["ok", "failed", "ok"]
    assert r["rows"][1]["error_code"] == "out_of_range" and r["failed_points"] == 1
    assert r["rows"][2]["time_constant"] == pytest.approx(2e-3)
    assert "not evidence of a causal mechanism" in r["interpretation"]


@pytest.mark.parametrize("model_id,base,param,output,expected", [
    ("rc_rl_step_response", CHEAP_RC, "resistance_ohm", "time_constant", 1.0),
    ("rc_rl_step_response", CHEAP_RC, "capacitance_f", "time_constant", 1.0),
    ("series_rlc_step_response", {"points": 2}, "inductance_h", "natural_angular_frequency", -0.5),
    ("series_rlc_step_response", {"points": 2}, "capacitance_f", "natural_angular_frequency", -0.5),
    ("arrhenius_reaction", {}, "pre_exponential_s_inv", "rate_constant", 1.0),
    ("arrhenius_reaction", {}, "activation_energy_j_mol", "rate_constant", -40000.0 / (GAS_CONSTANT * 298.15)),
    ("arrhenius_reaction", {}, "temperature_k", "rate_constant", 40000.0 / (GAS_CONSTANT * 298.15)),
])
def test_sensitivity_matches_analytical_elasticities(model_id, base, param, output, expected):
    r = local_sensitivity(model_id, base, [param], [output])
    row = r["rows"][0]
    assert row["status"] == "ok" and row["converged"] and row["normalised_coefficient"] == pytest.approx(expected, rel=1e-6)


def test_monte_carlo_is_reproducible_and_matches_the_analytical_spread():
    dist = {"resistance_ohm": {"distribution": "normal", "mean": 1000, "sd": 50}}
    a = monte_carlo("rc_rl_step_response", CHEAP_RC, dist, ["time_constant"], samples=600, seed=11)
    b = monte_carlo("rc_rl_step_response", CHEAP_RC, dist, ["time_constant"], samples=600, seed=11)
    c = monte_carlo("rc_rl_step_response", CHEAP_RC, dist, ["time_constant"], samples=600, seed=12)
    assert a["statistics"] == b["statistics"] and a["statistics"] != c["statistics"]
    s = a["statistics"]["time_constant"]
    assert s["mean"] == pytest.approx(1e-3, rel=0.01) and s["sd"] == pytest.approx(5e-5, rel=0.15) and s["unit"] == "s"
    assert s["convergence"]["stable"] is True


def test_bootstrap_interval_of_the_mean_has_about_95_percent_coverage():
    covered, seeds = 0, 100
    for seed in range(seeds):
        r = monte_carlo("rc_rl_step_response", CHEAP_RC, {"resistance_ohm": {"distribution": "normal", "mean": 1000, "sd": 100}},
                        ["time_constant"], samples=100, seed=seed, bootstrap=200)
        low, high = r["statistics"]["time_constant"]["mean_ci95_bootstrap"]
        covered += low <= 1e-3 <= high
    assert 0.88 <= covered / seeds <= 0.99, covered


def test_distributions_truncation_and_instrument_combination():
    r = monte_carlo("rc_rl_step_response", CHEAP_RC, {"resistance_ohm": {"distribution": "lognormal", "median": 1000, "geometric_sd": 1.2}}, ["time_constant"], samples=800, seed=1)
    assert r["statistics"]["time_constant"]["median"] == pytest.approx(1e-3, rel=0.05)
    r = monte_carlo("rc_rl_step_response", CHEAP_RC, {"resistance_ohm": {"distribution": "normal", "mean": 100, "sd": 150}}, ["time_constant"], samples=400, seed=2)
    assert r["samples_rejected"] > 0 and r["rejection_codes"].get("out_of_range") == r["samples_rejected"]
    r = monte_carlo("rc_rl_step_response", CHEAP_RC, {"capacitance_f": {"distribution": "uniform", "low": 0.9e-6, "high": 1.1e-6}}, ["time_constant"],
                    samples=200, seed=3, instrument_sd={"time_constant": 3e-5})
    comb = r["statistics"]["time_constant"]["combined_with_instrument"]
    assert comb["combined_sd"] == pytest.approx(math.hypot(r["statistics"]["time_constant"]["sd"], 3e-5))
    assert set(r["uncertainty_breakdown"]) == {"parameter", "numerical", "measurement"}
    for bad in ({"distribution": "normal", "mean": 1}, {"distribution": "uniform", "low": 2, "high": 1}, {"distribution": "weibull"}, {"distribution": "lognormal", "median": 1, "geometric_sd": 0.5}):
        with pytest.raises(AnalysisError):
            monte_carlo("rc_rl_step_response", CHEAP_RC, {"resistance_ohm": bad}, samples=20)


def test_numerical_uncertainty_is_reported_separately_for_kinetics():
    base_inputs = {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
                   "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5, "activation_energy_j_mol": 50000}],
                   "duration": 2.0, "dt": 0.1}
    r = monte_carlo("mass_action_kinetics", base_inputs, {"temperature_k": {"distribution": "uniform", "low": 290, "high": 310}}, ["integration_steps"], samples=20, seed=1)
    numerical = r["uncertainty_breakdown"]["numerical"]["max_estimated_solver_error"]
    assert r["samples_accepted"] == 20 and numerical is not None and 0 < numerical < 1e-6


def test_drawing_an_incompatible_value_is_rejected_not_altered():
    # duration must be a multiple of dt: such draws are refused by the engine and counted, never rounded silently.
    base_inputs = {"species": [{"id": "A", "initial_concentration": 1.0}], "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"A": 1}, "rate_constant": 0.0}],
                   "duration": 2.0, "dt": 0.1}
    with pytest.raises(AnalysisError) as exc:
        monte_carlo("mass_action_kinetics", base_inputs, {"duration": {"distribution": "uniform", "low": 1.0, "high": 3.0}}, ["integration_steps"], samples=20, seed=1)
    assert exc.value.code == "too_few_samples"


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v55.sqlite3")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def call(url, body=None, raw=False):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode()
            return r.status, (data if raw else json.loads(data))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def poll(base, job_id, until=("completed", "failed", "cancelled")):
    for _ in range(500):
        code, job = call(f"{base}/api/jobs/{job_id}")
        if job["status"] in until:
            return job
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_sweep_job_progress_result_and_csv_export(base):
    code, job = call(base + "/api/jobs", {"kind": "sweep", "model_id": "rc_rl_step_response", "base_inputs": CHEAP_RC, "parameter": "resistance_ohm",
                                          "values": {"start": 100, "stop": 1000, "count": 10}, "outputs": ["time_constant"]})
    assert code == 200 and job["status"] in ("queued", "running", "completed")
    done = poll(base, job["id"])
    assert done["status"] == "completed" and done["progress"]["fraction"] == 1.0 and len(done["result"]["rows"]) == 10
    code, text = call(f"{base}/api/jobs/{job['id']}.csv", raw=True)
    assert code == 200 and text.splitlines()[0] == "resistance_ohm (Ω),time_constant (s),status,error" and len(text.splitlines()) == 11


def test_cancellation_stops_a_long_job_without_publishing_a_result(base):
    code, job = call(base + "/api/jobs", {"kind": "monte_carlo", "model_id": "rc_rl_step_response", "base_inputs": {"points": 2001},
                                          "distributions": {"resistance_ohm": {"distribution": "normal", "mean": 1000, "sd": 10}}, "samples": 5000})
    time.sleep(0.2)
    call(f"{base}/api/jobs/{job['id']}/cancel", {})
    done = poll(base, job["id"])
    assert done["status"] == "cancelled" and "result" not in done and done["progress"]["done"] < 5000
    assert call(f"{base}/api/jobs/{job['id']}.csv", raw=True)[0] == 409


def test_job_errors_are_reported_with_codes(base):
    code, job = call(base + "/api/jobs", {"kind": "monte_carlo", "model_id": "rc_rl_step_response", "distributions": {"resistance_ohm": {"distribution": "weibull"}}})
    failed = poll(base, job["id"])
    assert failed["status"] == "failed" and failed["error"]["error_code"] == "invalid_analysis"
    assert call(base + "/api/jobs", {"kind": "sweep", "model_id": "nope"})[1]["error_code"] == "unknown_model"
    assert call(base + "/api/jobs", {"kind": "dance", "model_id": "rc_rl_step_response"})[1]["error_code"] == "invalid_analysis"
    assert call(base + "/api/jobs/0123456789ab")[1]["error_code"] == "unknown_job"
