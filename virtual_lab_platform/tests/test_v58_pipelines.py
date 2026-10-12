"""v5.8 — multi-model experiments: unit-checked bindings, provenance per step, honest maturity."""
from __future__ import annotations

import copy
import json
import math
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import experiment_service
import history
import maturity
import pipelines
from constants import GAS_CONSTANT
from pipelines import PipelineError, run_pipeline


def example(name):
    return copy.deepcopy(pipelines.example_pipelines()[name])


def first_order_b(a0, k, t):
    return a0 * (1.0 - math.exp(-k * t))


def test_verified_chain_matches_the_analytical_composition():
    r = run_pipeline(example("temperature_kinetics_absorbance"))
    k = 1.0e7 * math.exp(-60000.0 / (GAS_CONSTANT * 310.0))
    b = first_order_b(0.002, k, 600.0)
    out = r["final_outputs"]
    assert out["arrhenius.rate_constant"]["value"] == pytest.approx(k, rel=1e-13) and out["arrhenius.rate_constant"]["unit"] == "1/s"
    assert out["kinetics.result:summary.final_concentrations.B|{concentration_unit}"]["value"] == pytest.approx(b, rel=1e-9)
    assert out["absorbance.absorbance"]["value"] == pytest.approx(500.0 * 1.0 * b, rel=1e-9)
    assert r["maturity"]["level"] == "verified" and r["warnings"] == []
    assert r["steps"][1]["inputs"]["temperature_k"] == 310.0  # the kinetics step records the temperature it was run at


def test_joule_heating_chain_is_computable_because_of_its_weakest_step():
    r = run_pipeline(example("joule_heating_kinetics"))
    power = 12.0 ** 2 / 48.0
    temperature = 298.15 + power * 4.0
    k = 1.0e7 * math.exp(-60000.0 / (GAS_CONSTANT * temperature))
    out = r["final_outputs"]
    assert out["circuit.total_resistor_power"]["value"] == pytest.approx(power, rel=1e-12)
    assert out["heating.temperature_k"]["value"] == pytest.approx(temperature, rel=1e-14)
    assert out["heating.thermal_time_constant_s"]["value"] == pytest.approx(20.0)
    assert out["arrhenius.rate_constant"]["value"] == pytest.approx(k, rel=1e-13)
    assert out["kinetics.result:summary.final_concentrations.B|{concentration_unit}"]["value"] == pytest.approx(first_order_b(0.002, k, 600.0), rel=1e-9)
    assert r["maturity"]["level"] == "computable" and r["maturity"]["limiting_steps"] == ["heating"]
    levels = {s["step"]: s["maturity"]["level"] for s in r["steps"]}
    assert levels == {"circuit": "verified", "heating": "computable", "arrhenius": "verified", "kinetics": "verified"}


def test_units_are_converted_between_steps():
    spec = example("temperature_kinetics_absorbance")
    kin = spec["steps"][1]["inputs"]
    kin["concentration_unit"] = "mmol/L"
    kin["species"][0]["initial_concentration"] = 2.0  # 2 mmol/L = 0.002 mol/L
    r = run_pipeline(spec)
    conversion = r["steps"][2]["conversions"][0]
    assert conversion["unit"] == "mmol/L" and conversion["converted_unit"] == "mol/L"
    assert conversion["converted_value"] == pytest.approx(conversion["value"] * 1e-3, rel=1e-15)
    reference = run_pipeline(example("temperature_kinetics_absorbance"))
    assert r["final_outputs"]["absorbance.absorbance"]["value"] == pytest.approx(reference["final_outputs"]["absorbance.absorbance"]["value"], rel=1e-9)


def test_incompatible_dimensions_are_refused():
    spec = example("temperature_kinetics_absorbance")
    spec["steps"][1]["bind"].append({"from": "arrhenius.rate_constant", "to": "species[0].initial_concentration"})
    with pytest.raises(PipelineError) as exc:
        run_pipeline(spec)
    assert exc.value.code == "incompatible_variables" and exc.value.params["source_unit"] == "1/s" and exc.value.params["target_unit"] == "mol/L"


def test_a_first_order_rate_constant_cannot_feed_a_second_order_reaction():
    spec = example("temperature_kinetics_absorbance")
    spec["steps"][1]["inputs"]["reactions"][0]["reactants"] = {"A": 2}
    with pytest.raises(PipelineError) as exc:
        run_pipeline(spec)
    assert exc.value.code == "incompatible_variables" and exc.value.params["target_unit"] == "(mol/L)^-1/s"


