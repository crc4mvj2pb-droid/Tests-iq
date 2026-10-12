"""v6.0 — versioned data catalogue: one schema, data kinds kept apart, sources, lock, search and export."""
from __future__ import annotations

import copy
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import data_catalog
import experiment_service
import history
from data_catalog import CatalogError


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v60.sqlite3")


def puromycin():
    return copy.deepcopy(data_catalog.get_entry("puromycin_treloar_1974"))


def test_shipped_datasets_follow_the_schema_and_cite_known_sources():
    datasets = data_catalog.shipped_datasets()
    sources = data_catalog.load_sources()
    assert {d["id"] for d in datasets} >= {"puromycin_treloar_1974", "bod_marske_1967"}
    for d in datasets:
        assert d["data_kind"] in ("experimental", "reference") and d["source_ids"] and all(s in sources for s in d["source_ids"])
        assert d["license"] and d["applicability"] and len(d["content_sha256"]) == 64
    p = data_catalog.get_entry("puromycin_treloar_1974")
    assert len(p["rows"]) == 23 and len(data_catalog.column_values(p, "rate", {"state": "treated"})) == 12
    assert sum(data_catalog.column_values(p, "rate", {"state": "treated"})) == 1699  # sum of the 12 published treated rates


def test_constants_appear_as_reference_records_with_their_uncertainty():
    rows = data_catalog.search(data_kind="reference")
    gas = next(r for r in rows if r["id"] == "constant_gas_constant")
    assert gas["unit"] == "J/(mol·K)" and gas["exact"] is True and gas["approximate"] is False
    eps0 = data_catalog.get_entry("constant_vacuum_electric_permittivity")
    assert eps0["exact"] is False and eps0["uncertainty"]["value"] > 0 and eps0["source_ids"] == ["codata_2018"]


