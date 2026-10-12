from __future__ import annotations
import json
import os
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# VIRTUAL_LAB_DB lets tests and clean-environment checks use an isolated database.
DB_PATH = Path(os.environ.get("VIRTUAL_LAB_DB") or Path(__file__).resolve().parent / "virtual_lab_history.sqlite3")
# Schema 1: v2.x–v4.4 table. Schema 2 (v4.5): adds dossier_hash, dossier_schema_version and app_version
# columns, and repairs the index columns of legacy rows. Stored dossier JSON is never rewritten.
DB_SCHEMA_VERSION = 2


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _schema_version(conn) -> int:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    row = conn.execute("SELECT value FROM schema_meta WHERE key = 'db_schema_version'").fetchone()
    return int(row["value"]) if row else 1


def _migrate_1_to_2(conn) -> None:
    from dossier import legacy_model_id
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(experiments)")}
    for name, kind in (("dossier_hash", "TEXT"), ("dossier_schema_version", "INTEGER"), ("app_version", "TEXT")):
        if name not in columns:
            conn.execute(f"ALTER TABLE experiments ADD COLUMN {name} {kind}")
    for row in conn.execute("SELECT id, model_id, title, configuration_hash, dossier_json FROM experiments").fetchall():
        dossier = json.loads(row["dossier_json"])
        model_id = row["model_id"]
        if model_id == "unknown":
            model_id = legacy_model_id(dossier) or "unknown"
        title = row["title"]
        if title == "unknown experiment" and isinstance(dossier.get("name"), str):
            title = dossier["name"][:200]
        config_hash = row["configuration_hash"] or dossier.get("configuration_hash") or dossier.get("configuration_sha256")
        conn.execute("UPDATE experiments SET model_id=?, title=?, configuration_hash=?, dossier_hash=?, dossier_schema_version=? WHERE id=?",
                     (model_id, title, config_hash, dossier.get("dossier_hash"), int(dossier.get("dossier_schema_version", 1)), row["id"]))


def initialize():
    existed = DB_PATH.exists() and DB_PATH.stat().st_size > 0
    with closing(_connect()) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    configuration_hash TEXT,
                    status TEXT NOT NULL,
                    dossier_json TEXT NOT NULL
                )
            """)
            version = _schema_version(conn)
        if version >= DB_SCHEMA_VERSION:
            return
        has_rows = conn.execute("SELECT COUNT(*) AS n FROM experiments").fetchone()["n"] > 0
    if existed and has_rows:
        # Keep an untouched copy of the database before any structural change.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = DB_PATH.with_name(f"{DB_PATH.name}.backup-schema-{version}-{stamp}")
        if not backup.exists():
            shutil.copy2(DB_PATH, backup)
    with closing(_connect()) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        if _schema_version(conn) < 2:
            _migrate_1_to_2(conn)
            conn.execute("INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('db_schema_version', '2')")


def save_experiment(dossier: dict[str, Any]) -> dict[str, Any]:
    initialize()
    model_id = str(dossier.get("model_id", "unknown"))
    title = str(dossier.get("title") or f"{model_id} experiment")
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    config_hash = dossier.get("configuration_hash")
    status = str(dossier.get("status", "completed"))
    payload = json.dumps(dossier, ensure_ascii=False, allow_nan=False)
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO experiments (created_at, model_id, title, configuration_hash, status, dossier_json, dossier_hash, dossier_schema_version, app_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (created_at, model_id, title, config_hash, status, payload, dossier.get("dossier_hash"),
             int(dossier.get("dossier_schema_version", 1)), dossier.get("app_version"))
        )
        return {"id": cur.lastrowid, "created_at": created_at}


def list_experiments(limit: int = 50) -> list[dict[str, Any]]:
    initialize()
    limit = max(1, min(int(limit), 200))
    with closing(_connect()) as conn, conn:
        rows = conn.execute(
            "SELECT id, created_at, model_id, title, configuration_hash, status, dossier_schema_version, app_version FROM experiments ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_experiment(experiment_id: int) -> dict[str, Any] | None:
    initialize()
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT dossier_json FROM experiments WHERE id = ?", (int(experiment_id),)).fetchone()
    return json.loads(row["dossier_json"]) if row else None


def get_experiment_record(experiment_id: int) -> dict[str, Any] | None:
    """Dossier plus the index columns, so verification can compare both."""
    initialize()
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT id, created_at, configuration_hash, dossier_hash, dossier_json FROM experiments WHERE id = ?", (int(experiment_id),)).fetchone()
    if not row:
        return None
    return {"id": row["id"], "created_at": row["created_at"], "configuration_hash": row["configuration_hash"],
            "dossier_hash": row["dossier_hash"], "dossier": json.loads(row["dossier_json"])}


def all_experiment_ids() -> list[int]:
    initialize()
    with closing(_connect()) as conn, conn:
        return [r["id"] for r in conn.execute("SELECT id FROM experiments ORDER BY id")]


def clear_history() -> int:
    initialize()
    with closing(_connect()) as conn, conn:
        cur = conn.execute("DELETE FROM experiments")
        return cur.rowcount
