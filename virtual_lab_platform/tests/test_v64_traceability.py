"""v6.4 — traceability: event journal, environment, seeds, reproducible package checked by a third-party run."""
from __future__ import annotations

import io
import json
import os
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
import data_import
import experiment_service
import history
import scientific_imports
import trace_package

KINETICS = {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
            "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5}], "duration": 4.0, "dt": 0.1}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v64.sqlite3")
    library = tmp_path / "scientific_library" / "imported_assets"
    library.mkdir(parents=True)
    monkeypatch.setattr(scientific_imports, "BASE", tmp_path)
    monkeypatch.setattr(scientific_imports, "ASSET_DIR", library)
    monkeypatch.setattr(scientific_imports, "INDEX", library / "index.json")
    return tmp_path


def third_party_run(package: bytes, where: Path) -> tuple[int, dict, str]:
    """Extract the package in an empty directory and run reproduce.py in isolated mode (no access to this repository)."""
    where.mkdir()
    with zipfile.ZipFile(io.BytesIO(package)) as zf:
        zf.extractall(where)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "VIRTUAL_LAB"))}
    proc = subprocess.run([sys.executable, "-I", "reproduce.py"], cwd=where, env=env, capture_output=True, text=True, timeout=300)
    report = json.loads((where / "reproduction_report.json").read_text(encoding="utf-8")) if (where / "reproduction_report.json").exists() else {}
    return proc.returncode, report, proc.stdout + proc.stderr


def test_lifecycle_events_are_journalled(isolated):
    d = experiment_service.run_kinetics(KINETICS)
    eid = d["history_record"]["id"]
    experiment_service.verify(eid)
    experiment_service.replay(eid)
    experiment_service.export_one(eid)
    names = [e["event"] for e in trace_package.events(eid)]
    assert names == ["saved", "verified", "replayed", "exported"]
    saved = trace_package.events(eid)[0]["details"]
    assert saved["model_id"] == "chemical_kinetics_network" and saved["engine"]["version"] and saved["configuration_hash"] == d["configuration_hash"]


def test_environment_and_seeds_are_recorded():
    env = trace_package.environment()
    assert env["python"] and env["app_version"] and env["engines"]["nonlinear_least_squares"] and env["third_party_packages"].startswith("none")
    assert not any(k in json.dumps(env).lower() for k in ("/home/", "user", "hostname"))  # no personal data or paths
    assert trace_package.seeds({"a": {"seed": 7}, "runs": [{"seed": 3}], "x": 1}) == {"a.seed": 7, "runs.0.seed": 3}


def test_package_manifest_detects_any_change(isolated):
    d = experiment_service.run_kinetics(KINETICS)
    package, manifest = trace_package.build_package(d["history_record"]["id"])
    assert trace_package.verify_package(package)["valid"] and manifest["scope"].startswith("integrity")
    names = {f["path"] for f in manifest["files"]}
    assert {"dossier.json", "reproduce.py", "environment.json", "events.json", "platform/chemical_kinetics.py", "platform/experiment_service.py"} <= names
    assert not any(n.endswith(".sqlite3") or "imported_assets" in n for n in names)
    altered = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(package)) as src, zipfile.ZipFile(altered, "w") as dst:
        for item in src.namelist():
            content = src.read(item)
            if item == "dossier.json":
                content = content.replace(b'"rate_constant": 0.5', b'"rate_constant": 0.6')
            dst.writestr(item, content)
    report = trace_package.verify_package(altered.getvalue())
    assert not report["valid"] and report["altered"] == ["dossier.json"]


def test_third_party_reproduces_a_kinetics_dossier(isolated, tmp_path):
    d = experiment_service.run_kinetics(KINETICS)
    package, _ = trace_package.build_package(d["history_record"]["id"])
    code, report, out = third_party_run(package, tmp_path / "third_party")
    assert code == 0, out
    assert report["status"] == "reproduced" and report["dossier_hash_matches_content"] and report["comparison"]["compared_values"] > 50


def test_third_party_reproduces_a_fit_on_published_data(isolated, tmp_path):
    d = experiment_service.run_fit({"dataset_id": "puromycin_treloar_1974", "x_column": "conc", "y_column": "rate", "where": {"state": "treated"}, "model": "michaelis_menten"})
    package, manifest = trace_package.build_package(d["history_record"]["id"])
    assert "data/puromycin_treloar_1974.csv" in {f["path"] for f in manifest["files"]}
    code, report, out = third_party_run(package, tmp_path / "fit")
    assert code == 0 and report["status"] == "reproduced", out


def test_third_party_reproduces_a_fit_on_imported_data_with_its_original_file(isolated, tmp_path):
    csv = "t (d),y (mg/L)\n1,8.3\n2,10.3\n3,19.0\n4,16.0\n5,15.6\n7,19.8\n"
    data_import.import_file(csv, "bod_copy.csv", {"id": "bod_copy", "title": "copy", "license": "test", "applicability": "test"})
    d = experiment_service.run_fit({"dataset_id": "bod_copy", "x_column": "t", "y_column": "y", "model": "first_order_rise"})
    package, manifest = trace_package.build_package(d["history_record"]["id"])
    with zipfile.ZipFile(io.BytesIO(package)) as zf:
        assert zf.read("data/original/bod_copy.csv") == csv.encode("utf-8")
    code, report, out = third_party_run(package, tmp_path / "imported")
    assert code == 0 and report["status"] == "reproduced", out


def test_third_party_reproduces_an_instrument_reading_with_its_source_dossier(isolated, tmp_path):
    source = experiment_service.run_kinetics(KINETICS)
    reading = experiment_service.measure_linked({"source_experiment_id": source["history_record"]["id"], "quantity": "final_concentration:B",
                                                 "instrument_id": "spectrophotometer", "seed": 5, "epsilon_l_per_mol_cm": 100.0, "path_length_cm": 1.0})
    package, _ = trace_package.build_package(reading["history_record"]["id"])
    code, report, out = third_party_run(package, tmp_path / "reading")
    assert code == 0 and report["status"] == "reproduced", out


def test_tampered_package_is_refused_by_the_reproduction_script(isolated, tmp_path):
    d = experiment_service.run_kinetics(KINETICS)
    package, _ = trace_package.build_package(d["history_record"]["id"])
    target = tmp_path / "tampered"
    target.mkdir()
    with zipfile.ZipFile(io.BytesIO(package)) as zf:
        zf.extractall(target)
    engine = target / "platform" / "chemical_kinetics.py"
    engine.write_text(engine.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, "-I", "reproduce.py"], cwd=target, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 2 and "platform/chemical_kinetics.py" in proc.stdout


@pytest.fixture
def base(isolated):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def test_package_and_events_api(base):
    d = experiment_service.run_kinetics(KINETICS)
    eid = d["history_record"]["id"]
    with urllib.request.urlopen(f"{base}/api/history/{eid}/package", timeout=30) as r:
        assert r.headers["Content-Type"] == "application/zip" and "attachment" in r.headers["Content-Disposition"]
        assert trace_package.verify_package(r.read())["valid"]
    with urllib.request.urlopen(f"{base}/api/history/{eid}/events", timeout=10) as r:
        assert [e["event"] for e in json.loads(r.read())["events"]] == ["saved", "packaged"]
    try:
        urllib.request.urlopen(f"{base}/api/history/99999/package", timeout=10)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
