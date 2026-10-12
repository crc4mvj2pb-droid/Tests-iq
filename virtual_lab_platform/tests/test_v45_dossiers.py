"""v4.5 — unified dossiers, full integrity, replay comparison, SQLite migration, export/import."""
from __future__ import annotations

import json
import shutil
import sqlite3
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import app
import experiment_service
import history
from lab_designer import CATALOG

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "v41_history.sqlite3"
CIRCUIT = {"name": "diviseur", "components": [{"instanceId": "s", "id": "dc-source", "displayName": "S", "qty": 12},
           {"instanceId": "r1", "id": "resistor", "displayName": "R1", "qty": 1000}, {"instanceId": "r2", "id": "resistor", "displayName": "R2", "qty": 2000},
           {"instanceId": "g", "id": "ground", "displayName": "G", "qty": 0}],
           "connections": [{"a": "s", "pinA": "P", "b": "r1", "pinB": "A"}, {"a": "r1", "pinA": "B", "b": "r2", "pinB": "A"},
                           {"a": "r2", "pinA": "B", "b": "g", "pinB": "GND"}, {"a": "s", "pinA": "N", "b": "g", "pinB": "GND"}]}


@pytest.fixture
def server(tmp_path, monkeypatch):
    db = tmp_path / "v45.sqlite3"
    monkeypatch.setattr(history, "DB_PATH", db)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def call(path, body=None, method=None):
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        req = urllib.request.Request(base + path, data=data, method=method or ("POST" if data is not None else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())
    call.db = db
    try:
        yield call
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def lab_request():
    wf = next(x for x in CATALOG["workflows"] if x["id"] == "solution_dilution")
    return {"name": "dilution", "workflow_id": "solution_dilution", "discipline": wf["discipline"], "components": wf["required_components"][:],
            "equipment": wf["required_equipment"][:] + [g[0] for g in wf.get("required_equipment_options", [])], "steps": [{"action": "Prepare"}],
            "protocol_steps": [{"id": "s1", "action": "Prepare dilution", "duration_s": 0}],
            "parameters": {"stock_concentration_mM": 10, "stock_volume_ml": 0.5, "diluent_volume_ml": 9.5}}


SAVING = [
    ("/api/electrical/workbench-run", lambda: CIRCUIT, "electrical_workbench_dc"),
    ("/api/experiments", lambda: {"name": "enzyme", "question": "Km?", "model_id": "enzyme_kinetics", "parameters": {"vmax": 1.2, "km": 0.8, "s_max": 2.0, "points": 5}}, "enzyme_kinetics"),
    ("/api/protocol/run", lab_request, "structured_protocol"),
    ("/api/lab/run", lab_request, "solution_dilution"),
]


@pytest.mark.parametrize("path,body,model_id", SAVING)
def test_every_saving_endpoint_writes_a_fully_verifiable_schema2_dossier(server, path, body, model_id):
    code, d = server(path, body())
    assert code == 200, d
    assert d["dossier_schema_version"] == 2 and d["model_id"] == model_id and d["engine"]["version"] and d["app_version"]
    listed = server("/api/history")[1]["experiments"][0]
    assert listed["model_id"] == model_id and listed["dossier_schema_version"] == 2
    code, v = server(f"/api/history/{d['history_record']['id']}/verify")
    assert v["valid"] is True and v["level"] == "full", v


def _tamper(db, record_id, mutate, column=None):
    conn = sqlite3.connect(db)
    if column:
        conn.execute(f"UPDATE experiments SET {column}='0000' WHERE id=?", (record_id,))
    else:
        dossier = json.loads(conn.execute("SELECT dossier_json FROM experiments WHERE id=?", (record_id,)).fetchone()[0])
        mutate(dossier)
        conn.execute("UPDATE experiments SET dossier_json=? WHERE id=?", (json.dumps(dossier), record_id))
    conn.commit(); conn.close()


def test_modified_results_are_detected_and_replay_refused(server):
    record = server("/api/electrical/workbench-run", CIRCUIT)[1]["history_record"]["id"]
    _tamper(server.db, record, lambda d: d.__setitem__("source_current_a", 123.0))
    v = server(f"/api/history/{record}/verify")[1]
    assert v["valid"] is False and any(c["check"] == "dossier_hash" and not c["passed"] for c in v["checks"])
    assert server(f"/api/history/{record}/replay", b"")[0] == 409


def test_index_column_mismatch_is_detected(server):
    record = server("/api/electrical/workbench-run", CIRCUIT)[1]["history_record"]["id"]
    _tamper(server.db, record, None, column="configuration_hash")
    v = server(f"/api/history/{record}/verify")[1]
    assert v["valid"] is False and any(c["check"] == "index_configuration_hash" and not c["passed"] for c in v["checks"])


def test_replay_compares_results_and_reports_engine_versions(server):
    record = server("/api/electrical/workbench-run", CIRCUIT)[1]["history_record"]["id"]
    code, replay = server(f"/api/history/{record}/replay", b"")
    comparison = replay["replay_comparison"]
    assert code == 200 and comparison["identical_within_tolerance"] and comparison["compared_values"] == 6
    assert comparison["engine_changed"] is False and replay["replay_of"] == record
    assert server(f"/api/history/{replay['history_record']['id']}/verify")[1]["level"] == "full"


def test_replay_reports_differences_when_the_engine_output_changes(server, monkeypatch):
    record = server("/api/electrical/workbench-run", CIRCUIT)[1]["history_record"]["id"]
    run, compare, engine = experiment_service.REPLAYERS["electrical_workbench_dc"]

    def drifted(config):
        result = run(config)
        result["node_voltages_v"] = {k: v * 1.001 for k, v in result["node_voltages_v"].items()}
        return result
    monkeypatch.setitem(experiment_service.REPLAYERS, "electrical_workbench_dc", (drifted, compare, ("workbench_dc", "test-drift")))
    comparison = server(f"/api/history/{record}/replay", b"")[1]["replay_comparison"]
    assert comparison["identical_within_tolerance"] is False and comparison["engine_changed"] is True
    assert any(diff["quantity"].startswith("V(") for diff in comparison["differences"])


def test_v41_database_is_migrated_with_backup_and_without_rewriting_dossiers(tmp_path, monkeypatch):
    db = tmp_path / "virtual_lab_history.sqlite3"
    shutil.copy(FIXTURE, db)
    before = sqlite3.connect(db).execute("SELECT id, dossier_json FROM experiments ORDER BY id").fetchall()
    monkeypatch.setattr(history, "DB_PATH", db)
    history.initialize()
    backups = list(tmp_path.glob("virtual_lab_history.sqlite3.backup-schema-1-*"))
    assert len(backups) == 1
    assert sqlite3.connect(backups[0]).execute("SELECT id, dossier_json FROM experiments ORDER BY id").fetchall() == before
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT id, dossier_json FROM experiments ORDER BY id").fetchall() == before  # dossiers untouched
    rows = {r[0]: r[1:] for r in conn.execute("SELECT id, model_id, title, configuration_hash FROM experiments")}
    assert rows[3][0] == "enzyme_kinetics" and rows[3][1] == "enzyme v4.1" and rows[3][2]  # the legacy "unknown" row is repaired
    history.initialize()  # idempotent: no second backup, no error
    assert len(list(tmp_path.glob("virtual_lab_history.sqlite3.backup-schema-1-*"))) == 1
    levels = {i: experiment_service.verify(i)["level"] for i in (1, 2, 3, 4)}
    assert levels == {1: "configuration_only", 2: "configuration_only", 3: "configuration_only", 4: "unverifiable"}
    assert all(experiment_service.verify(i)["valid"] for i in (1, 2, 3))


def test_legacy_v41_circuit_replays_identically_with_the_v44_engine(tmp_path, monkeypatch):
    db = tmp_path / "virtual_lab_history.sqlite3"
    shutil.copy(FIXTURE, db)
    monkeypatch.setattr(history, "DB_PATH", db)
    replay = experiment_service.replay(1)
    comparison = replay["replay_comparison"]
    assert comparison["identical_within_tolerance"] and comparison["engine_changed"] is True
    assert comparison["engine_original"]["version"] == "pre-v4.5"


def test_history_export_import_round_trip_is_lossless_and_idempotent(server, tmp_path, monkeypatch):
    for path, body, _ in SAVING:
        server(path, body())
    exported = server("/api/history/export")[1]
    assert exported["format"] == "virtual-lab-history" and exported["record_count"] == 4
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "fresh.sqlite3")
    code, result = server("/api/history/import", exported)
    assert code == 200 and result["imported_count"] == 4
    for entry, item in zip(exported["records"], result["imported"]):
        restored = server(f"/api/history/{item['new_id']}")[1]
        original = {k: v for k, v in entry["dossier"].items() if k != "history_record"}
        assert {k: v for k, v in restored.items() if k != "imported_from"} == original
        assert server(f"/api/history/{item['new_id']}/verify")[1]["level"] == "full"
    again = server("/api/history/import", exported)[1]
    assert again["imported_count"] == 0 and again["skipped_count"] == 4


