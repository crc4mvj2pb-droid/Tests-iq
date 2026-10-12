"""v7.6 — interdisciplinary comparison: uncertainty propagated through a model chain, and the effect of each hypothesis."""
from __future__ import annotations

import copy
import json
import math
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import pipeline_analysis as pa
import pipelines
from constants import GAS_CONSTANT
from pipelines import PipelineError


def joule():
    return copy.deepcopy(pipelines.example_pipelines()["joule_heating_kinetics"])


def test_temperature_spread_matches_first_order_propagation():
    dist = {"circuit.resistors[0].resistance_ohm": {"distribution": "normal", "mean": 48.0, "sd": 0.5},
            "heating.thermal_resistance_k_per_w": {"distribution": "normal", "mean": 4.0, "sd": 0.4}}
    r = pa.monte_carlo(joule(), dist, ["heating.temperature_k"], samples=1500, seed=11)
    # T = T_amb + (V²/R_h)·R_th  ⇒  σ_T² ≈ (P·σ_Rth)² + (V²·R_th/R_h²·σ_Rh)²
    expected = math.hypot(3.0 * 0.4, 144.0 * 4.0 / 48.0 ** 2 * 0.5)
    s = r["statistics"]["heating.temperature_k"]
    assert s["sd"] == pytest.approx(expected, rel=0.06) and s["samples"] == 1500 and r["failures"] == 0


def test_rate_constant_is_lognormal_when_only_the_activation_energy_is_uncertain():
    sd_ea = 1500.0
    r = pa.monte_carlo(joule(), {"arrhenius.activation_energy_j_mol": {"distribution": "normal", "mean": 60000.0, "sd": sd_ea}},
                       ["arrhenius.rate_constant"], samples=1500, seed=5)
    s = r["statistics"]["arrhenius.rate_constant"]
    sigma = sd_ea / (GAS_CONSTANT * 310.15)  # ln k = ln A − Ea/(RT) is normal
    assert s["mean"] / s["baseline"] == pytest.approx(math.exp(sigma ** 2 / 2), rel=0.05)


def test_monte_carlo_is_reproducible_with_its_seed():
    dist = {"heating.thermal_resistance_k_per_w": {"distribution": "uniform", "low": 3.5, "high": 4.5}}
    a = pa.monte_carlo(joule(), dist, ["heating.temperature_k"], samples=50, seed=2)
    b = pa.monte_carlo(joule(), dist, ["heating.temperature_k"], samples=50, seed=2)
    assert a["statistics"] == b["statistics"] and "Parametric uncertainty only" in a["scope"]


def test_hypothesis_effects_are_reported_one_by_one():
    ex = pa.joule_uncertainty_example()
    h = pa.hypothesis_effects(joule(), ex["hypotheses"], ex["outputs"])
    by = {x["name"]: x["effects"]["heating.temperature_k"]["change"] for x in h["hypotheses"]}
    assert by["ambient 20 °C"] == pytest.approx(-5.0) and by["no self-heating"] == pytest.approx(-12.0) and by["better insulation"] == pytest.approx(12.0)
    assert h["largest_effect"]["heating.temperature_k"] == "no self-heating"


@pytest.mark.parametrize("dist,outputs,code", [
    ({"nowhere.x": {"distribution": "normal", "mean": 1, "sd": 1}}, ["heating.temperature_k"], "invalid_uncertain_input"),
    ({"heating.thermal_resistance_k_per_w": {"distribution": "cauchy"}}, ["heating.temperature_k"], "invalid_distribution"),
    ({"heating.thermal_resistance_k_per_w": {"distribution": "normal", "mean": 4, "sd": 0.1}}, ["heating.nothing"], "unknown_output"),
])
def test_invalid_requests(dist, outputs, code):
    with pytest.raises(PipelineError) as exc:
        pa.monte_carlo(joule(), dist, outputs, samples=20)
    assert exc.value.code == code


def test_failed_draws_are_counted_not_hidden():
    dist = {"heating.thermal_resistance_k_per_w": {"distribution": "normal", "mean": 0.2, "sd": 0.5}}  # some draws ≤ 0 are refused by the adapter
    r = pa.monte_carlo(joule(), dist, ["heating.temperature_k"], samples=100, seed=1)
    assert r["failures"] > 0 and r["statistics"]["heating.temperature_k"]["samples"] == 100 - r["failures"]


def test_api():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        with urllib.request.urlopen(base + "/api/pipelines/uncertainty-example", timeout=10) as resp:
            ex = json.loads(resp.read())
        body = {"spec": pipelines.example_pipelines()[ex["pipeline"]], "distributions": ex["distributions"], "outputs": ex["outputs"], "samples": 40, "seed": 1}
        req = urllib.request.Request(base + "/api/pipelines/uncertainty", data=json.dumps(body).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            mc = json.loads(resp.read())
        req = urllib.request.Request(base + "/api/pipelines/hypotheses", data=json.dumps({"spec": body["spec"], "hypotheses": ex["hypotheses"], "outputs": ex["outputs"]}).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            hy = json.loads(resp.read())
        req = urllib.request.Request(base + "/api/pipelines/uncertainty", data=json.dumps({**body, "samples": 999999}).encode(), method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req, timeout=10)
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert mc["statistics"]["heating.temperature_k"]["samples"] == 40 and len(hy["hypotheses"]) == 3 and exc.value.code == 400
