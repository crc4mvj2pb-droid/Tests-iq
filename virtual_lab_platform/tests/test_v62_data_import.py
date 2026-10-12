"""v6.2 — data import: preview, units from headers, schema check, quality report, original file kept unchanged."""
from __future__ import annotations

import hashlib
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import app
import data_catalog
import data_import
import history
import scientific_imports
from data_import import ImportError_

CSV = "time (s),signal [mV],label\n0,1.0,a\n1,1.1,b\n2,1.2,c\n2,1.2,c\n3,,d\n4,1.3,e\n5,9.9,f\n6,1.4,g\n"


def test_units_types_missing_duplicates_and_outliers_are_reported():
    r = data_import.analyze(CSV, "run.csv")
    cols = {c["name"]: c for c in r["columns"]}
    assert cols["time"]["unit"] == "s" and cols["time"]["unit_status"] == "recognized" and cols["signal"]["unit"] == "mV"
    assert cols["label"]["type"] == "text" and cols["time"]["type"] == "number"
    assert cols["signal"]["missing"] == 1 and cols["signal"]["missing_rows"] == [5]
    assert r["duplicates"] == [{"row": 4, "duplicate_of": 3}]
    assert [o["row"] for o in cols["signal"]["outliers"]] == [7] and cols["signal"]["outliers"][0]["value"] == 9.9
    codes = {i["code"] for i in r["issues"]}
    assert codes == {"duplicate_rows", "missing_values", "outliers"}
    assert r["row_count"] == 8 and r["rows"][4] == [3.0, None, "d"]  # nothing removed, nothing imputed
    assert r["file_sha256"] == hashlib.sha256(CSV.encode()).hexdigest()


def test_outlier_rule_matches_the_modified_z_score_by_hand():
    values = [10, 11, 12, 13, 14, 100]
    r = data_import.analyze("x (m)\n" + "\n".join(map(str, values)) + "\n")
    median, mad = 12.5, 1.5  # median of |x − 12.5| = [2.5, 1.5, 0.5, 0.5, 1.5, 87.5] → 1.5
    outliers = r["columns"][0]["outliers"]
    assert [o["value"] for o in outliers] == [100.0] and outliers[0]["modified_z"] == pytest.approx(0.6745 * (100 - median) / mad)


def test_transformations_are_listed():
    r = data_import.analyze("﻿a (s);b (m)\n1;2\n3;4\n", "x.csv")
    assert r["rows"] == [[1.0, 2.0], [3.0, 4.0]]
    t = " ".join(r["transformations"])
    assert "byte-order mark" in t and "delimiter detected: ';'" in t and "units read from the column headers" in t


def test_json_formats():
    a = data_import.analyze(json.dumps({"columns": [{"name": "t", "unit": "s"}, "y"], "rows": [[0, 1], [1, 2]]}), "d.json")
    assert [c["unit"] for c in a["columns"]] == ["s", None] and a["format"] == "json"
    b = data_import.analyze(json.dumps([{"t (s)": 0, "y": 1}, {"t (s)": 1}]), "d.json")
    assert b["rows"] == [[0.0, 1.0], [1.0, None]] and "missing keys become missing values" in " ".join(b["transformations"])


@pytest.mark.parametrize("content,code", [
    ("", "empty_file"), ("a,b\n1\n", "ragged_rows"), ("a (s),a (m)\n1,2\n", "duplicate_columns"), ("a,b\n", "no_rows"),
    ("{bad json", "invalid_json"), ('{"x": 1}', "invalid_json"),
])
def test_malformed_files_are_refused(content, code):
    with pytest.raises(ImportError_) as exc:
        data_import.analyze(content, "f.json" if content.startswith("{") else "f.csv")
    assert exc.value.code == code


def test_unrecognized_units_and_unitless_numbers_are_flagged():
    r = data_import.analyze("t (fortnights),y\n1,2\n2,3\n")
    codes = {(i["code"], i.get("column")) for i in r["issues"]}
    assert ("unrecognized_unit", "t") in codes and ("numeric_column_without_unit", "y") in codes
    with pytest.raises(ImportError_) as exc:
        data_import.to_catalog_entry(r, {"id": "x_1", "title": "t", "license": "l", "applicability": "a"})
    assert exc.value.code == "unrecognized_unit"


def test_schema_check():
    r = data_import.analyze(CSV)
    assert data_import.check_schema(r, [{"name": "time", "unit": "min", "type": "number"}]) == []  # s and min are compatible
    problems = data_import.check_schema(r, [{"name": "time", "unit": "m"}, {"name": "signal", "unit": "V", "type": "text"}, {"name": "pressure"}])
    assert {p["code"] for p in problems} == {"incompatible_unit", "wrong_type", "missing_column"}


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v62.sqlite3")
    monkeypatch.setattr(scientific_imports, "ASSET_DIR", tmp_path / "assets")
    monkeypatch.setattr(scientific_imports, "INDEX", tmp_path / "assets" / "index.json")
    monkeypatch.setattr(scientific_imports, "BASE", tmp_path)
    return tmp_path


def test_import_keeps_the_original_file_byte_for_byte_and_registers_an_imported_dataset(isolated):
    result = data_import.import_file(CSV, "run.csv", {"id": "my_run", "title": "Run", "license": "own data", "applicability": "test",
                                                     "declared_source": "bench notebook p. 12"})
    stored = isolated / result["asset"]["stored_path"]
    assert stored.read_bytes() == CSV.encode("utf-8") and result["asset"]["sha256"] == hashlib.sha256(CSV.encode()).hexdigest()
    entry = data_catalog.get_entry("my_run")
    assert entry["data_kind"] == "imported" and entry["provenance"]["file_sha256"] == result["asset"]["sha256"]
    assert entry["provenance"]["declared_by_user"] and entry["provenance"]["quality_issues"] and entry["integrity_ok"]
    assert entry["rows"][4] == [3.0, None, "d"]


@pytest.fixture
def base(isolated):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_api_preview_then_import(base):
    code, preview = post(base + "/api/data/preview", {"filename": "run.csv", "content": CSV, "expected_schema": [{"name": "time", "unit": "s"}]})
    assert code == 200 and preview["schema_problems"] == [] and len(preview["preview"]) == 8 and "rows" not in preview
    code, done = post(base + "/api/data/import", {"filename": "run.csv", "content": CSV, "metadata": {"id": "api_run", "title": "Run", "license": "own", "applicability": "test"}})
    assert code == 200 and done["entry"]["data_kind"] == "imported" and done["entry"]["id"] == "api_run"
    code, err = post(base + "/api/data/import", {"filename": "run.csv", "content": CSV, "metadata": {"id": "api_run2", "title": "Run"}})
    assert code == 400 and err["error_code"] == "missing_metadata"
