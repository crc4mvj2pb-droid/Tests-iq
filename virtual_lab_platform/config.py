"""Configuration of a local installation (v9.0).

Sources, in increasing priority: built-in defaults < JSON file (virtual_lab_config.json next to app.py,
or the path in VIRTUAL_LAB_CONFIG) < environment variables (VIRTUAL_LAB_PORT, VIRTUAL_LAB_DB, ...).
Every value is validated; an invalid configuration stops the start-up with a clear list of problems
instead of running with a silently corrected value. The server always listens on the loopback interface:
this is a single-user local application and the address is not configurable.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
HOST = "127.0.0.1"
DEFAULTS: dict[str, Any] = {"port": 8765, "db_path": str(BASE / "virtual_lab_history.sqlite3"), "backup_dir": str(BASE / "backups"),
                            "backup_keep": 10, "log_dir": str(BASE / "logs"), "log_max_bytes": 2_000_000, "max_request_bytes": 1_000_000,
                            "max_import_bytes": 20_000_000, "requests_per_minute": 600}
ENV = {"port": "VIRTUAL_LAB_PORT", "db_path": "VIRTUAL_LAB_DB", "backup_dir": "VIRTUAL_LAB_BACKUP_DIR", "log_dir": "VIRTUAL_LAB_LOG_DIR"}
RULES = {"port": (int, 1024, 65535), "backup_keep": (int, 1, 1000), "log_max_bytes": (int, 10_000, 1_000_000_000),
         "max_request_bytes": (int, 10_000, 100_000_000), "max_import_bytes": (int, 10_000, 1_000_000_000), "requests_per_minute": (int, 10, 1_000_000),
         "db_path": (str, None, None), "backup_dir": (str, None, None), "log_dir": (str, None, None)}


class ConfigError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("Invalid configuration: " + "; ".join(problems))
        self.problems = problems
        self.code = "invalid_configuration"


def load(environ: dict[str, str] | None = None, file_path: str | None = None) -> dict[str, Any]:
    environ = os.environ if environ is None else environ
    values, sources = dict(DEFAULTS), {k: "default" for k in DEFAULTS}
    path = Path(file_path or environ.get("VIRTUAL_LAB_CONFIG") or BASE / "virtual_lab_config.json")
    problems = []
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError([f"{path.name}: not readable JSON ({exc})"]) from exc
        if not isinstance(data, dict):
            raise ConfigError([f"{path.name}: must contain a JSON object"])
        for key, value in data.items():
            if key not in DEFAULTS:
                problems.append(f"{path.name}: unknown setting '{key}'")
                continue
            values[key], sources[key] = value, path.name
    for key, var in ENV.items():
        if var in environ and environ[var] != "":
            values[key], sources[key] = environ[var], f"environment {var}"
    for key, (kind, lo, hi) in RULES.items():
        value = values[key]
        if kind is int:
            try:
                value = int(value) if not isinstance(value, bool) else None
            except (TypeError, ValueError):
                value = None
            if value is None or not lo <= value <= hi:
                problems.append(f"{key} ({sources[key]}): integer between {lo} and {hi} expected, got {values[key]!r}")
                continue
        elif not isinstance(value, str) or not value.strip():
            problems.append(f"{key} ({sources[key]}): non-empty path expected")
            continue
        values[key] = value
    if problems:
        raise ConfigError(problems)
    return {**values, "host": HOST, "sources": sources, "config_file": str(path) if path.is_file() else None}


def public(config: dict[str, Any]) -> dict[str, Any]:
    """Configuration as shown to the user (paths reduced to names: no personal directory structure is exposed)."""
    return {k: (Path(v).name if k.endswith(("_path", "_dir")) else v) for k, v in config.items() if k != "config_file"} | \
           {"config_file": Path(config["config_file"]).name if config.get("config_file") else None}