@pytest.mark.parametrize("mutate,code", [
    (lambda s: s["steps"][1]["bind"].__setitem__(0, {"from": "absorbance.absorbance", "to": "reactions[0].rate_constant"}), "invalid_binding"),  # later step
    (lambda s: s["steps"][1]["bind"].__setitem__(0, {"from": "nowhere.x", "to": "reactions[0].rate_constant"}), "invalid_binding"),
    (lambda s: s["steps"][1]["bind"].__setitem__(0, {"from": "arrhenius.not_an_output", "to": "reactions[0].rate_constant"}), "invalid_binding"),
    (lambda s: s["steps"][1]["bind"].__setitem__(0, {"from": "arrhenius.rate_constant", "to": "reactions[3].rate_constant"}), "invalid_binding"),
    (lambda s: s["steps"][1]["bind"].__setitem__(0, {"from": "arrhenius.rate_constant", "to": "species"}), "invalid_binding"),  # no unit: unchecked transfer
    (lambda s: s["steps"][2]["bind"].__setitem__(0, {"from": "kinetics.result:summary.final_concentrations.B", "to": "concentration_mol_l"}), "invalid_binding"),
    (lambda s: s["steps"][2]["bind"].__setitem__(0, {"from": "kinetics.result:summary.missing|mol/L", "to": "concentration_mol_l"}), "invalid_binding"),
    (lambda s: s["steps"][2].__setitem__("adapter", "not_an_adapter"), "unknown_adapter"),
    (lambda s: s["steps"][2].__setitem__("model", "arrhenius_reaction"), "invalid_pipeline"),  # both model and adapter
    (lambda s: s["steps"][2].__setitem__("id", "arrhenius"), "invalid_pipeline"),
    (lambda s: s.__setitem__("steps", s["steps"][:1]), "invalid_pipeline"),
    (lambda s: s["steps"][0]["inputs"].__setitem__("temperature_k", -3.0), "out_of_range"),
])
def test_invalid_pipelines_are_refused_with_a_code(mutate, code):
    spec = example("temperature_kinetics_absorbance")
    mutate(spec)
    with pytest.raises(PipelineError) as exc:
        run_pipeline(spec)
    assert exc.value.code == code


def test_timescale_mismatch_is_reported_only_for_dependent_dynamic_steps():
    spec = example("joule_heating_kinetics")
    assert run_pipeline(spec)["warnings"] == []  # τ_th = 20 s ≪ 600 s
    spec["steps"][3]["inputs"]["duration"] = 100.0
    warnings = run_pipeline(spec)["warnings"]
    assert [(w["code"], w["step"], w["source"]) for w in warnings] == [("timescale_mismatch", "kinetics", "heating")]


def test_absorbance_outside_the_linear_range_is_flagged():
    spec = example("temperature_kinetics_absorbance")
    spec["steps"][2]["inputs"]["epsilon_l_per_mol_cm"] = 5000.0
    r = run_pipeline(spec)
    assert any(w["code"] == "absorbance_out_of_linear_range" for w in r["warnings"])


def test_each_step_keeps_inputs_outputs_conversions_and_provenance():
    r = run_pipeline(example("temperature_kinetics_absorbance"))
    kinetics = r["steps"][1]
    assert kinetics["inputs"]["reactions"][0]["rate_constant"] == r["steps"][0]["outputs"]["rate_constant"]["value"]
    assert kinetics["provenance"]["engine"] and kinetics["model_version"] and kinetics["assumptions"]
    assert [c["to"] for c in kinetics["conversions"]] == ["reactions[0].rate_constant", "temperature_k"]
    absorbance = r["steps"][2]
    assert absorbance["kind"] == "adapter" and absorbance["equations"] == ["A = ε·l·c"]
    assert r["engine"] == {"id": "multi_model_pipeline", "version": pipelines.ENGINE_VERSION}
    # the original input specification is not modified
    spec = example("temperature_kinetics_absorbance")
    run_pipeline(spec)
    assert spec == example("temperature_kinetics_absorbance")


def test_adapter_maturity_claims_are_backed_by_existing_tests():
    for name, adapter in pipelines.ADAPTERS.items():
        level = adapter["maturity"]["level"]
        assert level in maturity.LEVEL_IDS
        if level == "verified":
            assert adapter["maturity"]["evidence"] and all(maturity._test_exists(ev["test"]) for ev in adapter["maturity"]["evidence"])


def test_pipeline_is_saved_verified_and_replayed(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v58.sqlite3")
    d = experiment_service.run_pipeline(example("joule_heating_kinetics"))
    record_id = d["history_record"]["id"]
    assert d["model_id"] == "multi_model_pipeline" and d["configuration"]["steps"][0]["model"] == "dc_resistive_network"
    assert experiment_service.verify(record_id)["level"] == "full"
    replay = experiment_service.replay(record_id)
    comparison = replay["replay_comparison"]
    assert comparison["identical_within_tolerance"] and comparison["compared_values"] >= 10 and not comparison["engine_changed"]


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v58api.sqlite3")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def call(url, body=None):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_api_examples_run_and_errors(base):
    code, catalogue = call(base + "/api/pipelines/examples")
    assert code == 200 and set(catalogue["examples"]) == {"temperature_kinetics_absorbance", "joule_heating_kinetics"}
    assert "function" not in catalogue["adapters"]["beer_lambert"] and catalogue["adapters"]["beer_lambert"]["outputs"] == {"absorbance": "1"}
    code, d = call(base + "/api/pipelines/run", catalogue["examples"]["temperature_kinetics_absorbance"])
    assert code == 200 and d["history_record"]["id"] > 0 and d["maturity"]["level"] == "verified"
    code, replay = call(f"{base}/api/history/{d['history_record']['id']}/replay", {})
    assert code == 200 and replay["replay_comparison"]["identical_within_tolerance"]
    bad = copy.deepcopy(catalogue["examples"]["temperature_kinetics_absorbance"])
    bad["steps"][1]["inputs"]["reactions"][0]["reactants"] = {"A": 2}
    code, err = call(base + "/api/pipelines/run", bad)
    assert code == 400 and err["error_code"] == "incompatible_variables"
