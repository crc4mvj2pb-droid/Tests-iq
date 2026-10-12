"""v4.1: verify configuration integrity and replay saved DC workbench circuits."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import app
import history
from experiment_lifecycle import configuration_hash, verify_dossier_integrity


def test_canonical_configuration_hash_is_order_independent():
    a = {"components": [{"id": "resistor", "qty": 1000}], "connections": []}
    b = {"connections": [], "components": [{"qty": 1000, "id": "resistor"}]}
    assert configuration_hash(a) == configuration_hash(b)
    assert len(configuration_hash(a)) == 64


def test_integrity_check_detects_changed_configuration():
    config = {"components": [], "connections": []}
    dossier = {"configuration": config, "configuration_hash": configuration_hash(config)}
    assert verify_dossier_integrity(dossier)["valid"] is True
    dossier["configuration"]["components"].append({"id": "resistor"})
    assert verify_dossier_integrity(dossier)["valid"] is False


def test_non_json_finite_configuration_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        configuration_hash({"x": float("nan")})


def test_api_verify_and_replay_saved_workbench_circuit(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v41.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    request_data = {
        "name": "v4.1 replay test", "question": "Ohm's law",
        "components": [
            {"instanceId": "S", "id": "dc-source", "qty": 9, "displayName": "Source"},
            {"instanceId": "G", "id": "ground", "qty": 0, "displayName": "Ground"},
            {"instanceId": "R1", "id": "resistor", "qty": 1000, "displayName": "R1"},
        ],
        "connections": [
            {"a": "S", "pinA": "P", "b": "R1", "pinB": "A"},
            {"a": "R1", "pinA": "B", "b": "G", "pinB": "GND"},
            {"a": "S", "pinA": "N", "b": "G", "pinB": "GND"},
        ],
    }
    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=4) as response:
            return json.load(response)
    try:
        first = post("/api/electrical/workbench-run", request_data)
        original_id = first["history_record"]["id"]
        with urllib.request.urlopen(base + f"/api/history/{original_id}/verify", timeout=4) as response:
            integrity = json.load(response)
        assert integrity["valid"] is True
        replay = post(f"/api/history/{original_id}/replay", {})
        assert replay["replay_of"] == original_id
        assert replay["history_record"]["id"] != original_id
        assert replay["configuration_hash"] == first["configuration_hash"]
        assert abs(replay["source_current_a"] - first["source_current_a"]) < 1e-12
        with urllib.request.urlopen(base + "/api/history", timeout=4) as response:
            listed = json.load(response)["experiments"]
        assert len([x for x in listed if x["model_id"] == "electrical_workbench_dc"]) == 2
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


def test_replay_endpoint_rejects_non_circuit_dossiers(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v41_non_circuit.sqlite3")
    dossier = {"model_id": "not_a_circuit", "title": "Other", "configuration": {}, "configuration_hash": configuration_hash({}), "status": "completed"}
    saved = history.save_experiment(dossier)
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/history/{saved['id']}/replay", data=b"{}", headers={"Content-Type":"application/json"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=4)
            assert False, "Expected HTTP 400"
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


def test_frontend_exposes_verify_and_replay_controls():
    from pathlib import Path
    html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")
    assert "data-history-verify" in html
    assert "data-history-replay" in html
    assert "/verify" in html and "/replay" in html
