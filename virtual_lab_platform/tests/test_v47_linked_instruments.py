"""v4.7 — simulated instrument readings linked to saved engine results, with units, uncertainty and provenance."""
from __future__ import annotations

import json
import math
import sqlite3

import pytest

import experiment_service
import history
from test_v45_dossiers import CIRCUIT, server  # noqa: F401  (fixture reuse)

KINETICS = {"species": [{"id": "A", "initial_concentration": 0.002, "atoms": {"X": 1}}, {"id": "B", "initial_concentration": 0.0, "atoms": {"X": 1}}],
            "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5}], "duration": 2, "dt": 0.01}


def _circuit(server):
    return server("/api/electrical/workbench-run", CIRCUIT)[1]


def test_quantities_and_compatible_instruments_are_listed(server):
    d = _circuit(server)
    q = server(f"/api/history/{d['history_record']['id']}/quantities")[1]
    keys = {x["key"]: x for x in q["quantities"]}
    assert keys["node_voltage:N1"]["value"] == pytest.approx(8.0) and keys["node_voltage:N1"]["unit"] == "V"
    assert keys["branch_current:resistor:r1"]["unit"] == "A"
    assert [i["id"] for i in q["instruments_by_unit"]["V"]] == ["dmm_dc_voltage"]
    assert [i["id"] for i in q["instruments_by_unit"]["A"]] == ["dmm_dc_current"]


def test_voltage_reading_uses_the_engine_value_and_records_provenance(server):
    d = _circuit(server)
    code, m = server("/api/instruments/measure-linked", {"source_experiment_id": d["history_record"]["id"], "quantity": "node_voltage:N1",
                                                         "instrument_id": "dmm_dc_voltage", "seed": 3})
    assert code == 200, m
    assert m["theoretical_value"] == pytest.approx(8.0) and m["experimental_data"] is False and m["data_status"] == "simulated_measurement"
    assert m["provenance"]["source_dossier_hash"] == d["dossier_hash"] and m["provenance"]["source_engine"] == d["engine"]
    sd = (0.005 * 8.0 + 0.002) / math.sqrt(3)
    budget = m["uncertainty_budget"]
    assert budget["instrument_standard_uncertainty"] == pytest.approx(sd)
    assert budget["combined_standard_uncertainty"] == pytest.approx(math.sqrt(sd**2 + (0.001 / math.sqrt(12))**2 + budget["reference_model_standard_uncertainty"]**2))
    assert abs(m["indicated_reading"] - 8.0) < 5 * budget["combined_standard_uncertainty"]
    assert server(f"/api/history/{m['history_record']['id']}/verify")[1]["level"] == "full"


def test_current_is_converted_from_ampere_to_milliampere(server):
    d = _circuit(server)
    m = server("/api/instruments/measure-linked", {"source_experiment_id": d["history_record"]["id"], "quantity": "branch_current:resistor:r1",
                                                   "instrument_id": "dmm_dc_current", "seed": 1})[1]
    assert m["unit"] == "mA" and m["theoretical_value"] == pytest.approx(4.0)
    assert m["linked_quantity"]["transform"] == {"type": "unit_conversion", "from": "A", "to": "mA", "factor": 1000.0}


def test_unit_mismatch_and_unknown_quantity_are_refused(server):
    record = _circuit(server)["history_record"]["id"]
    code, body = server("/api/instruments/measure-linked", {"source_experiment_id": record, "quantity": "node_voltage:N1", "instrument_id": "dmm_dc_current"})
    assert code == 400 and "Unit mismatch" in body["error"]
    code, body = server("/api/instruments/measure-linked", {"source_experiment_id": record, "quantity": "node_voltage:ZZ", "instrument_id": "dmm_dc_voltage"})
    assert code == 400 and "Unknown quantity" in body["error"]


def test_spectrophotometer_reads_kinetics_concentration_through_beer_lambert(server):
    k = server("/api/chemistry/kinetics-run", KINETICS)[1]
    record, c_final = k["history_record"]["id"], k["summary"]["final_concentrations"]["A"]
    code, m = server("/api/instruments/measure-linked", {"source_experiment_id": record, "quantity": "final_concentration:A", "instrument_id": "spectrophotometer",
                                                         "epsilon_l_per_mol_cm": 400.0, "path_length_cm": 1.0, "seed": 5})
    assert code == 200 and m["unit"] == "AU" and m["theoretical_value"] == pytest.approx(400.0 * c_final)
    assert m["linked_quantity"]["transform"]["type"] == "beer_lambert"
    code, body = server("/api/instruments/measure-linked", {"source_experiment_id": record, "quantity": "final_concentration:A", "instrument_id": "spectrophotometer"})
    assert code == 400 and "epsilon" in body["error"]
    code, high = server("/api/instruments/measure-linked", {"source_experiment_id": record, "quantity": "final_concentration:A", "instrument_id": "spectrophotometer",
                                                            "epsilon_l_per_mol_cm": 1e5, "path_length_cm": 1.0})
    assert code == 200 and high["warnings"][0]["code"] == "absorbance_out_of_linear_range"


def test_reading_replays_identically_and_refuses_a_modified_source(server):
    d = _circuit(server)
    m = server("/api/instruments/measure-linked", {"source_experiment_id": d["history_record"]["id"], "quantity": "node_voltage:N1", "instrument_id": "dmm_dc_voltage", "seed": 11})[1]
    code, replay = server(f"/api/history/{m['history_record']['id']}/replay", b"")
    assert code == 200 and replay["replay_comparison"]["identical_within_tolerance"]
    conn = sqlite3.connect(server.db)
    source = json.loads(conn.execute("SELECT dossier_json FROM experiments WHERE id=?", (d["history_record"]["id"],)).fetchone()[0])
    source["node_voltages_v"]["N1"] = 7.0
    conn.execute("UPDATE experiments SET dossier_json=? WHERE id=?", (json.dumps(source), d["history_record"]["id"])); conn.commit(); conn.close()
    assert server(f"/api/history/{m['history_record']['id']}/replay", b"")[0] == 409
    assert server("/api/instruments/measure-linked", {"source_experiment_id": d["history_record"]["id"], "quantity": "node_voltage:N1", "instrument_id": "dmm_dc_voltage"})[0] == 409


def test_expanded_uncertainty_has_about_95_percent_coverage(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "coverage.sqlite3")
    d = experiment_service.run_workbench(CIRCUIT)
    import linked_measurements
    inside = 0
    trials = 2000
    for seed in range(trials):
        m = linked_measurements.measure(d, {"quantity": "node_voltage:N1", "instrument_id": "dmm_dc_voltage", "seed": seed, "resolution": 0.0})
        inside += m["comparison"]["within_expanded_uncertainty"]
    # Gaussian noise with k=2 → 95.45 %; 2000 trials give a binomial standard error ≈ 0.47 %.
    assert 0.94 <= inside / trials <= 0.97
