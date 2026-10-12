"""v9.3 — projects and sharing of reproducible dossiers between installations."""
from __future__ import annotations

import base64
import io
import json
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer

import pytest

import app
import experiment_service
import history
import projects
import trace_package

KINETICS = {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
            "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5}], "duration": 1.0, "dt": 0.1}


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "a.sqlite3")
    return tmp_path


def test_project_groups_experiments_without_owning_them(db):
    e1 = experiment_service.run_kinetics(KINETICS)["history_record"]["id"]
    e2 = experiment_service.run_fit({"dataset_id": "bod_marske_1967", "x_column": "time", "y_column": "demand", "model": "first_order_rise"})["history_record"]["id"]
    p = projects.create_project("Étude cinétique", "test")
    projects.add_experiment(p["id"], e1); projects.add_experiment(p["id"], e2); projects.add_experiment(p["id"], e1)
    assert projects.get_project(p["id"])["experiment_ids"] == [e1, e2]
    projects.delete_project(p["id"])
    assert history.get_experiment(e1) is not None and projects.list_projects() == []
    with pytest.raises(projects.ProjectError) as exc:
        projects.add_experiment(p["id"], e1)
    assert exc.value.code == "unknown_project"


def test_share_a_project_with_another_installation(db, monkeypatch):
    e1 = experiment_service.run_kinetics(KINETICS)["history_record"]["id"]
    p = projects.create_project("Partage")
    projects.add_experiment(p["id"], e1)
    data = projects.export_project(p["id"])
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert {"project.json", "history_bundle.json", "MANIFEST.json", f"packages/experiment_{e1}.zip"} <= set(names)
    package = zipfile.ZipFile(io.BytesIO(data)).read(f"packages/experiment_{e1}.zip")
    assert trace_package.verify_package(package)["valid"]
    monkeypatch.setattr(history, "DB_PATH", db / "colleague.sqlite3")  # a second, empty installation
    result = projects.import_project(data)
    assert result["imported_count"] == 1 and result["project"]["name"] == "Partage (importé)" and len(result["project"]["experiment_ids"]) == 1
    again = projects.import_project(data)  # importing twice links the existing dossier instead of duplicating it
    assert again["imported_count"] == 0 and again["already_present"] == 1 and len(history.all_experiment_ids()) == 1


def test_altered_project_file_is_refused_and_nothing_is_imported(db, monkeypatch):
    e1 = experiment_service.run_kinetics(KINETICS)["history_record"]["id"]
    p = projects.create_project("Altéré")
    projects.add_experiment(p["id"], e1)
    data = projects.export_project(p["id"], include_packages=False)
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(out, "w") as dst:
        for n in src.namelist():
            c = src.read(n)
            dst.writestr(n, c.replace(b'"rate_constant": 0.5', b'"rate_constant": 0.6') if n == "history_bundle.json" else c)
    monkeypatch.setattr(history, "DB_PATH", db / "other.sqlite3")
    with pytest.raises(projects.ProjectError) as exc:
        projects.import_project(out.getvalue())
    assert exc.value.code == "altered_project_file" and history.all_experiment_ids() == [] and projects.list_projects() == []


def test_invalid_inputs(db):
    with pytest.raises(projects.ProjectError):
        projects.create_project("")
    p = projects.create_project("Vide")
    with pytest.raises(projects.ProjectError) as exc:
        projects.export_project(p["id"])
    assert exc.value.code == "empty_project"
    with pytest.raises(projects.ProjectError):
        projects.import_project(b"not a zip")


def test_api(db):
    e1 = experiment_service.run_kinetics(KINETICS)["history_record"]["id"]
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())
    try:
        _, p = post("/api/projects", {"name": "API"})
        _, p = post(f"/api/projects/{p['id']}/experiments", {"experiment_id": e1})
        code_bad, bad = post(f"/api/projects/{p['id']}/experiments", {"experiment_id": 999})
        with urllib.request.urlopen(f"{base}/api/projects/{p['id']}/export", timeout=30) as r:
            data = r.read(); ctype = r.headers["Content-Type"]
        code_i, imported = post("/api/projects/import", {"bundle_base64": base64.b64encode(data).decode()})
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert p["experiment_ids"] == [e1] and code_bad == 404 and ctype == "application/zip" and code_i == 200 and imported["already_present"] == 1
