"""Versioned physical constants (v5.1), read from scientific_library/physical_constants.json.

Engines import constants from here instead of hard-coding them, so a value, its source and
its reference date are stated in exactly one place.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PATH = Path(__file__).resolve().parent / "scientific_library" / "physical_constants.json"
_DATA = json.loads(_PATH.read_text(encoding="utf-8"))
CONSTANTS_VERSION: str = _DATA["constants_version"]
_BY_ID: dict[str, dict[str, Any]] = {c["id"]: c for c in _DATA["constants"]}


def get(constant_id: str) -> dict[str, Any]:
    return dict(_BY_ID[constant_id])


def value(constant_id: str) -> float:
    return float(_BY_ID[constant_id]["value"])


def all_constants() -> list[dict[str, Any]]:
    return [dict(c) for c in _DATA["constants"]]


GAS_CONSTANT = value("gas_constant")          # J/(mol·K)
BOLTZMANN = value("boltzmann_constant")       # J/K
AVOGADRO = value("avogadro_constant")         # 1/mol
ELEMENTARY_CHARGE = value("elementary_charge")  # C
FARADAY = value("faraday_constant")           # C/mol
