"""v8.4 — critical analysis: hypotheses vs results, uncertainty, computed / interpreted / generated kept apart, missing data listed."""
from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import critical_analysis as ca


@pytest.mark.parametrize("s,mono,expected", [(1.0, "increasing", "H1"), (-0.8, "decreasing", "H2"), (0.0, "constant", "H0"), (0.01, "increasing", "H0"),
                                             (0.5, "non-monotonic", None), (0.5, "decreasing", None), (None, "increasing", None)])
def test_hypothesis_rules(s, mono, expected):
    assert ca.evaluate_hypotheses(s, mono)["supported"] == expected


def test_three_kinds_of_statements_are_separated_and_labelled():
    r = ca.analyze_question("Effet de la résistance sur la constante de temps", parameter_relative_sd=0.05)
    assert r["status"] == "analyzed" and r["hypothesis_evaluation"]["supported"] == "H1"
    assert all(c["source_node"] in ("sensitivity", "analysis", "reference") for c in r["computed_results"])
    assert r["generated_explanation"].startswith("[Texte généré par règles, à vérifier]")
    assert r["model_interpretation"][0].startswith("H1 supported in the model")


def test_parametric_uncertainty_matches_linear_propagation():
    r = ca.analyze_question("Effet de la résistance sur la constante de temps", parameter_relative_sd=0.05)
    p = r["uncertainty"]["parametric"]
    assert p["sd"] == pytest.approx(0.05 * 1e-3, rel=0.15)  # τ = R·C is linear in R: σ_τ = C·σ_R (300 draws)
    assert p["interval_95"][0] < 1e-3 < p["interval_95"][1]


def test_missing_data_prevent_conclusions_about_reality():
    r = ca.analyze_question("Effet de la puissance sur la constante de temps")
    assert r["hypothesis_evaluation"]["supported"] == "H0" and r["conclusion_scope"] == "model only"
    text = " ".join(r["missing_for_conclusion"])
    assert "not validated on measured data" in text and "illustrative default values" in text and "No input uncertainty" in text


def test_no_analysis_on_partial_or_missing_plans():
    assert ca.analyze({"status": "stopped_max_runs"})["status"] == "not_analyzed"
    assert ca.analyze_question("Effet de la couleur sur la constante de temps")["status"] == "not_analyzed"


def test_api():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/api/research/analyze",
                                     data=json.dumps({"question": "Effet de la température sur la constante de vitesse"}).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert data["hypothesis_evaluation"]["supported"] == "H1" and data["plan_nodes"]
