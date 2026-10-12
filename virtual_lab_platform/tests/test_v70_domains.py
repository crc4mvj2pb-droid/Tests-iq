"""v7.0 — domain architecture: limited scope, common interfaces, benchmark and derived validation status per domain."""
from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import app
import domains
import maturity
import model_registry


def test_domain_rules_hold():
    assert domains.problems() == []
    assert domains.plot_problems() == []


def test_every_contract_is_in_exactly_one_domain():
    owners = [m for d in domains.DOMAINS for m in d["models"]]
    assert sorted(owners) == sorted(c["id"] for c in model_registry.list_contracts())


def test_each_domain_has_scope_exclusions_benchmarks_and_a_derived_status():
    for d in domains.all_domains():
        assert d["scope"] and d["excluded"] and d["benchmark_cases"], d["id"]
        levels = [maturity.maturity_of(m["id"])["level"] for m in d["models"]]
        ranks = {l["id"]: l["rank"] for l in maturity.LEVELS}
        assert d["validation_status"]["lowest_level"] == min(levels, key=ranks.get)
        assert all(m["units"] for m in d["models"]), d["id"]


def test_a_missing_benchmark_or_unowned_model_is_detected(monkeypatch):
    broken = [dict(d) for d in domains.DOMAINS]
    broken[-1] = {**broken[-1], "models": []}
    monkeypatch.setattr(domains, "DOMAINS", broken)
    problems = domains.problems()
    assert f"domain {broken[-1]['id']}: no independent benchmark case" in problems
    assert "model environmental_decay: in no domain" in problems


def test_biomedical_domain_carries_its_disclaimer():
    bio = next(d for d in domains.all_domains() if d["id"] == "exploratory_biomedical")
    assert "conseil médical" in bio["disclaimer"] and "prédiction clinique" in bio["excluded"]


def test_domains_api():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/api/domains", timeout=20) as r:
            data = json.loads(r.read())
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert data["problems"] == [] and len(data["domains"]) == len(domains.DOMAINS)
    assert all(d["validation_status"]["statement"] for d in data["domains"])
