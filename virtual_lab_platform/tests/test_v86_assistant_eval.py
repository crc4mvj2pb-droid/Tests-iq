"""v8.6 — evaluation of the assistant on a fixed set: accuracy, hallucinations, traceability, abstention, 'unknown' cases."""
from __future__ import annotations

import hashlib

import pytest

import assistant
import assistant_eval
from scripts.run_assistant_eval import report

SET_SHA256 = "15c16c7624f8fa6b43926f19ef9227a35b905b245048372e6c2d76eac0775aec"  # fixed in v8.6 before the first run


def test_the_evaluation_set_is_unchanged():
    assert hashlib.sha256(assistant_eval.SET_PATH.read_bytes()).hexdigest() == SET_SHA256


def test_set_covers_unknown_out_of_scope_failures_and_hard_phrasings():
    cats = {c["category"] for c in assistant_eval.load_set()["cases"]}
    assert {"unknown", "out_of_scope", "tool_failure", "clarification", "numeric_hard", "hypothesis", "formulation"} <= cats


@pytest.fixture(scope="module")
def results():
    return assistant_eval.run()


def test_no_hallucination_and_full_traceability(results):
    assert results["hallucination_rate"] == 0.0 and results["traceability_rate"] == 1.0


def test_accuracy_does_not_regress_below_the_first_measured_run(results):
    assert results["passed"] >= 36 and results["cases"] == 39  # first run (v8.6): 36/39


def test_failures_are_abstentions_never_invented_values(results):
    for f in results["failures"]:
        assert not f.get("hallucination") and f["observed"].get("status") in ("unknown", "analyzed", "out_of_scope", "clarification_needed")


def test_expected_values_are_independent_of_the_assistant():
    assert assistant_eval.FORMULAS["rc_tau"](2000, 3e-6) == pytest.approx(6e-3)
    assert assistant_eval.FORMULAS["weak_acid_ph"](0.1, 4.756) == pytest.approx(2.88, abs=0.005)


def test_detector_counts_tool_errors_as_tool_outputs():
    r = assistant.answer("Constante de temps d'un circuit RC avec R = -5 Ω")
    assert r["status"] == "tool_failed" and assistant.untraced_numbers(r) == []


def test_report_states_rates_and_limits(results):
    text = report(results)
    assert "Taux d'hallucination" in text and "hypothesis_3" in text and "general scientific autonomy" in text
