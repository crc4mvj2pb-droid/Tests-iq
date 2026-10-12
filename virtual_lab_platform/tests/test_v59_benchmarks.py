"""v5.9 — independent benchmark: separate references, a-priori tolerances, negative results, generated report."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from benchmarks import independent_suite as suite
from scripts.run_benchmarks import report

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_IMPORTS = {"__future__", "math", "typing", "model_registry", "units"}


def test_suite_only_uses_public_interfaces():
    tree = ast.parse((ROOT / "benchmarks" / "independent_suite.py").read_text(encoding="utf-8"))
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imported <= ALLOWED_IMPORTS, imported - ALLOWED_IMPORTS


def test_no_unit_test_reuses_the_benchmark_references():
    users = [p.name for p in (ROOT / "tests").rglob("test_*.py") if "independent_suite" in p.read_text(encoding="utf-8") and p.name != Path(__file__).name]
    assert users == []


def test_cases_are_documented_and_cover_several_engines():
    ids = [c["id"] for c in suite.CASES]
    assert len(ids) == len(set(ids)) >= 30
    for c in suite.CASES:
        assert c["source"] and c["tolerance_basis"] and c["title"], c["id"]
        assert c["expectation"] in ("within_tolerance", "known_limit", "refused")
        assert c["reference_kind"] in ("analytical", "published_benchmark", "independent_solver")
        if c["expectation"] == "within_tolerance":
            assert c["tolerance"] is not None and c["tolerance"] >= 0
        if c["expectation"] == "known_limit":
            assert c["limit_threshold"] > 0
    assert len({c["model"] for c in suite.CASES}) >= 12 and len({c["domain"] for c in suite.CASES}) >= 6
    assert {c["reference_kind"] for c in suite.CASES} == {"analytical", "published_benchmark", "independent_solver"}
    assert sum(c["expectation"] != "within_tolerance" for c in suite.CASES) >= 4  # negative results are part of the suite


def _synthetic(**over):
    base = {"id": "x", "domain": "d", "model": "m", "title": "t", "reference_kind": "analytical", "source": "s", "tolerance": 1e-3, "relative": True,
            "tolerance_basis": "b", "expectation": "within_tolerance", "limit_threshold": None, "run": lambda: (1.0, 1.0)}
    return {**base, **over}


@pytest.mark.parametrize("case,status", [
    (_synthetic(), "pass"),
    (_synthetic(run=lambda: (1.01, 1.0)), "fail"),
    (_synthetic(run=lambda: 1 / 0), "error"),
    (_synthetic(expectation="refused", run=lambda: {"ok": 1}), "not_refused"),
    (_synthetic(expectation="refused", run=lambda: 1 / 0), "refused_as_expected"),
    (_synthetic(expectation="known_limit", limit_threshold=1e-2, tolerance=None, run=lambda: (1.05, 1.0)), "limit_reproduced"),
    (_synthetic(expectation="known_limit", limit_threshold=1e-2, tolerance=None, run=lambda: (1.001, 1.0)), "limit_changed"),
    (_synthetic(expectation="known_limit", limit_threshold=1e-2, tolerance=0.03, run=lambda: (1.05, 1.0)), "limit_changed"),
])
def test_outcome_classification_never_hides_a_failure(case, status):
    assert suite.run_case(case)["status"] == status


def test_reference_constants_are_exact_si_values():
    assert suite.R_GAS == pytest.approx(8.31446261815324, rel=1e-15)


@pytest.fixture(scope="module")
def results():
    return suite.run_suite()


def test_every_benchmark_case_has_its_expected_outcome(results):
    unexpected = [(r["id"], r["status"], r.get("deviation"), r.get("refusal")) for r in results if r["status"] not in suite.GOOD_STATUSES]
    assert unexpected == []
    statuses = {r["status"] for r in results}
    assert {"pass", "limit_reproduced", "refused_as_expected"} <= statuses


def test_report_shows_counts_negative_results_and_incidents(results):
    text = report(results)
    assert "tous les cas ont le résultat attendu" in text and f"**{len(results)} cas**" in text
    assert "Résultats négatifs et limites documentées" in text and "Incidents de la première exécution" in text
    assert "ngspice" in text  # states what could not be used
    broken = [dict(results[0], status="fail")] + results[1:]
    assert "AU MOINS UN CAS NE DONNE PAS LE RÉSULTAT ATTENDU" in report(broken)


def test_api_lists_the_benchmark_cases():
    import json
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer

    import app
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/api/benchmarks", timeout=10) as r:
            data = json.loads(r.read())
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert len(data["cases"]) == len(suite.CASES) and "run" not in data["cases"][0] and data["report_file"] == "BENCHMARK_REPORT_FR.md"
