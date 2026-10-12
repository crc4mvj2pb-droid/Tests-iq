"""v8.1 — research question → variables, testable hypotheses, evaluation criterion; clarification instead of guessing."""
from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import model_registry
import research_question as rq


@pytest.mark.parametrize("question,model,x,y", [
    ("Quel est l'effet de la résistance sur la constante de temps ?", "rc_rl_step_response", "resistance_ohm", "time_constant"),
    ("Effet de la température sur la constante de vitesse", "arrhenius_reaction", "temperature_k", "rate_constant"),
    ("Effet de la résistance thermique sur la température stationnaire", "lumped_thermal_transient", "thermal_resistance_k_per_w", "steady_temperature"),
    ("How does the current affect the firing rate?", "hodgkin_huxley", "current_ua_cm2", "firing_rate"),
])
def test_questions_are_mapped_to_contract_variables(question, model, x, y):
    f = rq.formulate(question)
    assert f["status"] == "formulated" and f["model_id"] == model
    assert f["independent_variable"]["name"] == x and f["dependent_variable"]["name"] == y
    contract = model_registry.get_contract(model)
    spec = next(p for p in contract["parameters"] if p["name"] == x)
    assert f["independent_variable"]["unit"] == spec.get("unit") and f["independent_variable"]["reference_value"] == spec["default"]
    assert {c["name"] for c in f["controlled_variables"]}.isdisjoint({x}) and f["controlled_variables"]


def test_three_testable_hypotheses_with_a_computable_criterion():
    f = rq.formulate("Quel est l'effet de la résistance sur la constante de temps ?")
    assert [h["id"] for h in f["hypotheses"]] == ["H1", "H2", "H0"] and all(h["test"] for h in f["hypotheses"])
    assert "normalised sensitivity" in f["evaluation_criterion"] and str(rq.EFFECT_THRESHOLD) in f["evaluation_criterion"]


def test_longer_phrases_win():
    f = rq.formulate("Effet de la résistance thermique sur la température stationnaire")
    assert f["independent_variable"]["name"] == "thermal_resistance_k_per_w"  # not the electrical resistance


@pytest.mark.parametrize("question,missing", [("Quel est l'effet de la capacité ?", "dependent_variable"),
                                              ("Effet de la couleur sur la constante de temps", "independent_variable")])
def test_missing_variables_trigger_a_clarification_with_choices(question, missing):
    f = rq.formulate(question)
    assert f["status"] == "clarification_needed" and f["missing"] == [missing] and f["choices"]


def test_impossible_combination_is_unknown():
    f = rq.formulate("Effet de la fréquence sur la population finale")
    assert f["status"] == "unknown"


def test_scope_note_reminds_that_the_model_is_tested_not_reality():
    f = rq.formulate("Effet de la température sur la constante de vitesse")
    assert "not on the real system" in f["scope_note"] and "not validated on data" in f["scope_note"]


def test_api():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/api/research/formulate",
                                     data=json.dumps({"question": "Effet de la puissance sur la constante de temps"}).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert data["status"] == "formulated" and data["model_id"] == "lumped_thermal_transient"
