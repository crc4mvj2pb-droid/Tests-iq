"""Versioned data catalogue (v6.0).

One schema for every value the platform uses or shows: property, value, unit, conditions,
source, date, licence, uncertainty, applicability and — always — the kind of data:

  reference     defined or evaluated values (SI definitions, CODATA)
  experimental  measurements published by a cited source
  imported      a file brought in by the user (provenance as declared by the user)
  computed      derived by a deterministic calculation from other catalogue entries
  simulated     output of a platform model (never presented as a measurement)

Shipped entries live in data_catalog/ (JSON, versioned). Each dataset's content hash is
recorded in data_catalog/catalog_lock.json: a change of content without a new version is
detected. User entries (imported, simulated) are stored in the local SQLite database.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import constants
import history
import units

ROOT = Path(__file__).resolve().parent / "data_catalog"
DATA_KINDS = ("reference", "experimental", "imported", "computed", "simulated")
CATALOG_SCHEMA_VERSION = "1.0"
ID_PATTERN = re.compile(r"^[a-z0-9_]{3,80}$")


class CatalogError(ValueError):
    def __init__(self, message: str, code: str = "invalid_catalog_entry", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def canonical_hash(entry: dict[str, Any]) -> str:
    content = {k: v for k, v in entry.items() if k not in ("content_sha256", "origin")}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_sources() -> dict[str, dict[str, Any]]:
    data = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    return {s["id"]: s for s in data["sources"]}


def _check_unit(unit: Any, where: str) -> None:
    if unit is None:
        return
    if not isinstance(unit, str) or not unit:
        raise CatalogError(f"{where}: unit must be a non-empty string or null (non-numeric column).", "invalid_unit")
    try:
        units.parse(unit)
    except units.UnitError as exc:
        raise CatalogError(f"{where}: unit '{unit}' is not understood ({exc}).", "invalid_unit", unit=unit) from exc


def validate_dataset(entry: Any, sources: dict[str, dict] | None = None) -> dict[str, Any]:
    """Check one dataset against the catalogue schema; return it unchanged or raise CatalogError."""
    sources = load_sources() if sources is None else sources
    if not isinstance(entry, dict):
        raise CatalogError("A dataset must be a JSON object.")
    for key in ("id", "version", "title", "data_kind", "columns", "rows", "license", "applicability"):
        if key not in entry:
            raise CatalogError(f"Dataset field '{key}' is required.", "missing_field", field=key)
    if not isinstance(entry["id"], str) or not ID_PATTERN.match(entry["id"]):
        raise CatalogError("Dataset id: 3–80 characters among a–z, 0–9 and '_'.", "invalid_id")
    if entry["data_kind"] not in DATA_KINDS:
        raise CatalogError(f"data_kind must be one of {', '.join(DATA_KINDS)}.", "invalid_data_kind")
    cited = entry.get("source_ids") or []
    if entry["data_kind"] in ("reference", "experimental") and not cited:
        raise CatalogError(f"A '{entry['data_kind']}' dataset must cite at least one source.", "missing_source")
    unknown = [s for s in cited if s not in sources]
    if unknown and entry["data_kind"] in ("reference", "experimental"):
        raise CatalogError(f"Unknown source id(s): {', '.join(unknown)}.", "unknown_source", sources=unknown)
    if entry["data_kind"] == "simulated" and not (entry.get("provenance") or {}).get("dossier_hash"):
        raise CatalogError("Simulated data must reference the dossier that produced it (provenance.dossier_hash).", "missing_provenance")
    if entry["data_kind"] == "imported" and not (entry.get("provenance") or {}).get("file_sha256"):
        raise CatalogError("Imported data must keep the hash of its original file (provenance.file_sha256).", "missing_provenance")
    columns = entry["columns"]
    if not isinstance(columns, list) or not columns or not all(isinstance(c, dict) and isinstance(c.get("name"), str) for c in columns):
        raise CatalogError("columns must be a non-empty list of {name, quantity, unit}.", "invalid_columns")
    names = [c["name"] for c in columns]
    if len(set(names)) != len(names):
        raise CatalogError("Column names must be unique.", "invalid_columns")
    for c in columns:
        _check_unit(c.get("unit"), f"column {c['name']}")
    rows = entry["rows"]
    if not isinstance(rows, list) or not rows:
        raise CatalogError("rows must be a non-empty list.", "invalid_rows")
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(columns):
            raise CatalogError(f"Row {i + 1} must have {len(columns)} values.", "invalid_rows", row=i + 1)
        for value, column in zip(row, columns):
            if column.get("unit") is not None and value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise CatalogError(f"Row {i + 1}, column {column['name']}: numeric value expected.", "invalid_rows", row=i + 1)
    return entry


def _constant_entries() -> list[dict[str, Any]]:
    """The physical constants file expressed as catalogue property records (kind 'reference')."""
    out = []
    for c in constants.all_constants():
        source = "bipm_si_brochure_2019" if c.get("exact") else "codata_2018"
        out.append({"id": f"constant_{c['id']}", "record_type": "property", "property": c["name"], "symbol": c.get("symbol"), "value": c["value"],
                    "unit": c["unit"], "uncertainty": {"kind": "relative_standard", "value": c["relative_standard_uncertainty"]},
                    "exact": bool(c.get("exact")), "approximate": False, "conditions": {}, "source_ids": [source], "date": c["reference_date"],
                    "license": "factual value", "data_kind": "reference", "applicability": "universal constant", "version": constants.CONSTANTS_VERSION})
    return out


def shipped_datasets() -> list[dict[str, Any]]:
    sources = load_sources()
    out = []
    for path in sorted((ROOT / "datasets").glob("*.json")):
        entry = validate_dataset(json.loads(path.read_text(encoding="utf-8")), sources)
        out.append({**entry, "record_type": "dataset", "content_sha256": canonical_hash(entry), "origin": "shipped"})
    return out


def lock_problems() -> list[str]:
    """Shipped datasets whose content changed without a version change (or that are missing from the lock)."""
    lock = json.loads((ROOT / "catalog_lock.json").read_text(encoding="utf-8"))["datasets"]
    problems = []
    for d in shipped_datasets():
        locked = lock.get(d["id"])
        if locked is None:
            problems.append(f"{d['id']}: not in catalog_lock.json")
        elif locked["version"] == d["version"] and locked["content_sha256"] != d["content_sha256"]:
            problems.append(f"{d['id']}: content changed but version {d['version']} was kept")
        elif locked["version"] != d["version"]:
            problems.append(f"{d['id']}: version {d['version']} not recorded in catalog_lock.json (locked {locked['version']})")
    return problems


# ---- user entries (SQLite) ---------------------------------------------------------------------

def _connect():
    conn = history._connect()
    conn.execute("""CREATE TABLE IF NOT EXISTS catalog_entries (
        id TEXT PRIMARY KEY, version TEXT NOT NULL, data_kind TEXT NOT NULL, created_at TEXT NOT NULL,
        content_sha256 TEXT NOT NULL, entry_json TEXT NOT NULL)""")
    return conn


def add_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Register a user dataset (kind imported or simulated only: reference/experimental data ship with a source)."""
    validate_dataset(entry)
    if entry["data_kind"] not in ("imported", "simulated", "computed"):
        raise CatalogError("Only imported, computed or simulated datasets can be added locally; experimental and reference data are shipped with their sources.",
                           "kind_not_allowed")
    if any(d["id"] == entry["id"] for d in shipped_datasets()):
        raise CatalogError(f"'{entry['id']}' is a shipped dataset id.", "duplicate_id")
    digest = canonical_hash(entry)
    with closing(_connect()) as conn, conn:
        if conn.execute("SELECT 1 FROM catalog_entries WHERE id = ?", (entry["id"],)).fetchone():
            raise CatalogError(f"Dataset '{entry['id']}' already exists; use a new id or version.", "duplicate_id")
        conn.execute("INSERT INTO catalog_entries VALUES (?,?,?,?,?,?)", (entry["id"], str(entry["version"]), entry["data_kind"],
                                                                            datetime.now(timezone.utc).isoformat(timespec="seconds"), digest,
                                                                            json.dumps(entry, ensure_ascii=False)))
    return {**entry, "record_type": "dataset", "content_sha256": digest, "origin": "local"}


