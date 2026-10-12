"""v6.1 — sources and references: every constant, model, default value and unit says where it comes from."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import constants
import model_registry
import pipelines
import references
import units


def test_no_reference_problem_anywhere():
    assert references.problems() == []


def test_every_contract_cites_resolvable_sources():
    known = references.sources()
    for c in model_registry.list_contracts():
        assert c["reference_ids"] and all(s in known for s in c["reference_ids"]), c["id"]
    arrhenius = model_registry.get_contract("arrhenius_reaction")
    assert arrhenius["reference_ids"] == ["arrhenius_1889"] and "1889" in known["arrhenius_1889"]["citation"]


def test_numeric_defaults_are_labelled_illustrative():
    labelled = 0
    for c in model_registry.list_contracts():
        for p in c["parameters"]:
            if p["type"] in ("number", "integer") and "default" in p:
                assert p["default_provenance"]["status"] == "illustrative", (c["id"], p["name"])
                labelled += 1
    assert labelled > 60


def test_constants_name_their_source_and_uncertainty():
    for c in constants.all_constants():
        assert c["source_id"] == ("bipm_si_brochure_2019" if c["exact"] else "codata_2018")
        assert c["exact"] or c["relative_standard_uncertainty"] > 0


def test_every_accepted_non_si_unit_is_defined_and_approximations_are_flagged():
    assert set(units.non_si_symbols()) <= set(units.DEFINITIONS)
    assert units.DEFINITIONS["Da"]["exact"] is False and units.DEFINITIONS["Da"]["relative_standard_uncertainty"] > 0
    assert units.DEFINITIONS["atm"]["source_id"] == "cgpm_1954" and units.DEFINITIONS["ppm"]["note"]
    assert units.convert(1.0, "Da", "kg") == pytest.approx(1.66053906660e-27, rel=1e-15)  # definition text and factor agree


def test_adapters_cite_their_sources():
    assert pipelines.ADAPTERS["beer_lambert"]["reference_ids"] == ["beer_1852"]
    assert pipelines.ADAPTERS["lumped_steady_heating"]["reference_ids"] == ["incropera_2007"]


def test_problems_are_detected(monkeypatch):
    real = references.contract_reference_ids()
    monkeypatch.setattr(references, "contract_reference_ids", lambda: {**real, "sir_epidemic": ["nobody_1999"]})
    contract = model_registry.REGISTRY["sir_epidemic"]["contract"]
    monkeypatch.setitem(contract, "reference_ids", ["nobody_1999"])
    assert "contract sir_epidemic: unknown source nobody_1999" in references.problems()
    spec = next(p for p in contract["parameters"] if p["name"] == "beta")
    monkeypatch.delitem(spec, "default_provenance")
    assert "contract sir_epidemic: default of beta has no provenance label" in references.problems()


def test_reverse_index_links_sources_to_what_cites_them():
    index = references.cited_by()
    assert {"kind": "dataset", "id": "puromycin_treloar_1974"} in index["bates_watts_1988"]
    assert {"kind": "model_contract", "id": "sir_epidemic"} in index["kermack_mckendrick_1927"]
    assert {"kind": "physical_constant", "id": "gas_constant"} in index["bipm_si_brochure_2019"]
    assert {"kind": "unit", "id": "Da"} in index["codata_2018"]
    unused = [sid for sid in references.sources() if sid not in index]
    assert unused == [], unused  # the bibliography holds no orphan entry


@pytest.fixture
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_sources_api(base):
    code, d = get(base + "/api/sources")
    assert code == 200 and d["problems"] == [] and len(d["sources"]) >= 30
    michaelis = next(s for s in d["sources"] if s["id"] == "michaelis_menten_1913")
    assert {"kind": "model_contract", "id": "enzyme_kinetics"} in michaelis["cited_by"]
    code, s = get(base + "/api/sources/codata_2018")
    assert code == 200 and s["doi"] == "10.1103/RevModPhys.93.025010" and s["cited_by"]
    code, err = get(base + "/api/sources/unknown_1900")
    assert code == 404 and err["error_code"] == "unknown_source"
    code, c = get(base + "/api/contracts/logistic_growth")
    assert c["reference_ids"] == ["verhulst_1838"] and all(p["default_provenance"]["status"] == "illustrative" for p in c["parameters"] if "default" in p and p["type"] == "number")
