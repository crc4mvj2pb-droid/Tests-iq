"""Backups, verification and restore of the local data (v9.0).

A backup is one ZIP file containing:
  history.sqlite3     a consistent copy made with SQLite's online backup API (safe while the server runs);
  imported_assets/    the imported source files and their registry;
  backup.json         creation time, app version, database schema version, experiment count, and the
                      SHA-256 of every file (integrity, not authenticity).
`verify_backup` re-hashes every file and opens the database copy (PRAGMA integrity_check).
`restore_backup` verifies first, saves the current data as a "pre-restore" backup, then replaces the
database and the imported assets. Nothing is overwritten when verification fails.
Command line:  python maintenance.py backup | list | verify <file> | restore <file> | check
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import history
import scientific_imports
from version import APP_VERSION

FORMAT = "virtual-lab-backup"
FORMAT_VERSION = 1


class BackupError(ValueError):
    def __init__(self, message: str, code: str = "backup_error", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def backup_dir() -> Path:
    import config
    try:
        return Path(config.load()["backup_dir"])
    except config.ConfigError:
        return Path(config.DEFAULTS["backup_dir"])


def integrity_check(db_path: Path | None = None) -> dict[str, Any]:
    path = Path(db_path or history.DB_PATH)
    if not path.exists():
        return {"ok": True, "detail": "no database yet (created at first save)", "experiments": 0}
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0] if conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='experiments'").fetchone() else 0
    except sqlite3.DatabaseError as exc:
        return {"ok": False, "detail": f"database unreadable: {exc}", "experiments": None}
    return {"ok": result == "ok", "detail": result, "experiments": count}


def _db_copy_bytes() -> bytes:
    history.initialize()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "copy.sqlite3"
        with closing(sqlite3.connect(history.DB_PATH)) as src, closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
        return target.read_bytes()


def create_backup(label: str = "manual", directory: Path | None = None) -> dict[str, Any]:
    files: dict[str, bytes] = {"history.sqlite3": _db_copy_bytes()}
    assets = Path(scientific_imports.ASSET_DIR)
    if assets.is_dir():
        for path in sorted(p for p in assets.rglob("*") if p.is_file()):
            files["imported_assets/" + path.relative_to(assets).as_posix()] = path.read_bytes()
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.sqlite3"
        probe.write_bytes(files["history.sqlite3"])
        check = integrity_check(probe)
        with closing(sqlite3.connect(probe)) as conn:
            schema = conn.execute("SELECT value FROM schema_meta WHERE key='db_schema_version'").fetchone()
    meta = {"format": FORMAT, "format_version": FORMAT_VERSION, "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": "".join(c for c in str(label) if c.isalnum() or c in "-_")[:40] or "manual", "app_version": APP_VERSION,
            "db_schema_version": int(schema[0]) if schema else 1, "experiments": check["experiments"],
            "files": [{"path": p, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)} for p, b in sorted(files.items())],
            "scope": "integrity of the listed files; not a signature"}
    out_dir = Path(directory or backup_dir())
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"virtual_lab_backup_{meta['created_at_utc'].replace(':', '').replace('-', '')}_{meta['label']}.zip"
    target = out_dir / name
    counter = 1
    while target.exists():
        target = out_dir / name.replace(".zip", f"_{counter}.zip"); counter += 1
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items()):
            zf.writestr(path, content)
        zf.writestr("backup.json", json.dumps(meta, indent=2))
    tmp_target = target.with_suffix(".partial")
    tmp_target.write_bytes(buffer.getvalue())
    tmp_target.replace(target)  # atomic: a crash never leaves a half-written backup under the final name
    return {"file": target.name, "path": str(target), "size": target.stat().st_size, **{k: meta[k] for k in ("created_at_utc", "app_version", "experiments", "label")}}


def verify_backup(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as zf:
            meta = json.loads(zf.read("backup.json"))
            if meta.get("format") != FORMAT:
                return {"valid": False, "reason": "not a Virtual Lab backup"}
            altered = [f["path"] for f in meta["files"] if f["path"] not in zf.namelist() or hashlib.sha256(zf.read(f["path"])).hexdigest() != f["sha256"]]
            with tempfile.TemporaryDirectory() as tmp:
                probe = Path(tmp) / "probe.sqlite3"
                probe.write_bytes(zf.read("history.sqlite3"))
                check = integrity_check(probe)
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError) as exc:
        return {"valid": False, "reason": f"unreadable backup: {exc}"}
    valid = not altered and check["ok"]
    return {"valid": valid, "altered": altered, "database_check": check, "app_version": meta.get("app_version"), "experiments": meta.get("experiments"),
            "created_at_utc": meta.get("created_at_utc"), "reason": None if valid else ("altered files" if altered else "database copy failed its integrity check")}


def restore_backup(path: Path | str) -> dict[str, Any]:
    report = verify_backup(path)
    if not report["valid"]:
        raise BackupError(f"Backup refused: {report['reason']}. Nothing was changed.", "invalid_backup", report=report)
    safety = create_backup("pre-restore")  # the current state can always be recovered
    with zipfile.ZipFile(path) as zf:
        db_bytes = zf.read("history.sqlite3")
        assets = {n[len("imported_assets/"):]: zf.read(n) for n in zf.namelist() if n.startswith("imported_assets/")}
    db = Path(history.DB_PATH)
    tmp_db = db.with_suffix(".restoring")
    tmp_db.write_bytes(db_bytes)
    tmp_db.replace(db)
    asset_dir = Path(scientific_imports.ASSET_DIR)
    if asset_dir.exists():
        shutil.rmtree(asset_dir)
    for rel, content in assets.items():
        target = asset_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    history.initialize()  # migrates an older schema if needed (with its own automatic copy)
    return {"restored_from": Path(path).name, "experiments": integrity_check()["experiments"], "pre_restore_backup": safety["file"]}


def list_backups(directory: Path | None = None) -> list[dict[str, Any]]:
    out = []
    for path in sorted(Path(directory or backup_dir()).glob("virtual_lab_backup_*.zip")):
        out.append({"file": path.name, "size": path.stat().st_size, "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")})
    return out


def prune(keep: int, directory: Path | None = None) -> list[str]:
    files = sorted(Path(directory or backup_dir()).glob("virtual_lab_backup_*.zip"), key=lambda p: p.stat().st_mtime)
    removed = [p.name for p in files[:-keep]] if keep > 0 else []
    for name in removed:
        (Path(directory or backup_dir()) / name).unlink()
    return removed


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "check"
    if command == "backup":
        print(json.dumps(create_backup("cli"), indent=2)); return 0
    if command == "list":
        print(json.dumps(list_backups(), indent=2)); return 0
    if command == "verify" and len(argv) > 2:
        r = verify_backup(argv[2]); print(json.dumps(r, indent=2)); return 0 if r["valid"] else 1
    if command == "restore" and len(argv) > 2:
        print(json.dumps(restore_backup(argv[2]), indent=2)); return 0
    if command == "check":
        r = integrity_check(); print(json.dumps(r, indent=2)); return 0 if r["ok"] else 1
    print(__doc__); return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