def local_datasets() -> list[dict[str, Any]]:
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT entry_json, content_sha256 FROM catalog_entries ORDER BY created_at").fetchall()
    out = []
    for row in rows:
        entry = json.loads(row["entry_json"])
        integrity = canonical_hash(entry) == row["content_sha256"]
        out.append({**entry, "record_type": "dataset", "content_sha256": row["content_sha256"], "origin": "local", "integrity_ok": integrity})
    return out


def simulated_from_dossier(dossier: dict[str, Any], columns: list[dict[str, Any]], rows_key: str = "rows") -> dict[str, Any]:
    """A dataset of kind 'simulated' built from a saved dossier's sampled rows, keeping the dossier hash."""
    source_rows = dossier.get(rows_key) or dossier.get("points")
    if not isinstance(source_rows, list) or not source_rows:
        raise CatalogError("The dossier has no sampled rows to catalogue.", "no_rows")
    names = [c["name"] for c in columns]
    rows = [[r.get(n) for n in names] for r in source_rows]
    record = (dossier.get("history_record") or {})
    return {"id": f"simulated_{dossier.get('model_id', 'model')}_{record.get('id', 'x')}".lower()[:80].replace("-", "_"),
            "version": "1", "title": f"Simulated output — {dossier.get('title', dossier.get('model_id'))}", "data_kind": "simulated",
            "domain": dossier.get("model_id", ""), "columns": columns, "rows": rows,
            "license": "generated locally", "applicability": "Model output under the dossier's assumptions; not a measurement.",
            "provenance": {"dossier_hash": dossier.get("dossier_hash"), "model_id": dossier.get("model_id"), "engine": dossier.get("engine"),
                           "app_version": dossier.get("app_version"), "experiment_id": record.get("id")}}