def test_lock_detects_content_changed_without_a_new_version(tmp_path, monkeypatch):
    assert data_catalog.lock_problems() == []
    fake = tmp_path / "data_catalog"
    (fake / "datasets").mkdir(parents=True)
    for name in ("sources.json", "catalog_lock.json"):
        (fake / name).write_text((data_catalog.ROOT / name).read_text(encoding="utf-8"), encoding="utf-8")
    for path in (data_catalog.ROOT / "datasets").glob("*.json"):
        (fake / "datasets" / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    entry = json.loads((fake / "datasets" / "bod_marske_1967.json").read_text(encoding="utf-8"))
    entry["rows"][2][1] = 19.5  # silent edit of a measured value
    (fake / "datasets" / "bod_marske_1967.json").write_text(json.dumps(entry), encoding="utf-8")
    monkeypatch.setattr(data_catalog, "ROOT", fake)
    assert data_catalog.lock_problems() == ["bod_marske_1967: content changed but version 1.0 was kept"]


@pytest.mark.parametrize("mutate,code", [
    (lambda d: d.pop("license"), "missing_field"),
    (lambda d: d.__setitem__("data_kind", "measured"), "invalid_data_kind"),
    (lambda d: d.__setitem__("source_ids", []), "missing_source"),
    (lambda d: d.__setitem__("source_ids", ["nobody_2020"]), "unknown_source"),
    (lambda d: d["columns"][0].__setitem__("unit", "furlongs"), "invalid_unit"),
    (lambda d: d["rows"][0].__setitem__(1, "fast"), "invalid_rows"),
    (lambda d: d["rows"].append([1.0]), "invalid_rows"),
    (lambda d: d.__setitem__("id", "Bad Id"), "invalid_id"),
    (lambda d: d["columns"].append(dict(d["columns"][0])), "invalid_columns"),
])
def test_invalid_entries_are_refused(mutate, code):
    entry = {k: v for k, v in puromycin().items() if k not in ("record_type", "content_sha256", "origin")}
    mutate(entry)
    with pytest.raises(CatalogError) as exc:
        data_catalog.validate_dataset(entry)
    assert exc.value.code == code


def test_simulated_and_imported_data_need_their_provenance_and_cannot_pose_as_experimental(db):
    base = {"id": "my_series", "version": "1", "title": "t", "columns": [{"name": "t", "unit": "s"}], "rows": [[1.0]], "license": "local", "applicability": "test"}
    with pytest.raises(CatalogError) as exc:
        data_catalog.add_entry({**base, "data_kind": "simulated"})
    assert exc.value.code == "missing_provenance"
    with pytest.raises(CatalogError) as exc:
        data_catalog.add_entry({**base, "data_kind": "imported"})
    assert exc.value.code == "missing_provenance"
    with pytest.raises(CatalogError) as exc:  # a local entry cannot claim to be a measurement from a source
        data_catalog.add_entry({**base, "data_kind": "experimental", "source_ids": ["bates_watts_1988"]})
    assert exc.value.code == "kind_not_allowed"
    added = data_catalog.add_entry({**base, "data_kind": "imported", "provenance": {"file_sha256": "a" * 64}})
    assert added["origin"] == "local" and data_catalog.get_entry("my_series")["integrity_ok"]
    with pytest.raises(CatalogError) as exc:
        data_catalog.add_entry({**base, "data_kind": "imported", "provenance": {"file_sha256": "a" * 64}})
    assert exc.value.code == "duplicate_id"


def test_dossier_output_becomes_a_simulated_dataset_linked_to_its_dossier(db):
    dossier = experiment_service.run_kinetics({"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
                                               "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5}], "duration": 2.0, "dt": 0.1})
    entry = data_catalog.simulated_from_dossier(dossier, [{"name": "time", "unit": "s"}, {"name": "A", "unit": "mol/L"}])
    added = data_catalog.add_entry(entry)
    assert added["data_kind"] == "simulated" and added["provenance"]["dossier_hash"] == dossier["dossier_hash"]
    assert data_catalog.search(data_kind="experimental", query="kinetics") == []  # never listed with measurements
    assert any(r["id"] == added["id"] for r in data_catalog.search(data_kind="simulated"))


def test_search_filters_and_csv_export():
    assert [r["id"] for r in data_catalog.search("oxygen demand")] == ["bod_marske_1967"]
    assert all(r["record_type"] == "dataset" for r in data_catalog.search(record_type="dataset"))
    assert data_catalog.search("planck", record_type="property")[0]["id"] == "constant_planck_constant"
    csv_text = data_catalog.export_csv("bod_marske_1967").splitlines()
    assert csv_text[0].startswith("# bod_marske_1967 v1.0 — data_kind: experimental") and csv_text[1] == "time (d),demand (mg/L)" and csv_text[4] == "3,19.0"
    with pytest.raises(CatalogError):
        data_catalog.search(data_kind="measured")


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v60api.sqlite3")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def call(url, body=None, raw=False):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read().decode()
            return r.status, data if raw else json.loads(data)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_catalog_api(base):
    code, d = call(base + "/api/data/catalog?q=puromycin")
    assert code == 200 and [r["id"] for r in d["entries"]] == ["puromycin_treloar_1974"] and d["data_kinds"] == list(data_catalog.DATA_KINDS)
    code, d = call(base + "/api/data/catalog?kind=reference")
    assert code == 200 and all(r["data_kind"] == "reference" for r in d["entries"]) and len(d["entries"]) >= 9
    code, entry = call(base + "/api/data/catalog/bod_marske_1967")
    assert code == 200 and entry["rows"][0] == [1, 8.3] and entry["published_analyses"]
    code, text = call(base + "/api/data/catalog/bod_marske_1967.csv", raw=True)
    assert code == 200 and "time (d),demand (mg/L)" in text
    code, err = call(base + "/api/data/catalog/nothing_here")
    assert code == 404 and err["error_code"] == "unknown_entry"
    code, err = call(base + "/api/data/catalog?kind=measured")
    assert code == 400 and err["error_code"] == "invalid_data_kind"
    code, ok = call(base + "/api/data/catalog/validate", {"id": "x_y_z", "version": "1", "title": "t", "data_kind": "experimental", "columns": [{"name": "a", "unit": "s"}],
                                                          "rows": [[1]], "license": "l", "applicability": "a"})
    assert code == 400 and ok["error_code"] == "missing_source"
