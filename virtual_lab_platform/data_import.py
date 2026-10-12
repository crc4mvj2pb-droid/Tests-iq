"""Data import with preview and quality report (v6.2).

CSV or JSON text is parsed without modifying it. The report states, column by column, the unit
detected in the header ("name (unit)" or "name [unit]"), the type, missing values, duplicates
and outliers, and lists every transformation applied to obtain the catalogue rows. The original
file is stored byte for byte (scientific_imports) and its SHA-256 is kept in the catalogue entry.

Outlier rule (reported, never removed automatically): modified z-score |0.6745·(x − median)/MAD| > 3.5
(B. Iglewicz, D. C. Hoaglin, How to Detect and Handle Outliers, ASQC, 1993).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import statistics
from typing import Any

import data_catalog
import units

MAX_BYTES = 2_000_000
MAX_ROWS = 50_000
MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "missing", "."}
HEADER_UNIT = re.compile(r"^\s*(?P<name>.*?)\s*[\(\[](?P<unit>[^\)\]]+)[\)\]]\s*$")
OUTLIER_Z = 3.5


class ImportError_(ValueError):
    def __init__(self, message: str, code: str = "invalid_data_file", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def _parse_header(raw: str) -> dict[str, Any]:
    match = HEADER_UNIT.match(raw)
    if not match:
        return {"header": raw, "name": raw.strip(), "unit": None, "unit_status": "none"}
    unit = match.group("unit").strip()
    try:
        units.parse(unit)
        status = "recognized"
    except units.UnitError:
        status = "unrecognized"
    return {"header": raw, "name": match.group("name").strip(), "unit": unit, "unit_status": status}


def _table(content: str, fmt: str) -> tuple[list[str], list[list[Any]], list[str]]:
    """Header strings, raw rows (strings or JSON values) and the transformations needed to read them."""
    transformations = []
    if fmt == "csv":
        text = content
        if text.startswith("﻿"):
            text = text[1:]
            transformations.append("byte-order mark removed before parsing (file itself unchanged)")
        try:
            dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","
        if delimiter != ",":
            transformations.append(f"delimiter detected: {delimiter!r}")
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = [r for r in reader]
        rows = [r for r in rows if any(c.strip() for c in r)]
        if not rows:
            raise ImportError_("The file contains no header row.", "empty_file")
        header, body = rows[0], rows[1:]
        for i, r in enumerate(body):
            if len(r) != len(header):
                raise ImportError_(f"Line {i + 2} has {len(r)} fields; the header has {len(header)}.", "ragged_rows", line=i + 2)
        return [h.strip() for h in header], body, transformations
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ImportError_(f"Invalid JSON: {exc}", "invalid_json") from exc
    if isinstance(data, dict) and isinstance(data.get("columns"), list) and isinstance(data.get("rows"), list):
        header = [c if isinstance(c, str) else (f"{c.get('name')} ({c['unit']})" if c.get("unit") else str(c.get("name"))) for c in data["columns"]]
        body = data["rows"]
    elif isinstance(data, list) and data and all(isinstance(r, dict) for r in data):
        header = list(dict.fromkeys(k for r in data for k in r))
        body = [[r.get(k) for k in header] for r in data]
        transformations.append("list of JSON objects converted to rows (missing keys become missing values)")
    else:
        raise ImportError_("JSON must be {\"columns\": [...], \"rows\": [[...]]} or a list of objects.", "invalid_json")
    for i, r in enumerate(body):
        if not isinstance(r, list) or len(r) != len(header):
            raise ImportError_(f"Row {i + 1} must have {len(header)} values.", "ragged_rows", line=i + 1)
    return [str(h).strip() for h in header], body, transformations


def _to_number(value: Any) -> tuple[float | None, bool]:
    """(number, is_missing); strings are parsed with '.' as the decimal separator only."""
    if value is None:
        return None, True
    if isinstance(value, bool):
        return None, False
    if isinstance(value, (int, float)):
        return (float(value), False) if math.isfinite(value) else (None, True)
    text = str(value).strip()
    if text.casefold() in MISSING_TOKENS:
        return None, True
    try:
        number = float(text)
    except ValueError:
        return None, False
    return (number, False) if math.isfinite(number) else (None, True)


def analyze(content: Any, filename: str = "data.csv", fmt: str | None = None) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise ImportError_("Provide the file content as text.", "empty_file")
    raw = content.encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ImportError_(f"File larger than {MAX_BYTES} bytes.", "file_too_large")
    fmt = fmt or ("json" if str(filename).casefold().endswith(".json") else "csv")
    if fmt not in ("csv", "json"):
        raise ImportError_("Format must be csv or json.", "invalid_format")
    headers, body, transformations = _table(content, fmt)
    if not headers or any(not h for h in headers):
        raise ImportError_("Every column needs a name.", "invalid_header")
    columns = [_parse_header(h) for h in headers]
    names = [c["name"] for c in columns]
    if len(set(names)) != len(names):
        raise ImportError_("Column names must be unique (after removing units).", "duplicate_columns")
    if not body:
        raise ImportError_("The file has no data rows.", "no_rows")
    if len(body) > MAX_ROWS:
        raise ImportError_(f"More than {MAX_ROWS} rows.", "too_many_rows")
    if any(c["unit"] for c in columns):
        transformations.append("units read from the column headers and removed from the column names")
    report_columns, typed = [], []
    for j, column in enumerate(columns):
        values = [row[j] for row in body]
        parsed = [_to_number(v) for v in values]
        missing_rows = [i + 1 for i, (_, miss) in enumerate(parsed) if miss]
        present = [v for v, (_, miss) in zip(values, parsed) if not miss]
        numbers = [n for n, miss in parsed if n is not None]
        numeric = bool(present) and len(numbers) == len(present)
        info = {**column, "type": "number" if numeric else "text", "missing": len(missing_rows), "missing_rows": missing_rows[:50]}
        if numeric:
            median = statistics.median(numbers)
            mad = statistics.median(abs(x - median) for x in numbers)
            outliers = []
            if mad > 0:
                outliers = [{"row": i + 1, "value": n, "modified_z": 0.6745 * (n - median) / mad}
                            for i, (n, _) in enumerate(parsed) if n is not None and abs(0.6745 * (n - median) / mad) > OUTLIER_Z]
            info.update(minimum=min(numbers), maximum=max(numbers), median=median, outliers=outliers[:50], outlier_count=len(outliers))
            if any(isinstance(v, str) for v in values):
                transformations.append(f"column {column['name']}: text converted to numbers")
            typed.append([n for n, _ in parsed])
        else:
            if column["unit"]:
                info["warning"] = "a unit is declared but the values are not all numeric"
            typed.append([None if miss else (str(v).strip() if v is not None else None) for v, (_, miss) in zip(values, parsed)])
        report_columns.append(info)
    rows = [list(r) for r in zip(*typed)]
    seen, duplicates = {}, []
    for i, r in enumerate(rows):
        key = json.dumps(r)
        if key in seen:
            duplicates.append({"row": i + 1, "duplicate_of": seen[key]})
        else:
            seen[key] = i + 1
    issues = []
    if duplicates:
        issues.append({"code": "duplicate_rows", "count": len(duplicates)})
    for c in report_columns:
        if c["missing"]:
            issues.append({"code": "missing_values", "column": c["name"], "count": c["missing"]})
        if c.get("outlier_count"):
            issues.append({"code": "outliers", "column": c["name"], "count": c["outlier_count"], "rule": f"|modified z| > {OUTLIER_Z} (Iglewicz & Hoaglin, 1993)"})
        if c["unit_status"] == "unrecognized":
            issues.append({"code": "unrecognized_unit", "column": c["name"], "unit": c["unit"]})
        if c["type"] == "number" and c["unit_status"] == "none":
            issues.append({"code": "numeric_column_without_unit", "column": c["name"]})
    return {"format": fmt, "filename": str(filename), "file_sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
            "row_count": len(rows), "columns": report_columns, "duplicates": duplicates[:50], "issues": issues,
            "transformations": list(dict.fromkeys(transformations)), "preview": rows[:10], "rows": rows,
            "policy": "Nothing is removed or corrected automatically: duplicates, missing values and outliers are reported for the user to decide."}


def check_schema(report: dict[str, Any], expected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare the detected columns with an expected schema [{name, unit?, type?}]; units must be convertible."""
    problems = []
    found = {c["name"]: c for c in report["columns"]}
    for spec in expected:
        column = found.get(spec["name"])
        if column is None:
            problems.append({"code": "missing_column", "column": spec["name"]})
            continue
        if spec.get("type") and column["type"] != spec["type"]:
            problems.append({"code": "wrong_type", "column": spec["name"], "expected": spec["type"], "found": column["type"]})
        if spec.get("unit"):
            if not column["unit"]:
                problems.append({"code": "missing_unit", "column": spec["name"], "expected": spec["unit"]})
            elif column["unit_status"] == "recognized" and not units.compatible(column["unit"], spec["unit"]):
                problems.append({"code": "incompatible_unit", "column": spec["name"], "expected": spec["unit"], "found": column["unit"]})
    return problems


