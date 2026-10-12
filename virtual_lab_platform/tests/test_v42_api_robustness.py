"""v4.2 — HTTP robustness: lab run, malformed bodies, optional replay body, logged 500s."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import history
from lab_designer import CATALOG


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v42.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


def call(url, data=None, method="POST"):
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def lab_request():
    wf = next(x for x in CATALOG["workflows"] if x["id"] == "solution_dilution")
    return {"name": "v42 dilution", "workflow_id": "solution_dilution", "discipline": wf["discipline"],
            "components": wf["required_components"][:],
            "equipment": wf["required_equipment"][:] + [g[0] for g in wf.get("required_equipment_options", [])],
            "steps": [{"action": "Prepare"}], "protocol_steps": [{"id": "s1", "action": "Prepare dilution", "duration_s": 0}],
            "parameters": {"stock_concentration_mM": 10, "stock_volume_ml": 0.5, "diluent_volume_ml": 9.5}}


REFERENCE = {"components": [{"instanceId": "s", "id": "dc-source", "displayName": "S", "qty": 9},
                            {"instanceId": "r", "id": "resistor", "displayName": "R1", "qty": 1000},
                            {"instanceId": "g", "id": "ground", "displayName": "GND", "qty": 0}],
             "connections": [{"a": "s", "pinA": "P", "b": "r", "pinB": "A"}, {"a": "r", "pinA": "B", "b": "g", "pinB": "GND"},
                             {"a": "s", "pinA": "N", "b": "g", "pinB": "GND"}]}


def test_lab_run_succeeds_and_is_saved(base):
    code, body = call(base + "/api/lab/run", json.dumps(lab_request()).encode())
    assert code == 200, body
    assert body["history_record"]["id"] >= 1
    assert body["configuration"]["workflow_id"] == "solution_dilution"
    code, verify = call(f"{base}/api/history/{body['history_record']['id']}/verify", method="GET")
    assert code == 200 and verify["valid"] is True


@pytest.mark.parametrize("raw", [b"[1,2]", b'"text"', b"42", b"null"])
def test_non_object_json_body_is_rejected_with_400(base, raw):
    code, body = call(base + "/api/electrical/workbench-run", raw)
    assert code == 400
    assert "JSON object" in body["error"]


def test_missing_body_is_400_not_413(base):
    code, body = call(base + "/api/electrical/workbench-run", b"")
    assert code == 400 and "missing" in body["error"]


def test_replay_accepts_an_empty_body(base):
    code, first = call(base + "/api/electrical/workbench-run", json.dumps(REFERENCE).encode())
    assert code == 200
    code, replay = call(f"{base}/api/history/{first['history_record']['id']}/replay", b"")
    assert code == 200 and replay["replay_of"] == first["history_record"]["id"]


def test_workbench_errors_expose_stable_codes(base):
    bad = json.loads(json.dumps(REFERENCE)); bad["connections"].append({"a": "s", "pinA": "P", "b": "g", "pinB": "GND"})
    code, body = call(base + "/api/electrical/workbench-run", json.dumps(bad).encode())
    assert code == 400 and body["error_code"] == "source_short"


def test_internal_errors_are_logged_but_not_exposed(base, monkeypatch, capfd):
    def boom(_request):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(app, "solve_dc_circuit", boom)
    code, body = call(base + "/api/electrical/dc-solve", b"{}")
    assert code == 500 and "secret" not in body["error"]
    assert "RuntimeError: secret internal detail" in capfd.readouterr().err


def test_single_version_is_reported_everywhere(base):
    from pathlib import Path
    from version import APP_VERSION
    assert call(base + "/api/health", method="GET")[1]["version"] == APP_VERSION
    assert call(base + "/api/version", method="GET")[1]["version"] == APP_VERSION
    html = (Path(app.__file__).resolve().parent / "static" / "index.html").read_text(encoding="utf-8")
    assert f"<title>Virtual Lab Platform v{APP_VERSION}</title>" in html
    assert f"Virtual Lab Platform v{APP_VERSION} ·" in html
