"""v8.0 — tool-connected assistant: real tool calls, traced values, honest failures, no invented result."""
from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import assistant
import model_registry


def test_answer_comes_from_a_traced_tool_call():
    r = assistant.answer("Quelle est la constante de temps d'un circuit RC avec R = 2 kΩ et C = 3 µF ?")
    assert r["status"] == "answered" and r["assistant"].startswith("rule-based")
    call = r["tool_calls"][0]
    assert call["tool"] == "run_model" and call["status"] == "ok" and call["arguments"]["model_id"] == "rc_rl_step_response"
    assert call["arguments"]["inputs"]["resistance_ohm"] == {"value": 2.0, "unit": "kΩ"}  # converted by the contract, not by the assistant
    direct = model_registry.run_model("rc_rl_step_response", {"resistance_ohm": 2000.0, "capacitance_f": 3e-6})["outputs"]["time_constant"]["value"]
    value = next(v for s in r["statements"] for v in s.get("values", []) if v["name"] == "time_constant")
    assert value["value"] == pytest.approx(direct) and value["unit"] == "s" and value["source"] == call["id"]
    assert "[c1]" in r["text"] and assistant.untraced_numbers(r) == []


def test_a_failing_tool_gives_no_value():
    r = assistant.answer("Constante de temps d'un circuit RC avec R = -5 Ω ?")
    assert r["status"] == "tool_failed" and r["tool_calls"][0]["status"] == "error"
    assert not any(s.get("values") for s in r["statements"]) and "Aucune valeur" in r["text"]


def test_missing_information_triggers_a_clarification():
    r = assistant.answer("Quel est le pH d'une solution d'acide acétique ?")
    assert r["status"] == "clarification_needed" and r["statements"][0]["missing"] == ["total_concentration_mol_l"] and r["tool_calls"] == []


def test_sourced_data_are_used_and_cited():
    r = assistant.answer("Quel est le pH d'une solution d'acide acétique à 0.01 mol/L ?")
    tools = [c["tool"] for c in r["tool_calls"]]
    assert tools == ["search_catalog", "run_model"] and "pka_aqueous_25c" in r["text"] and "valeur approchée" in r["text"]
    ph = next(v for s in r["statements"] for v in s.get("values", []) if v.get("name") == "ph")
    assert 3.3 < ph["value"] < 3.45


@pytest.mark.parametrize("question,status", [
    ("Quelle dose de chimiothérapie pour ce patient ?", "out_of_scope"),
    ("What will the weather be tomorrow?", "out_of_scope"),
    ("Combien de pattes a une araignée ?", "unknown"),
])
def test_out_of_scope_and_unknown_questions_are_not_answered(question, status):
    r = assistant.answer(question)
    assert r["status"] == status and r["tool_calls"] == [] and not any(s.get("values") for s in r["statements"])


def test_maturity_and_validation_questions_use_the_registries():
    r = assistant.answer("Le modèle de Michaelis est-il validé ?")
    assert [c["tool"] for c in r["tool_calls"]] == ["maturity", "validations"] and "Validé sur données" in r["text"]


def test_unused_quantities_are_reported():
    r = assistant.answer("Constante de temps d'un circuit RC avec R = 1 kΩ et une masse de 3 kg")
    assert any("3 kg" in s["text"] for s in r["statements"] if s["kind"] == "limitation")


def test_untraced_number_detector_catches_an_invented_value():
    r = assistant.answer("Quelle est la constante de vitesse d'Arrhenius à T = 350 K ?")
    tampered = {**r, "text": r["text"] + "\nLa demi-vie vaut 123.456 s."}
    assert assistant.untraced_numbers(tampered) == ["123.456"]


def test_assistant_api():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/api/assistant/ask", data=json.dumps({"question": "Parle-moi du modèle de Hodgkin"}).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert data["status"] == "answered" and data["tool_calls"][0]["tool"] == "describe_model" and data["untraced_numbers"] == []
