"""v9.2 — observability, diagnostics and recovery after a failure."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import app
import experiment_service
import history
import maintenance
import observability

KINETICS = {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
            "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5}], "duration": 1.0, "dt": 0.1}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "h.sqlite3")
    monkeypatch.setattr(maintenance, "backup_dir", lambda: tmp_path / "backups")
    monkeypatch.setitem(observability.LOG, "path", None)
    observability.leave_recovery()
    yield tmp_path
    observability.leave_recovery()


@pytest.fixture
def base(env):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_request_log_has_no_body_parameters_or_client_address(base):
    post(base + "/api/electrical/dc-solve", {"source_voltage": 12.345678, "resistors": []})
    entry = list(observability.RECENT)[-1]
    assert entry["path"] == "/api/electrical/dc-solve" and entry["status"] == 400 and entry["error_code"]
    assert "12.345678" not in json.dumps(list(observability.RECENT)) and set(entry) == {"at_utc", "method", "path", "status", "error_code", "duration_ms"}


def test_log_file_rotation(env, monkeypatch):
    observability.configure_log(env / "logs", 10_000)
    for i in range(400):
        observability.record("GET", f"/api/health?x={i}", 200, None, 1.0)
    files = sorted(p.name for p in (env / "logs").iterdir())
    assert "requests.jsonl" in files and "requests.jsonl.1" in files and len(files) <= 4
    assert all("?" not in json.loads(line)["path"] for line in (env / "logs" / "requests.jsonl").read_text().splitlines())


def test_diagnostics_describe_the_installation(base):
    experiment_service.run_kinetics(KINETICS)
    with urllib.request.urlopen(base + "/api/diagnostics", timeout=20) as r:
        d = json.loads(r.read())
    assert d["database"]["ok"] and d["database"]["experiments"] == 1 and d["recovery_mode"]["active"] is False
    assert d["app_version"] and d["python"] and "disk_free_bytes" in d and d["requests"]["requests"] >= 1
    assert "/home/" not in json.dumps(d)  # no personal path


def test_recovery_mode_refuses_writes_but_allows_restore(base, env):
    experiment_service.run_kinetics(KINETICS)
    backup = maintenance.create_backup("good")
    observability.enter_recovery("database integrity check failed (test)")
    code, body = post(base + "/api/chemistry/kinetics-run", KINETICS)
    assert code == 503 and body["error_code"] == "recovery_mode"
    code, restored = post(base + "/api/admin/backup/restore", {"file": backup["file"]})
    assert code == 200 and restored["experiments"] == 1 and observability.RECOVERY["active"] is False
    assert post(base + "/api/chemistry/kinetics-run", KINETICS)[0] == 200


def test_startup_backup_only_when_needed(env):
    experiment_service.run_kinetics(KINETICS)
    first = observability.startup_backup()
    assert first is not None and observability.startup_backup() is None  # a recent backup exists
    assert observability.startup_backup(max_age_hours=0) is not None


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_server_starts_in_recovery_mode_with_a_damaged_database(env):
    db = env / "damaged.sqlite3"
    db.write_bytes(b"SQLite format 3\x00" + b"\xff" * 4096)
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "app.py"], cwd=Path(app.__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env={**{k: v for k, v in os.environ.items() if not k.startswith("VIRTUAL_LAB")}, "VIRTUAL_LAB_DB": str(db), "VIRTUAL_LAB_PORT": str(port),
                                 "VIRTUAL_LAB_BACKUP_DIR": str(env / "b"), "VIRTUAL_LAB_LOG_DIR": str(env / "l")})
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/diagnostics", timeout=2) as r:
                    d = json.loads(r.read())
                break
            except OSError:
                time.sleep(0.1)
        code, body = post(f"http://127.0.0.1:{port}/api/chemistry/kinetics-run", KINETICS)
    finally:
        proc.terminate(); out = proc.communicate(timeout=10)[0]
    assert d["recovery_mode"]["active"] and code == 503 and "RECOVERY MODE" in out
    assert not (env / "b").exists() or not list((env / "b").glob("*.zip"))  # no automatic backup of a damaged database
