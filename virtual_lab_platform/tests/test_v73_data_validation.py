"""v7.3 — first model validated on sourced data, with a protocol and criterion fixed in advance and a negative control."""
from __future__ import annotations

import json
import math
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import data_catalog
import data_validation
import domains
import maturity


def test_puromycin_protocol_is_validated_and_rejects_its_negative_control():
    r = data_validation.run("michaelis_menten_puromycin_treated")
    assert r["verdict"] == "validated" and r["validation_points"] == 6 and r["ratio"] <= r["threshold"] == 2.0
    control = r["negative_controls"][0]
    assert control["name"] == "untreated cells" and control["rejected"] and control["ratio"] > 2.0
    assert r["dataset"]["data_kind"] == "experimental" and r["dataset"]["content_sha256"] == data_catalog.get_entry("puromycin_treloar_1974")["content_sha256"]


def test_replicate_noise_by_hand():
    rates = [76, 47, 97, 107, 123, 139, 159, 152, 191, 201, 207, 200]
    d = [rates[i] - rates[i + 1] for i in range(0, 12, 2)]  # 29, -10, -16, 7, -10, 7
    expected = math.sqrt(sum(x * x for x in d) / 12)
    assert data_validation.run("michaelis_menten_puromycin_treated")["replicate_sd"] == pytest.approx(expected, rel=1e-12)


def test_criterion_would_fail_if_the_data_were_noisier(monkeypatch):
    real = data_catalog.get_entry("puromycin_treloar_1974")
    tampered = json.loads(json.dumps(real))
    for row in tampered["rows"]:
        if row[2] == "treated" and row[0] == 1.10:
            row[1] += 120  # a gross disagreement at the highest concentration
    monkeypatch.setattr(data_catalog, "get_entry", lambda entry_id: tampered)
    assert data_validation.run("michaelis_menten_puromycin_treated")["verdict"] == "not_validated"


def test_maturity_claim_requires_and_has_sourced_data():
    m = maturity.maturity_of("enzyme_kinetics")
    assert m["level"] == "validated_on_data" and any(ev["kind"] == "data" and ev["dataset_source"] for ev in m["evidence"])
    assert maturity.check_claims() == []
    bio = next(d for d in domains.all_domains() if d["id"] == "quantitative_biology")
    assert bio["validation_status"]["counts"]["validated_on_data"] == 1


def test_validations_api():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/api/validations", timeout=20) as resp:
            data = json.loads(resp.read())
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert data["results"][0]["verdict"] == "validated" and "Valid for this dataset" in data["results"][0]["scope"]
