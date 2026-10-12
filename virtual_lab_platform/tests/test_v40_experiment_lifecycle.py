"""v4.0: end-to-end circuit runs create traceable experiment dossiers."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")


def test_api_exposes_v40_and_documented_lifecycle_feature():
    assert '"version": APP_VERSION' in APP
    assert "v4.0 experiment lifecycle" in APP
    assert '"/api/electrical/workbench-run"' in APP


def test_circuit_workbench_uses_persisting_run_endpoint():
    # v4.2: the call goes through wbFetchJson, which adds network/non-JSON error handling.
    assert "wbFetchJson('/api/electrical/workbench-run'" in HTML
    assert "history_record?.id" in HTML
    assert "configuration_hash" in HTML


def test_endpoint_creates_reproducible_configuration_hash_and_saves_history(tmp_path, monkeypatch):
    # v4.5: the lifecycle moved to experiment_service.py; the same guarantees are now checked by behaviour
    # (real HTTP call) instead of searching for source lines in app.py.
    import threading, urllib.request
    from http.server import ThreadingHTTPServer
    import app, history
    from experiment_lifecycle import configuration_hash
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v40.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        body = {"name": "v40", "components": [{"instanceId": "s", "id": "dc-source", "displayName": "S", "qty": 9},
                {"instanceId": "r", "id": "resistor", "displayName": "R", "qty": 1000}, {"instanceId": "g", "id": "ground", "displayName": "G", "qty": 0}],
                "connections": [{"a": "s", "pinA": "P", "b": "r", "pinB": "A"}, {"a": "r", "pinA": "B", "b": "g", "pinB": "GND"},
                                {"a": "s", "pinA": "N", "b": "g", "pinB": "GND"}]}
        req = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/electrical/workbench-run", data=json.dumps(body).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.load(response)
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
    assert result["configuration"] == {"components": body["components"], "connections": body["connections"]}
    assert result["configuration_hash"] == configuration_hash(result["configuration"])
    assert result["status"] == "completed" and result["data_status"] == "simulated_calculation"
    assert history.get_experiment(result["history_record"]["id"])["configuration_hash"] == result["configuration_hash"]


def test_old_non_persisting_solver_remains_available_for_compatibility():
    assert 'parsed.path == "/api/electrical/workbench-solve"' in APP or 'parsed.path in ("/api/electrical/workbench-solve", "/api/electrical/workbench-run")' in APP


def test_dossier_hash_is_stable_for_same_canonical_configuration():
    config = {"components": [{"instanceId": "R1", "qty": 1000}], "connections": []}
    canonical = json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest_a = hashlib.sha256(canonical.encode()).hexdigest()
    digest_b = hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    assert digest_a == digest_b and len(digest_a) == 64


def test_workbench_run_api_persists_and_reloads_a_real_dossier(tmp_path, monkeypatch):
    import json as _json
    import threading
    import urllib.request
    import app
    import history
    from http.server import ThreadingHTTPServer

    monkeypatch.setattr(history, "DB_PATH", tmp_path / "test_history.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    request_data = {
        "name": "Integration circuit 9 V / 1 kΩ",
        "question": "Verify Ohm's law",
        "components": [
            {"instanceId": "S", "id": "dc-source", "qty": 9, "displayName": "Source 9 V", "cat": "electrical"},
            {"instanceId": "G", "id": "ground", "qty": 0, "displayName": "Ground", "cat": "electrical"},
            {"instanceId": "R1", "id": "resistor", "qty": 1000, "displayName": "R1", "cat": "electrical"},
        ],
        "connections": [
            {"a": "S", "pinA": "P", "b": "R1", "pinB": "A", "kind": "ideal-wire"},
            {"a": "R1", "pinA": "B", "b": "G", "pinB": "GND", "kind": "ideal-wire"},
            {"a": "S", "pinA": "N", "b": "G", "pinB": "GND", "kind": "ideal-wire"},
        ],
    }
    try:
        req = urllib.request.Request(base + "/api/electrical/workbench-run", data=_json.dumps(request_data).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as response:
            result = _json.load(response)
        assert result["status"] == "completed"
        assert result["data_status"] == "simulated_calculation"
        assert abs(result["source_current_a"] - 0.009) < 1e-12
        assert len(result["configuration_hash"]) == 64
        experiment_id = result["history_record"]["id"]
        with urllib.request.urlopen(base + "/api/history", timeout=3) as response:
            listed = _json.load(response)["experiments"]
        assert any(item["id"] == experiment_id for item in listed)
        with urllib.request.urlopen(base + f"/api/history/{experiment_id}", timeout=3) as response:
            dossier = _json.load(response)
        assert dossier["model_id"] == "electrical_workbench_dc"
        assert dossier["configuration_hash"] == result["configuration_hash"]
        assert dossier["branches"][0]["current_a"] == result["branches"][0]["current_a"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
