"""Observability, diagnostics and crash recovery (v9.2).

Request log: one JSON line per request (UTC time, method, path without query string, status, error code,
duration). No request body, no parameter values, no client address: the log cannot leak experiment data.
Kept in memory (recent entries and counters) and, when the server is started from app.py, also written to
logs/requests.jsonl with size-based rotation (3 old files kept).
Diagnostics: versions, uptime, counters, recent errors, database integrity and size, backups, disk space,
running jobs, configuration sources and maturity counts — everything needed to describe a problem to support.
Recovery: if the database fails its integrity check at start-up, the server runs in read-only recovery mode
(writes refused with 503) until a backup is restored; an automatic backup is made at start-up when the most
recent one is older than 24 h.
"""
from __future__ import annotations

import json
import platform
import shutil
import sqlite3
import threading
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STARTED = time.time()
_LOCK = threading.Lock()
RECENT = deque(maxlen=200)
ERRORS = deque(maxlen=50)
COUNTS: Counter = Counter()
LOG = {"path": None, "max_bytes": 2_000_000, "keep": 3}
RECOVERY = {"active": False, "reason": None, "since": None}
RECOVERY_ALLOWED_POSTS = {"/api/admin/backup/verify", "/api/admin/backup/restore", "/api/admin/backup"}


def configure_log(log_dir: str | Path, max_bytes: int) -> None:
    path = Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)
    LOG.update(path=path / "requests.jsonl", max_bytes=max_bytes)


def _rotate(path: Path) -> None:
    if path.exists() and path.stat().st_size > LOG["max_bytes"]:
        for i in range(LOG["keep"] - 1, 0, -1):
            older = path.with_suffix(f".jsonl.{i}")
            if older.exists():
                older.replace(path.with_suffix(f".jsonl.{i + 1}"))
        path.replace(path.with_suffix(".jsonl.1"))
        last = path.with_suffix(f".jsonl.{LOG['keep'] + 1}")
        if last.exists():
            last.unlink()


def record(method: str, path: str, status: int, error_code: str | None, duration_ms: float) -> None:
    entry = {"at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "method": method, "path": path.split("?", 1)[0][:200],
             "status": status, "error_code": error_code, "duration_ms": round(duration_ms, 2)}
    with _LOCK:
        RECENT.append(entry)
        COUNTS[f"status_{status // 100}xx"] += 1
        COUNTS["requests"] += 1
        if status >= 400:
            ERRORS.append(entry)
        if LOG["path"] is not None:
            try:
                _rotate(LOG["path"])
                with LOG["path"].open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            except OSError:
                COUNTS["log_write_failures"] += 1


def enter_recovery(reason: str) -> None:
    RECOVERY.update(active=True, reason=reason, since=datetime.now(timezone.utc).isoformat(timespec="seconds"))


def leave_recovery() -> None:
    RECOVERY.update(active=False, reason=None, since=None)


def startup_backup(max_age_hours: float = 24.0, keep: int = 10) -> dict[str, Any] | None:
    """Make an automatic backup when the latest one is older than max_age_hours (never when the database is damaged)."""
    import maintenance
    if not maintenance.integrity_check()["ok"]:
        return None
    backups = sorted(Path(maintenance.backup_dir()).glob("virtual_lab_backup_*.zip"), key=lambda p: p.stat().st_mtime)
    if backups and time.time() - backups[-1].stat().st_mtime < max_age_hours * 3600:
        return None
    made = maintenance.create_backup("auto-startup")
    maintenance.prune(keep)
    return made


def diagnostics() -> dict[str, Any]:
    import config
    import history
    import jobs
    import maintenance
    import maturity
    from version import APP_VERSION
    db = Path(history.DB_PATH)
    backups = maintenance.list_backups()
    try:
        cfg = config.public(config.load())
    except config.ConfigError as exc:
        cfg = {"problems": exc.problems}
    usage = shutil.disk_usage(db.parent if db.parent.exists() else Path("."))
    with jobs.MANAGER._lock:
        running = sum(j["status"] in ("queued", "running") for j in jobs.MANAGER._jobs.values())
    with _LOCK:
        counts, errors = dict(COUNTS), list(ERRORS)[-20:]
    return {"app_version": APP_VERSION, "python": platform.python_version(), "os": platform.system(), "sqlite": sqlite3.sqlite_version,
            "uptime_s": round(time.time() - STARTED, 1), "recovery_mode": dict(RECOVERY), "requests": counts, "recent_errors": errors,
            "database": {**maintenance.integrity_check(), "size_bytes": db.stat().st_size if db.exists() else 0},
            "backups": {"count": len(backups), "latest": backups[-1] if backups else None},
            "disk_free_bytes": usage.free, "jobs_running": running, "configuration": cfg,
            "maturity_counts": maturity.summary()["counts"], "log_file": LOG["path"].name if LOG["path"] else None}
