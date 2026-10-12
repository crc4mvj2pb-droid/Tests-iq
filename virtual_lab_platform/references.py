"""Sources and references (v6.1): every constant, model and parameter value says where it comes from.

- Every model contract cites source ids (data_catalog/contract_references.json) resolving in
  data_catalog/sources.json, the single bibliography of the platform.
- Every physical constant names its source id (SI Brochure for exact constants, CODATA 2018 otherwise).
- Every numeric default of a contract is labelled: these defaults are illustrative values chosen to
  demonstrate a model, not properties of a real system, and the label says so.
- Every non-SI unit accepted by units.py has a definition with its source and an exact/approximate flag.

`problems()` lists anything that breaks these rules; the test suite requires it to be empty.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
ILLUSTRATIVE = {"status": "illustrative",
                "note": "Default value chosen to demonstrate the model; not a sourced property of a real system. Replace it with a sourced value for any real study."}
REQUIRED_SOURCE_FIELDS = ("id", "kind", "citation", "year", "license")


def sources() -> dict[str, dict[str, Any]]:
    data = json.loads((ROOT / "data_catalog" / "sources.json").read_text(encoding="utf-8"))
    return {s["id"]: s for s in data["sources"]}


def contract_reference_ids() -> dict[str, list[str]]:
    return json.loads((ROOT / "data_catalog" / "contract_references.json").read_text(encoding="utf-8"))["contracts"]


def annotate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Add reference_ids and default provenance labels to a contract (in place) and return it."""
    contract["reference_ids"] = list(contract_reference_ids().get(contract["id"], []))
    for spec in contract["parameters"]:
        if spec.get("type") in ("number", "integer") and "default" in spec and "default_provenance" not in spec:
            spec["default_provenance"] = dict(ILLUSTRATIVE)
    return contract


def cited_by() -> dict[str, list[dict[str, str]]]:
    """Reverse index: source id → entries citing it (contracts, constants, catalogue datasets, adapters)."""
    import constants
    import data_catalog
    import model_registry
    import pipelines
    index: dict[str, list[dict[str, str]]] = {}

    def add(source_id, kind, item):
        index.setdefault(source_id, []).append({"kind": kind, "id": item})
    for c in model_registry.list_contracts():
        for sid in c.get("reference_ids", []):
            add(sid, "model_contract", c["id"])
    for c in constants.all_constants():
        add(c["source_id"], "physical_constant", c["id"])
    for d in data_catalog.shipped_datasets():
        for sid in d.get("source_ids", []):
            add(sid, "dataset", d["id"])
    for name, adapter in pipelines.ADAPTERS.items():
        for sid in adapter.get("reference_ids", []):
            add(sid, "pipeline_adapter", name)
    import units
    for symbol, definition in units.DEFINITIONS.items():
        if definition.get("source_id"):
            add(definition["source_id"], "unit", symbol)
    return index


def problems() -> list[str]:
    import constants
    import model_registry
    import pipelines
    import units
    known = sources()
    out = []
    for sid, s in known.items():
        missing = [f for f in REQUIRED_SOURCE_FIELDS if not s.get(f)]
        if missing:
            out.append(f"source {sid}: missing {', '.join(missing)}")
        if not (s.get("version") or s.get("accessed")):
            out.append(f"source {sid}: no version or access date")
    for c in model_registry.list_contracts():
        if not c.get("reference_ids"):
            out.append(f"contract {c['id']}: no reference id")
        out += [f"contract {c['id']}: unknown source {sid}" for sid in c.get("reference_ids", []) if sid not in known]
        for p in c["parameters"]:
            if p.get("type") in ("number", "integer") and "default" in p and not p.get("default_provenance"):
                out.append(f"contract {c['id']}: default of {p['name']} has no provenance label")
    for c in constants.all_constants():
        if c.get("source_id") not in known:
            out.append(f"constant {c['id']}: source id {c.get('source_id')!r} unknown")
        if not c.get("exact") and not c.get("relative_standard_uncertainty"):
            out.append(f"constant {c['id']}: measured constant without uncertainty")
    for name, adapter in pipelines.ADAPTERS.items():
        if not adapter.get("reference_ids"):
            out.append(f"adapter {name}: no reference id")
        out += [f"adapter {name}: unknown source {sid}" for sid in adapter.get("reference_ids", []) if sid not in known]
    for symbol, definition in units.DEFINITIONS.items():
        if definition.get("source_id") and definition["source_id"] not in known:
            out.append(f"unit {symbol}: unknown source {definition['source_id']}")
        if "exact" not in definition:
            out.append(f"unit {symbol}: exact/approximate not stated")
    undefined = [s for s in units.non_si_symbols() if s not in units.DEFINITIONS]
    out += [f"unit {s}: accepted but has no documented definition" for s in undefined]
    return out
