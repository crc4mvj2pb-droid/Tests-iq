"""v5.7 — maturity levels: claims backed by existing evidence; equations, assumptions and limits exposed."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import maturity
import model_registry
from lab_designer import CATALOG
from models import MODEL_CATALOG

ROOT = Path(__file__).resolve().parents[1]


def test_every_maturity_claim_is_backed():
    assert maturity.check_claims() == []


def test_counts_and_honest_absence_of_data_validation():
    counts = maturity.summary()["counts"]
    assert counts["validated_on_data"] == 1  # v7.3: enzyme_kinetics validated on the Puromycin data (was 0 up to v7.2)
    assert counts["concept"] == sum(m["status"] == "workflow_template" for m in MODEL_CATALOG)
    assert sum(counts.values()) == len(maturity.summary()["models"])


@pytest.mark.parametrize("bad", [
    {"level": "verified", "evidence": [{"kind": "analytical", "test": "tests/test_nothing.py::test_x", "description": "", "tolerance": ""}]},
    {"level": "verified", "evidence": [{"kind": "internal_checks", "test": "tests/test_v57_maturity.py::test_every_maturity_claim_is_backed", "description": "", "tolerance": ""}]},
    {"level": "validated_on_data", "evidence": []},
    {"level": "excellent", "evidence": []},
])
def test_unbacked_claims_are_detected(monkeypatch, bad):
    monkeypatch.setitem(maturity.MATURITY, "fake_model", bad)
    assert any(p.startswith("fake_model") for p in maturity.check_claims())


def test_every_contract_exposes_maturity_equations_assumptions_and_validity():
    for contract in model_registry.list_contracts():
        m = contract["maturity"]
        assert m["level"] in maturity.LEVEL_IDS and m["label_fr"]
        if m["level"] == "verified":
            assert contract["equations"] and contract["assumptions"] and contract["validity"] and m["evidence"], contract["id"]


def test_catalogue_templates_are_conceptual_mockups():
    for m in MODEL_CATALOG:
        level = maturity.maturity_of(m["id"], m["status"])["level"]
        expected = ("concept",) if m["status"] == "workflow_template" else ("verified", "validated_on_data")  # v7.3: enzyme_kinetics validated on data
        assert level in expected, m["id"]


def test_catalogue_counts_announced_by_the_api_match_the_code():
    text = (ROOT / "app.py").read_text(encoding="utf-8")
    claim = re.search(r"(\d+) disciplines, (\d+) components, (\d+) equipment entries, (\d+) experiment workflows, (\d+) model entries including (\d+) L0 templates", text)
    assert claim, "catalogue claim not found"
    expected = (len(CATALOG["disciplines"]), len(CATALOG["components"]), len(CATALOG["equipment"]), len(CATALOG["workflows"]),
                len(MODEL_CATALOG), sum(m["status"] == "workflow_template" for m in MODEL_CATALOG))
    assert tuple(int(x) for x in claim.groups()) == expected
