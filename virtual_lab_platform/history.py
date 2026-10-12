from __future__ import annotations
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# VIRTUAL_LAB_DB lets tests and clean-environment checks use an isolated database.
DB_PATH = Path(os.environ.get("VIRTUAL_LAB_DB") or Path(__file__).resolve().parent / "virtual_lab_history.sqlite3")

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize():
    with closing(_connect()) as conn, conn:
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
            "INSERT INTO experiments (created_at, model_id, title, configuration_hash, status, dossier_json) VALUES (?, ?, ?, ?, ?, ?)",
            (created_at, model_id, title, config_hash, status, payload)
        )
        return {"id": cur.lastrowid, "created_at": created_at}

def list_experiments(limit: int = 50) -> list[dict[str, Any]]:
    initialize()
    limit = max(1, min(int(limit), 200))
    with closing(_connect()) as conn, conn:
        rows = conn.execute(
            "SELECT id, created_at, model_id, title, configuration_hash, status FROM experiments ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(row) for row in rows]

def get_experiment(experiment_id: int) -> dict[str, Any] | None:
    initialize()
    with closing(_connect()) as conn, conn:
        row = conn.execute("SELECT dossier_json FROM experiments WHERE id = ?", (int(experiment_id),)).fetchone()
    return json.loads(row["dossier_json"]) if row else None

def clear_history() -> int:
    initialize()
    with closing(_connect()) as conn, conn:
        cur = conn.execute("DELETE FROM experiments")
        return cur.rowcount
