from __future__ import annotations
import csv, hashlib, io, json, math
from typing import Any

def sha256_json(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def parse_xy_csv(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or len(text) > 2_000_000:
        raise ValueError("CSV must be text no larger than 2 MB.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not {"x", "y"}.issubset({h.strip().lower() for h in reader.fieldnames}):
        raise ValueError("CSV must contain x and y headers.")
    # Resolve header casing and whitespace.
    headers = {h.strip().lower(): h for h in reader.fieldnames}
    rows = []
    for i, row in enumerate(reader, start=2):
        try:
            x, y = float(row[headers["x"]]), float(row[headers["y"]])
        except (TypeError, ValueError, KeyError):
            raise ValueError(f"Row {i} must contain numeric x and y.")
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError(f"Row {i} contains non-finite values.")
        rows.append({"x": x, "y": y})
    if len(rows) < 2:
        raise ValueError("At least two numeric rows are required.")
    return {"rows": rows, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "row_count": len(rows)}

def create_provenance_record(model_id: str, model_version: str, parameters: dict[str, Any], data_hashes: list[str] | None = None) -> dict[str, Any]:
    record = {
        "model_id": model_id,
        "model_version": model_version,
        "parameters": parameters,
        "input_data_sha256": data_hashes or [],
        "provenance_level": "local-prototype-record",
        "limitations": ["A hash supports integrity checks but does not independently prove origin, correctness, or scientific validity."]
    }
    record["record_sha256"] = sha256_json(record)
    return record
