"""v5.9 — multi-model experiments: inconsistent operating conditions between steps are reported (v5.8 criterion completed)."""
from __future__ import annotations

import copy

import pipelines
from pipelines import run_pipeline


def example(name):
    return copy.deepcopy(pipelines.example_pipelines()[name])


def test_examples_bind_their_conditions_and_raise_no_warning():
    for name in pipelines.example_pipelines():
        assert not [w for w in run_pipeline(example(name))["warnings"] if w["code"] == "inconsistent_conditions"], name


def test_two_temperatures_in_one_experiment_are_reported():
    spec = example("temperature_kinetics_absorbance")
    spec["steps"][1]["bind"] = spec["steps"][1]["bind"][:1]  # kinetics keeps its default 298.15 K while Arrhenius used 310 K
    warnings = [w for w in run_pipeline(spec)["warnings"] if w["code"] == "inconsistent_conditions"]
    assert len(warnings) == 1 and warnings[0]["condition"] == "temperature_k"
    assert {(v["step"], v["value"]) for v in warnings[0]["values"]} == {("arrhenius", 310.0), ("kinetics", 298.15)}


def test_adapter_temperature_counts_as_a_condition():
    spec = example("joule_heating_kinetics")
    spec["steps"][3]["bind"] = spec["steps"][3]["bind"][:1]
    warning = next(w for w in run_pipeline(spec)["warnings"] if w["code"] == "inconsistent_conditions")
    assert {v["step"] for v in warning["values"]} == {"heating", "arrhenius", "kinetics"} and "298.15" in warning["message"]


def test_different_concentration_units_are_reported():
    spec = example("temperature_kinetics_absorbance")
    second = copy.deepcopy(spec["steps"][1]); second["id"] = "kinetics_mm"; second["inputs"]["concentration_unit"] = "mmol/L"
    spec["steps"].insert(2, second)
    warning = next(w for w in run_pipeline(spec)["warnings"] if w["code"] == "inconsistent_conditions")
    assert warning["condition"] == "concentration_unit"
