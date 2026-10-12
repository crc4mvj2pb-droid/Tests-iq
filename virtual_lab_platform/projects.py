"""Projects and sharing of reproducible dossiers (v9.3).

A project groups saved experiments (an experiment may belong to several projects; deleting a project never
deletes experiments). A project can be shared as one ZIP file:
  project.json            name, description, and the dossier hash of each experiment;
  history_bundle.json     the dossiers in the standard export format (imported with integrity verification);
  packages/<id>.zip       the reproducible package of each experiment (v6.4: data, code, reproduce.py);
  MANIFEST.json           SHA-256 of every file (integrity, not authenticity).
Import verifies the manifest, then imports the dossiers all-or-nothing (an altered dossier refuses the whole
file) and recreates the project with the new local ids; dossiers already present are linked, not duplicated.
Users and roles are deliberately not implemented: the application is local and single-user (see INSTALLATION_FR.md).
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from typing import Any

import experiment_service
import history
import trace_package

FORMAT = "virtual-lab-project"
FORMAT_VERSION = 1


class ProjectError(ValueError):
    def __init__(self, message: str, code: str = "invalid_project", status: int = 400, **params):
        super().__init__(message)
        self.code = code
        self.status = status
        self.params = params


def _connect():
    history.initialize()
    conn = history._connect()
    conn.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL, created_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS project_experiments (project_id INTEGER NOT NULL, experiment_id INTEGER NOT NULL, added_at TEXT NOT NULL, "
                 "PRIMARY KEY (project_id, experiment_id))")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_project(name: str, description: str = "") -> dict[str, Any]:
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise ProjectError("A project name of 1 to 120 characters is required.", "invalid_name")
    with closing(_connect()) as conn, conn:
        cur = conn.execute("INSERT INTO projects (name, description, created_at) VALUES (?,?,?)", (name.strip(), str(description or "")[:2000], _now()))
        return get_project(cur.lastrowid, conn)


def get_project(project_id: int, conn=None) -> dict[str, Any]:
    own = conn is None
    conn = conn or _connect()
    try:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (int(project_id),)).fetchone()
        if row is None:
            raise ProjectError("Unknown project.", "unknown_project", 404)
        ids = [r["experiment_id"] for r in conn.execute("SELECT experiment_id FROM project_experiments WHERE project_id = ? ORDER BY experiment_id", (row["id"],))]
    finally:
        if own:
            conn.close()
    return {"id": row["id"], "name": row["name"], "description": row["description"], "created_at": row["created_at"], "experiment_ids": ids}


def list_projects() -> list[dict[str, Any]]:
    with closing(_connect()) as conn:
        return [get_project(r["id"], conn) for r in conn.execute("SELECT id FROM projects ORDER BY id")]


def add_experiment(project_id: int, experiment_id: int) -> dict[str, Any]:
    if history.get_experiment(int(experiment_id)) is None:
        raise ProjectError("Unknown experiment.", "unknown_experiment", 404)
    with closing(_connect()) as conn, conn:
        get_project(project_id, conn)
        conn.execute("INSERT OR IGNORE INTO project_experiments VALUES (?,?,?)", (int(project_id), int(experiment_id), _now()))
        return get_project(project_id, conn)


def remove_experiment(project_id: int, experiment_id: int) -> dict[str, Any]:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM project_experiments WHERE project_id = ? AND experiment_id = ?", (int(project_id), int(experiment_id)))
        return get_project(project_id, conn)


def delete_project(project_id: int) -> dict[str, Any]:
    with closing(_connect()) as conn, conn:
        get_project(project_id, conn)
        conn.execute("DELETE FROM project_experiments WHERE project_id = ?", (int(project_id),))
        conn.execute("DELETE FROM projects WHERE id = ?", (int(project_id),))
    return {"deleted": int(project_id), "experiments_kept": True}


def export_project(project_id: int, include_packages: bool = True) -> bytes:
    project = get_project(project_id)
    if not project["experiment_ids"]:
        raise ProjectError("The project has no experiment to share.", "empty_project")
    records = [history.get_experiment_record(i) for i in project["experiment_ids"]]
    bundle = {"format": experiment_service.EXPORT_FORMAT_HISTORY, "format_version": experiment_service.EXPORT_FORMAT_VERSION,
              "exported_at": _now(), "app_version": experiment_service.APP_VERSION, "record_count": len(records),
              "records": [{"id": r["id"], "created_at": r["created_at"], "dossier": r["dossier"]} for r in records]}
    meta = {"format": FORMAT, "format_version": FORMAT_VERSION, "name": project["name"], "description": project["description"], "exported_at": _now(),
            "experiments": [{"original_id": r["id"], "model_id": r["dossier"].get("model_id"), "dossier_hash": r["dossier"].get("dossier_hash")} for r in records]}
    files = {"project.json": json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"),
             "history_bundle.json": json.dumps(bundle, ensure_ascii=False).encode("utf-8")}
    if include_packages:
        for r in records:
            files[f"packages/experiment_{r['id']}.zip"] = trace_package.build_package(r["id"])[0]
    listing = [{"path": p, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)} for p, b in sorted(files.items())]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items()):
            zf.writestr(path, content)
        zf.writestr("MANIFEST.json", json.dumps({"files": listing, "scope": "integrity of the listed files; not a signature"}, indent=2))
    for i in project["experiment_ids"]:
        trace_package.log_event(i, "shared_in_project", project=project["name"])
    return out.getvalue()


def import_project(data: bytes) -> dict[str, Any]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ProjectError("Not a ZIP file.", "invalid_project_file") from None
    with zf:
        try:
            manifest = json.loads(zf.read("MANIFEST.json"))
            altered = [f["path"] for f in manifest["files"] if f["path"] not in zf.namelist() or hashlib.sha256(zf.read(f["path"])).hexdigest() != f["sha256"]]
            meta = json.loads(zf.read("project.json"))
            bundle = json.loads(zf.read("history_bundle.json"))
        except (KeyError, json.JSONDecodeError) as exc:
            raise ProjectError(f"Incomplete project file: {exc}", "invalid_project_file") from None
    if altered:
        raise ProjectError("Project file altered: files differ from its manifest. Nothing was imported.", "altered_project_file", 409, altered=altered)
    if meta.get("format") != FORMAT:
        raise ProjectError("Not a Virtual Lab project file.", "invalid_project_file")
    result = experiment_service.import_bundle(bundle)  # verifies every dossier; all-or-nothing
    by_hash = {history.get_experiment_record(i)["dossier"].get("dossier_hash"): i for i in history.all_experiment_ids()}
    project = create_project(meta["name"] + " (importé)", meta.get("description", ""))
    for exp in meta["experiments"]:
        local = by_hash.get(exp["dossier_hash"])
        if local is not None:
            add_experiment(project["id"], local)
    return {"project": get_project(project["id"]), "imported_count": result["imported_count"], "already_present": result["skipped_count"]}