# ---- search and export -------------------------------------------------------------------------

def all_entries() -> list[dict[str, Any]]:
    return _constant_entries() + shipped_datasets() + local_datasets()


def summary(entry: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "record_type", "version", "title", "property", "value", "unit", "data_kind", "domain", "source_ids", "license",
            "applicability", "origin", "content_sha256", "exact", "approximate")
    out = {k: entry[k] for k in keys if k in entry}
    if entry.get("record_type") == "dataset":
        out["columns"] = [{"name": c["name"], "unit": c.get("unit"), "quantity": c.get("quantity")} for c in entry["columns"]]
        out["row_count"] = len(entry["rows"])
    return out


def search(query: str = "", data_kind: str | None = None, record_type: str | None = None, domain: str | None = None) -> list[dict[str, Any]]:
    if data_kind is not None and data_kind not in DATA_KINDS:
        raise CatalogError(f"data_kind must be one of {', '.join(DATA_KINDS)}.", "invalid_data_kind")
    words = [w for w in str(query or "").casefold().split() if w]
    results = []
    for entry in all_entries():
        if data_kind and entry["data_kind"] != data_kind:
            continue
        if record_type and entry.get("record_type") != record_type:
            continue
        if domain and domain.casefold() not in str(entry.get("domain", "")).casefold():
            continue
        text = json.dumps(summary(entry), ensure_ascii=False).casefold() + " " + str(entry.get("description", "")).casefold()
        if all(w in text for w in words):
            results.append(summary(entry))
    return results


def get_entry(entry_id: str) -> dict[str, Any]:
    for entry in all_entries():
        if entry["id"] == entry_id:
            return entry
    raise CatalogError(f"No catalogue entry '{entry_id}'.", "unknown_entry")


def export_csv(entry_id: str) -> str:
    entry = get_entry(entry_id)
    if entry.get("record_type") != "dataset":
        raise CatalogError("Only datasets can be exported as CSV.", "not_a_dataset")
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    sources = ", ".join(entry.get("source_ids") or []) or "none"
    buffer.write(f"# {entry['id']} v{entry['version']} — data_kind: {entry['data_kind']} — sources: {sources} — sha256: {entry['content_sha256']}\n")
    writer.writerow([f"{c['name']} ({c['unit']})" if c.get("unit") else c["name"] for c in entry["columns"]])
    writer.writerows(entry["rows"])
    return buffer.getvalue()


def column_values(entry: dict[str, Any], column: str, where: dict[str, Any] | None = None) -> list[Any]:
    names = [c["name"] for c in entry["columns"]]
    if column not in names:
        raise CatalogError(f"Unknown column '{column}'.", "unknown_column")
    idx = names.index(column)
    filters = [(names.index(k), v) for k, v in (where or {}).items()]
    return [row[idx] for row in entry["rows"] if all(row[i] == v for i, v in filters)]