def test_altered_export_is_refused_entirely(server, tmp_path, monkeypatch):
    server("/api/electrical/workbench-run", CIRCUIT); server("/api/electrical/workbench-run", CIRCUIT)
    exported = server("/api/history/export")[1]
    exported["records"][1]["dossier"]["branches"][0]["current_a"] = 1.0
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "fresh.sqlite3")
    code, body = server("/api/history/import", exported)
    assert code == 409 and body["rejected"][0]["position"] == 2
    assert server("/api/history")[1]["experiments"] == []


def test_single_dossier_export_and_unknown_formats(server, tmp_path, monkeypatch):
    record = server("/api/electrical/workbench-run", CIRCUIT)[1]["history_record"]["id"]
    one = server(f"/api/history/{record}/export")[1]
    assert one["format"] == "virtual-lab-dossier"
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "fresh.sqlite3")
    assert server("/api/history/import", one)[1]["imported_count"] == 1
    assert server("/api/history/import", {"format": "something-else", "format_version": 1})[0] == 400
    assert server("/api/history/import", {**one, "format_version": 99})[0] == 400


def test_legacy_export_imports_at_configuration_level(tmp_path, monkeypatch):
    db = tmp_path / "virtual_lab_history.sqlite3"; shutil.copy(FIXTURE, db)
    monkeypatch.setattr(history, "DB_PATH", db)
    exported = experiment_service.export_all()
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "fresh.sqlite3")
    with pytest.raises(experiment_service.ServiceError) as exc:  # the v4.1 protocol dossier has no hash at all
        experiment_service.import_bundle(exported)
    assert exc.value.status == 409 and exc.value.details["rejected"][0]["original_id"] == 4
    exported["records"] = exported["records"][:3]
    result = experiment_service.import_bundle(exported)
    assert [x["verification_level"] for x in result["imported"]] == ["configuration_only"] * 3


def test_hash_survives_a_javascript_style_json_round_trip(server):
    # JavaScript writes 9.0 as 9 and -0.0 as 0: re-serializing must not break the integrity check.
    from dossier import verify_dossier
    d = server("/api/electrical/workbench-run", CIRCUIT)[1]
    def js_like(value):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, dict):
            return {k: js_like(v) for k, v in value.items()}
        if isinstance(value, list):
            return [js_like(v) for v in value]
        return value
    assert any(isinstance(v, float) and v.is_integer() for v in d["node_voltages_v"].values())  # the case actually occurs
    assert verify_dossier(js_like(d))["valid"] is True
