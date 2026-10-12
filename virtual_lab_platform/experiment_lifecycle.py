"""Reproducibility and integrity helpers for saved Virtual Lab experiment dossiers."""
from __future__ import annotations
import hashlib
import json
from typing import Any


def canonical_configuration(configuration: dict[str, Any]) -> str:
    """Serialize configuration deterministically; reject non-JSON/non-finite values."""
    if not isinstance(configuration, dict):
        raise ValueError("Experiment configuration must be an object.")
    return json.dumps(configuration, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def configuration_hash(configuration: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_configuration(configuration).encode("utf-8")).hexdigest()


def verify_dossier_integrity(dossier: dict[str, Any]) -> dict[str, Any]:
    """Verify the stored configuration hash when the dossier has a configuration."""
    configuration = dossier.get("configuration")
    expected = dossier.get("configuration_hash")
    if not isinstance(configuration, dict) or not isinstance(expected, str):
        return {"valid": False, "check": "configuration_hash", "reason": "Dossier has no verifiable configuration hash."}
    actual = configuration_hash(configuration)
    return {
        "valid": actual == expected,
        "check": "configuration_hash",
        "expected_hash": expected,
        "actual_hash": actual,
        "reason": "Configuration hash matches." if actual == expected else "Configuration differs from the hash recorded in the dossier.",
    }
