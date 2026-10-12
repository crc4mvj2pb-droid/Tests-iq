"""Unified experiment dossier format (schema 2) and its integrity checks.

Every endpoint that saves an experiment builds its dossier here, so all records share the
same envelope: schema/app/engine versions, model id, configuration and its hash, data
status, and a hash of the whole dossier (results included). Earlier dossiers (schema 1,
before v4.5) remain readable; their verification level is reported honestly.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from experiment_lifecycle import canonical_configuration, configuration_hash
from version import APP_VERSION

DOSSIER_SCHEMA_VERSION = 2
# Fields that are not part of the hashed content: where the record was stored, and the hash itself.
_UNHASHED = ("history_record", "dossier_hash", "imported_from")


def normalize_numbers(value: Any) -> Any:
    """Make the canonical form independent of the JSON writer.

    JavaScript serializes 9.0 as 9 and -0.0 as 0, so a dossier that went through the browser
    comes back with ints where Python wrote floats. Integral floats are therefore written as
    ints before hashing; the numeric values are unchanged.
    """
    if isinstance(value, float) and value.is_integer() and abs(value) < 2 ** 63:
        return int(value)
    if isinstance(value, dict):
        return {k: normalize_numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_numbers(v) for v in value]
    return value


def normalized_configuration_hash(configuration: dict[str, Any]) -> str:
    return configuration_hash(normalize_numbers(configuration))


def dossier_content_hash(dossier: dict[str, Any]) -> str:
    content = normalize_numbers({k: v for k, v in dossier.items() if k not in _UNHASHED})
    return hashlib.sha256(canonical_configuration(content).encode("utf-8")).hexdigest()


def build_dossier(result: dict[str, Any], *, model_id: str, title: str, configuration: dict[str, Any],
                  engine_id: str, engine_version: str, question: str = "", data_status: str = "simulated_calculation",
                  status: str = "completed") -> dict[str, Any]:
    """Wrap an engine result into a schema-2 dossier (result fields stay at the top level for API compatibility)."""
    dossier = dict(result)
    dossier.update({
        "dossier_schema_version": DOSSIER_SCHEMA_VERSION,
        # Distinguishes two runs of the same configuration; part of the hashed content.
        "created_at_utc": dossier.get("created_at_utc") or datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "app_version": APP_VERSION,
        "engine": {"id": engine_id, "version": engine_version},
        "model_id": model_id,
        "title": str(title or f"{model_id} experiment")[:200],
        "question": str(question or "")[:4000],
        "status": status,
        "data_status": data_status,
        "configuration": configuration,
        "configuration_hash": normalized_configuration_hash(configuration),
    })
    dossier["dossier_hash"] = dossier_content_hash(dossier)
    return dossier


def legacy_model_id(dossier: dict[str, Any]) -> str | None:
    """model_id of a pre-v4.5 dossier: /api/experiments stored it as model.id."""
    if isinstance(dossier.get("model_id"), str):
        return dossier["model_id"]
    model = dossier.get("model")
    return model.get("id") if isinstance(model, dict) and isinstance(model.get("id"), str) else None


def verify_dossier(dossier: dict[str, Any], column_hash: str | None = None, column_dossier_hash: str | None = None) -> dict[str, Any]:
    """Return {valid, level, checks[], reason}. level: full | configuration_only | unverifiable."""
    checks = []
    configuration = dossier.get("configuration")
    expected = dossier.get("configuration_hash") or dossier.get("configuration_sha256")
    if isinstance(configuration, dict) and isinstance(expected, str):
        actual = configuration_hash(configuration)
        if actual != expected and normalized_configuration_hash(configuration) == expected:
            actual = expected  # same configuration, re-serialized by a JSON writer that drops ".0" (e.g. the browser)
        if dossier.get("configuration_sha256") and not dossier.get("configuration_hash"):
            # /api/experiments (schema 1) hashed with engine.canonical_hash: same canonical form, NaN allowed.
            actual = hashlib.sha256(json.dumps(configuration, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        checks.append({"check": "configuration_hash", "passed": actual == expected, "expected": expected, "actual": actual})
    if isinstance(dossier.get("dossier_hash"), str):
        actual = dossier_content_hash(dossier)
        checks.append({"check": "dossier_hash", "passed": actual == dossier["dossier_hash"], "expected": dossier["dossier_hash"], "actual": actual})
    if column_hash is not None and isinstance(expected, str):
        checks.append({"check": "index_configuration_hash", "passed": column_hash == expected, "expected": column_hash, "actual": expected})
    if column_dossier_hash is not None:
        checks.append({"check": "index_dossier_hash", "passed": column_dossier_hash == dossier.get("dossier_hash"), "expected": column_dossier_hash, "actual": dossier.get("dossier_hash")})
    names = {c["check"] for c in checks}
    if not checks:
        return {"valid": False, "level": "unverifiable", "checks": [], "reason": "Dossier has no verifiable hash."}
    valid = all(c["passed"] for c in checks)
    level = "full" if "dossier_hash" in names else ("configuration_only" if "configuration_hash" in names else "unverifiable")
    if not valid:
        failed = ", ".join(c["check"] for c in checks if not c["passed"])
        reason = f"Integrity check failed: {failed}."
    elif level == "full":
        reason = "Configuration and full dossier (results included) match their recorded hashes."
    else:
        reason = "Configuration hash matches. This pre-v4.5 dossier has no full-dossier hash: results are not covered."
    return {"valid": valid, "level": level, "checks": checks, "reason": reason,
            # v4.1-compatible fields
            "check": "configuration_hash", "expected_hash": expected, "actual_hash": next((c["actual"] for c in checks if c["check"] == "configuration_hash"), None)}