def to_catalog_entry(report: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Catalogue entry of kind 'imported' built from an analysis report and user-declared metadata."""
    for key in ("id", "title", "license", "applicability"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ImportError_(f"Metadata field '{key}' is required.", "missing_metadata", field=key)
    unknown_units = [c["name"] for c in report["columns"] if c["unit_status"] == "unrecognized"]
    if unknown_units:
        raise ImportError_(f"Columns with unrecognized units: {', '.join(unknown_units)}. Fix the header before importing.", "unrecognized_unit", columns=unknown_units)
    return {"id": metadata["id"], "version": str(metadata.get("version", "1")), "title": metadata["title"], "data_kind": "imported",
            "domain": metadata.get("domain", ""), "license": metadata["license"], "applicability": metadata["applicability"],
            "description": metadata.get("description", ""),
            "columns": [{"name": c["name"], "unit": c["unit"] if c["type"] == "number" else None, "quantity": c["name"]} for c in report["columns"]],
            "rows": report["rows"],
            "provenance": {"file_sha256": report["file_sha256"], "filename": report["filename"], "format": report["format"],
                           "declared_source": metadata.get("declared_source", ""), "transformations": report["transformations"],
                           "quality_issues": report["issues"], "declared_by_user": True}}


def import_file(content: str, filename: str, metadata: dict[str, Any], fmt: str | None = None) -> dict[str, Any]:
    """Analyze, store the original file unchanged (imported assets) and register a catalogue entry of kind 'imported'."""
    import scientific_imports
    from datetime import datetime, timezone
    report = analyze(content, filename, fmt)
    entry = to_catalog_entry(report, metadata)
    data_catalog.validate_dataset(entry)
    raw = content.encode("utf-8")
    safe = scientific_imports._clean_filename(filename, f"data.{report['format']}")
    target = scientific_imports.ASSET_DIR / "datasets" / f"{report['format']}_{report['file_sha256'][:16]}_{safe}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(raw)
    if target.read_bytes() != raw:
        raise ImportError_("A different file is stored under the same name and hash prefix; import refused.", "storage_conflict")
    asset = {"id": f"{report['format']}_{report['file_sha256'][:16]}", "type": "catalogue_source_file", "filename": safe,
             "stored_path": str(target.relative_to(scientific_imports.BASE)), "sha256": report["file_sha256"], "size_bytes": len(raw),
             "imported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "catalogue_entry": entry["id"],
             "license": metadata["license"], "validation_status": "quality report attached; values not scientifically validated"}
    scientific_imports._save_asset(dict(asset))
    added = data_catalog.add_entry(entry)
    return {"asset": asset, "entry": data_catalog.summary(added), "report": {k: v for k, v in report.items() if k != "rows"}}
