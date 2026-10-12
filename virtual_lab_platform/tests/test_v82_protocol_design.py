"""v8.2 — protocol design: sweep inside contract bounds, controls, justified replicates, equipment, contract check, non-simulated parts."""
from __future__ import annotations

import json
import math
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import model_registry
import protocol_design as pd
import research_question as rq
from contracts import validate_inputs


def design(q, **kw):
    return pd.design(rq.formulate(q), **kw)


def test_sweep_is_logarithmic_around_the_reference_and_every_run_passes_the_contract():
    d = design("Effet de la résistance sur la constante de temps")
    values = d["sweep"]["values"]
    assert d["status"] == "designed" and values[0] == pytest.approx(500.0) and values[-1] == pytest.approx(2000.0) and len(values) == 7
    ratios = [b / a for a, b in zip(values, values[1:])]
    assert max(ratios) == pytest.approx(min(ratios))  # constant ratio: logarithmic spacing
    contract = model_registry.get_contract("rc_rl_step_response")
    for run in d["runs"]:
        validate_inputs(contract, run["inputs"])  # raises if a planned run violated the contract


def test_controls_and_replicates_are_justified():
    d = design("Effet de la température sur la constante de vitesse")
    roles = [r["role"] for r in d["runs"][:2]]
    assert roles[0].startswith("control: reference") and roles[1].startswith("control: determinism")
    assert d["replicates_per_point"] == 1 and "deterministic" in d["replicate_justification"]


def test_sweep_is_clipped_to_the_contract_bounds():
    f = rq.formulate("Effet de la température sur la constante de vitesse")
    f["independent_variable"] = {**f["independent_variable"], "reference_value": 0.8}  # near the 1 K lower bound of the contract
    d = pd.design(f)
    assert min(d["sweep"]["values"]) >= 1.0


def test_noisy_instrument_requires_a_compatible_unit():
    d = design("Effet de la résistance thermique sur la température stationnaire")
    ids = [e["id"] for e in d["virtual_equipment"]]
    if ids:  # catalogue instruments measuring a temperature
        noisy = design("Effet de la résistance thermique sur la température stationnaire", instrument_id=ids[0])
        assert noisy["replicates_per_point"] == 5 and "seeded noise" in noisy["replicate_justification"]
    wrong = design("Effet de la résistance thermique sur la température stationnaire", instrument_id="analytical_balance")
    assert wrong["status"] == "not_designed" and "does not measure" in wrong["reason"]


def test_non_simulated_parts_are_listed_and_unformulated_questions_are_not_designed():
    d = design("How does the current affect the firing rate?")
    assert any("Sample preparation" in item for item in d["not_simulated"]) and any("Space-clamped" in item for item in d["not_simulated"])
    assert design("Effet de la couleur sur la constante de temps")["status"] == "not_designed"


def test_api():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/api/research/design",
                                     data=json.dumps({"question": "Effet de la résistance sur la constante de temps", "points": 5}).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert data["status"] == "designed" and len(data["sweep"]["values"]) == 5 and len(data["runs"]) == 7
