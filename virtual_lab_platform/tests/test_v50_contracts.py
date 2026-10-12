"""v5.0 — common model contracts: well-formed, faithful to the engines, enforced before computation."""
from __future__ import annotations

import ast
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import app
import history
import model_registry
from contracts import ContractError, check_contract, validate_inputs
from models import SOLVERS

ROOT = Path(__file__).resolve().parents[1]
IDS = sorted(model_registry.REGISTRY)


def test_every_engine_has_a_well_formed_contract():
    assert model_registry.contract_problems() == {}
    assert set(SOLVERS) <= set(IDS)  # every catalogue solver is covered
    for required in ("dc_resistive_network", "workbench_dc_circuit", "rc_rl_step_response", "series_rlc_ac", "mass_action_kinetics", "stoichiometry"):
        assert required in IDS


@pytest.mark.parametrize("model_id", IDS)
def test_example_produces_every_declared_output(model_id):
    entry = model_registry.REGISTRY[model_id]
    env = model_registry.run_model(model_id, entry["example"] or {})
    for name, out in env["outputs"].items():
        assert not out.get("missing"), name
        assert out["unit"]
    assert env["model_version"] == entry["contract"]["version"] and env["provenance"]["engine"]


@pytest.mark.parametrize("model_id", [m for m in IDS if not model_registry.REGISTRY[m]["contract"]["parameters"][0].get("required")
                                      and not any(p.get("required") for p in model_registry.REGISTRY[m]["contract"]["parameters"])])
def test_contract_defaults_match_engine_defaults(model_id):
    # Running with the contract's defaults must give exactly what the engine computes with its own defaults.
    runner = model_registry.REGISTRY[model_id]["runner"]
    assert json.dumps(model_registry.run_model(model_id, {})["result"], sort_keys=True) == json.dumps(runner({}), sort_keys=True)


@pytest.mark.parametrize("model_id", IDS)
def test_numeric_bounds_are_enforced_before_the_engine(model_id):
    contract = model_registry.REGISTRY[model_id]["contract"]
    base = dict(model_registry.REGISTRY[model_id]["example"] or {})  # valid inputs; one parameter is altered at a time
    validate_inputs(contract, base)
    for p in contract["parameters"]:
        if p["type"] not in ("number", "integer"):
            continue
        if "maximum" in p:
            with pytest.raises(ContractError) as exc:
                validate_inputs(contract, {**base, p["name"]: p["maximum"] * 10 + 10})
            assert exc.value.code == "out_of_range"
        if "minimum" in p:
            with pytest.raises(ContractError) as exc:
                validate_inputs(contract, {**base, p["name"]: p["minimum"] - 1 if not p.get("exclusive_minimum") else p["minimum"]})
            assert exc.value.code == "out_of_range"
        with pytest.raises(ContractError) as exc:
            validate_inputs(contract, {**base, p["name"]: "12"})
        assert exc.value.code == "invalid_type"


def test_unknown_missing_and_enum_errors_have_stable_codes():
    rc = model_registry.get_contract("rc_rl_step_response")
    for bad, code in (({"resistence_ohm": 10}, "unknown_parameter"), ({"kind": "LC"}, "invalid_choice"), ({"points": 10.5}, "invalid_type"), ({"points": True}, "invalid_type")):
        with pytest.raises(ContractError) as exc:
            validate_inputs(rc, bad)
        assert exc.value.code == code
    with pytest.raises(ContractError) as exc:
        validate_inputs(model_registry.get_contract("mass_action_kinetics"), {"species": [], "reactions": []})
    assert exc.value.code == "missing_parameter"


def test_check_contract_detects_malformed_definitions():
    bad = {"id": "x", "version": "1", "title": "t", "domain": "d", "assumptions": [], "validity": [], "error_codes": [], "references": [],
           "parameters": [{"name": "a", "type": "number", "default": 5, "maximum": 1}, {"name": "a", "type": "weird"}], "outputs": [{"name": "o", "path": "o"}]}
    problems = " | ".join(check_contract(bad))
    for fragment in ("without unit", "violates its own bounds", "duplicated", "invalid type", "missing unit"):
        assert fragment in problems


ENGINE_MODULES = ["electrical_circuits.py", "workbench_circuit.py", "electrical_advanced.py", "chemical_kinetics.py", "reaction_stoichiometry.py", "models.py",
                  "virtual_instruments.py", "linked_measurements.py", "contracts.py"]


@pytest.mark.parametrize("module", ENGINE_MODULES)
def test_engines_do_not_depend_on_interface_or_persistence(module):
    tree = ast.parse((ROOT / module).read_text(encoding="utf-8"))
    imported = {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
               {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not imported & {"app", "history", "sqlite3", "http", "experiment_service", "urllib"}, imported


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v50.sqlite3")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def call(url, body=None):
    req = urllib.request.Request(url, data=None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode()), method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_contract_api_and_standard_run(base):
    code, listing = call(base + "/api/contracts")
    assert code == 200 and len(listing["contracts"]) == len(IDS)
    assert call(base + "/api/contracts/series_rlc_ac")[1]["parameters"][0]["unit"] == "V"
    code, env = call(base + "/api/models/series_rlc_ac/run", {"inputs": {"frequency_hz": 1591.549}})
    assert code == 200 and env["outputs"]["power_factor"]["value"] == pytest.approx(1.0, abs=1e-4)
    assert call(base + "/api/models/nope/run", {"inputs": {}})[1]["error_code"] == "unknown_model"
    code, err = call(base + "/api/models/series_rlc_ac/run", {"inputs": {"frequency_hz": -5}})
    assert code == 400 and err["error_code"] == "out_of_range" and err["error_params"]["name"] == "frequency_hz"


@pytest.mark.parametrize("path,body", [("/api/models/series_rlc_ac/run", b"[1]"), ("/api/electrical/workbench-run", {"components": []}),
                                       ("/api/chemistry/kinetics-run", {"species": "x"}), ("/api/history/999/verify", None), ("/api/nowhere", None),
                                       ("/api/electrical/dc-solve", b"{bad"), ("/api/history/abc", None), ("/api/contracts/unknown", None)])
def test_every_error_response_has_a_stable_code(base, path, body):
    code, err = call(base + path, body)
    assert code >= 400 and isinstance(err.get("error_code"), str) and err["error"]
