"""v9.0 — validated configuration; consistent backups, verification and restore of the local data."""
from __future__ import annotations

import io
import json
import sqlite3
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import app
import config
import experiment_service
import history
import maintenance
import scientific_imports

KINETICS = {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
            "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5}], "duration": 1.0, "dt": 0.1}


def test_configuration_precedence_and_validation(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"port": 9000, "backup_keep": 3}), encoding="utf-8")
    c = config.load({"VIRTUAL_LAB_PORT": "9100"}, str(cfg))
    assert c["port"] == 9100 and c["sources"]["port"] == "environment VIRTUAL_LAB_PORT" and c["backup_keep"] == 3 and c["host"] == "127.0.0.1"
    assert config.load({}, str(tmp_path / "missing.json"))["port"] == 8765
    cfg.write_text(json.dumps({"port": 80, "colour": "blue", "max_request_bytes": "big"}), encoding="utf-8")
    with pytest.raises(config.ConfigError) as exc:
        config.load({}, str(cfg))
    text = " ".join(exc.value.problems)
    assert "unknown setting 'colour'" in text and "port" in text and "max_request_bytes" in text
    assert "/" not in json.dumps(config.public(config.load({}, str(tmp_path / "none.json")))["db_path"])  # no directory exposed


def test_invalid_configuration_stops_the_start_up(tmp_path):
    proc = subprocess.run([sys.executable, "app.py"], cwd=Path(app.__file__).parent, env={"VIRTUAL_LAB_PORT": "12", "PATH": ""}, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 2 and "invalid configuration" in proc.stdout and "port" in proc.stdout


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "h.sqlite3")
    assets = tmp_path / "assets"
    (assets / "datasets").mkdir(parents=True)
    (assets / "index.json").write_text('{"schema_version": "1.0", "assets": []}', encoding="utf-8")
    (assets / "datasets" / "x.csv").write_text("t (s),y\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(scientific_imports, "ASSET_DIR", assets)
    monkeypatch.setattr(maintenance, "backup_dir", lambda: tmp_path / "backups")
    return tmp_path


def test_backup_verify_restore_roundtrip(data):
    for _ in range(2):
        experiment_service.run_kinetics(KINETICS)
    b = maintenance.create_backup("test")
    assert b["experiments"] == 2 and maintenance.verify_backup(data / "backups" / b["file"])["valid"]
    experiment_service.run_kinetics(KINETICS)  # a third experiment after the backup
    (data / "assets" / "datasets" / "x.csv").write_text("changed", encoding="utf-8")
    r = maintenance.restore_backup(data / "backups" / b["file"])
    assert r["experiments"] == 2 and (data / "assets" / "datasets" / "x.csv").read_text() == "t (s),y\n1,2\n"
    pre = maintenance.verify_backup(data / "backups" / r["pre_restore_backup"])
    assert pre["valid"] and pre["experiments"] == 3  # the replaced state is kept


def test_altered_backup_is_refused_and_nothing_changes(data):
    experiment_service.run_kinetics(KINETICS)
    b = data / "backups" / maintenance.create_backup("t")["file"]
    altered = data / "backups" / "virtual_lab_backup_altered.zip"
    with zipfile.ZipFile(b) as src, zipfile.ZipFile(altered, "w") as dst:
        for name in src.namelist():
            content = src.read(name)
            if name.endswith("x.csv"):
                content = b"tampered"
            dst.writestr(name, content)
    experiment_service.run_kinetics(KINETICS)
    with pytest.raises(maintenance.BackupError) as exc:
        maintenance.restore_backup(altered)
    assert exc.value.code == "invalid_backup" and maintenance.integrity_check()["experiments"] == 2


def test_corrupted_database_is_detected(data):
    experiment_service.run_kinetics(KINETICS)
    raw = bytearray(history.DB_PATH.read_bytes())
    raw[200:4000] = b"\x00" * 3800
    history.DB_PATH.write_bytes(bytes(raw))
    assert maintenance.integrity_check()["ok"] is False


def test_backup_is_consistent_while_writes_happen(data):
    experiment_service.run_kinetics(KINETICS)
    stop = threading.Event()

    def writer():
        while not stop.is_set():
            experiment_service.run_kinetics(KINETICS)
    t = threading.Thread(target=writer); t.start()
    try:
        backups = [maintenance.create_backup(f"c{i}") for i in range(3)]
    finally:
        stop.set(); t.join()
    assert all(maintenance.verify_backup(data / "backups" / b["file"])["valid"] for b in backups)


def test_prune_keeps_the_most_recent(data):
    for i in range(4):
        maintenance.create_backup(f"p{i}")
    removed = maintenance.prune(2)
    assert len(removed) == 2 and len(maintenance.list_backups()) == 2


def test_api_refuses_paths_and_restores_listed_files(data):
    experiment_service.run_kinetics(KINETICS)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())
    try:
        code, made = post("/api/admin/backup", {"label": "api"})
        code_v, verified = post("/api/admin/backup/verify", {"file": made["file"]})
        code_t, traversal = post("/api/admin/backup/restore", {"file": "../h.sqlite3"})
        with urllib.request.urlopen(base + "/api/admin/integrity", timeout=10) as resp:
            integrity = json.loads(resp.read())
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert code == 200 and verified["valid"] and code_t == 404 and traversal["error_code"] == "unknown_backup" and integrity["ok"]


def test_command_line(data):
    experiment_service.run_kinetics(KINETICS)
    assert maintenance.main(["maintenance.py", "check"]) == 0
    assert maintenance.main(["maintenance.py", "backup"]) == 0 and len(maintenance.list_backups()) == 1
