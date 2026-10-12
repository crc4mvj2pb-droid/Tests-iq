"""v4.6 — chemistry: validation, RK4 error estimate vs analytical solutions, saved/replayable dossiers."""
from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import history
from chemical_kinetics import ChemicalKineticsError, simulate_reaction_network
from reaction_stoichiometry import StoichiometryError, calculate_stoichiometry


def first_order(k, dt, duration=1.0):
    return {"species": [{"id": "A", "initial_concentration": 1.0, "atoms": {"X": 1}}, {"id": "B", "initial_concentration": 0.0, "atoms": {"X": 1}}],
            "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": k}], "duration": duration, "dt": dt}


@pytest.mark.parametrize("k,dt", [(1.0, 0.1), (2.0, 0.05), (5.0, 0.05), (15.0, 0.1), (0.3, 0.5)])
def test_error_estimate_tracks_the_true_rk4_error(k, dt):
    d = simulate_reaction_network(first_order(k, dt))
    true_error = abs(d["summary"]["final_concentrations"]["A"] - math.exp(-k))
    estimate = d["summary"]["estimated_final_error"]["A"]
    # Richardson is asymptotic: within a factor 2 in the resolved regime, conservative-or-close when coarse.
    assert 0.5 * true_error <= estimate <= 2.0 * true_error + 1e-16, (true_error, estimate)


def test_audit_case_coarse_step_is_now_flagged():
    # Audit v4.1: k·dt = 1.5 gave A(1) 18 % below exp(-15) with no warning.
    d = simulate_reaction_network(first_order(15.0, 0.1))
    warning = next(w for w in d["warnings"] if w["code"] == "coarse_time_step")
    assert "A" in warning["params"]["species"] and warning["params"]["relative_error"] > 0.1


def test_fine_step_has_no_accuracy_warning():
    d = simulate_reaction_network(first_order(1.0, 0.001))
    assert not [w for w in d["warnings"] if w["code"] == "coarse_time_step"]
    assert abs(d["summary"]["final_concentrations"]["A"] - math.exp(-1)) < 1e-12


def test_duplicate_reaction_ids_are_refused():
    req = first_order(1, 0.1); req["reactions"].append({"id": "r", "reactants": {"B": 1}, "products": {"A": 1}, "rate_constant": 1})
    with pytest.raises(ChemicalKineticsError, match="unique"):
        simulate_reaction_network(req)


def test_missing_formulas_are_signalled():
    req = first_order(1, 0.1)
    for sp in req["species"]:
        sp.pop("atoms")
    assert [w["code"] for w in simulate_reaction_network(req)["warnings"]] == ["atom_balance_not_checked"]


@pytest.mark.parametrize("formula", ["Xy", "Ab2", "Qq(OH)2"])
def test_unknown_elements_are_refused(formula):
    with pytest.raises(StoichiometryError, match="Unknown chemical element"):
        calculate_stoichiometry({"reactants": {"A": 1}, "products": {"B": 1},
                                 "species": [{"id": "A", "amount_mol": 1, "formula": formula}, {"id": "B", "amount_mol": 0, "formula": formula}]})


def test_real_elements_including_superheavy_are_accepted():
    d = calculate_stoichiometry({"reactants": {"A": 1}, "products": {"B": 1},
                                 "species": [{"id": "A", "amount_mol": 2, "formula": "OgTs"}, {"id": "B", "amount_mol": 0, "formula": "TsOg"}]})
    assert d["reaction_extent_mol"] == 2


def test_largest_kinetics_run_with_error_estimate_stays_fast():
    species = [{"id": f"S{i}", "initial_concentration": 1.0 if i == 0 else 0.0} for i in range(10)]
    reactions = [{"id": f"r{i}", "reactants": {f"S{i}": 1}, "products": {f"S{i+1}": 1}, "rate_constant": 0.5} for i in range(9)]
    started = time.perf_counter()
    d = simulate_reaction_network({"species": species, "reactions": reactions, "duration": 100, "dt": 0.01})
    assert time.perf_counter() - started < 20 and d["summary"]["estimated_final_error"] is not None


# ---- HTTP: saved, verifiable, replayable ----------------------------------------------------------

@pytest.fixture
def call(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v46.sqlite3")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def do(path, body=None):
        req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), method="POST" if body is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())
    try:
        yield do
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


STOICH = {"reaction_id": "water", "reaction_name": "2 H2 + O2 -> 2 H2O", "reactants": {"H2": 2, "O2": 1}, "products": {"H2O": 2},
          "species": [{"id": "H2", "amount_mol": 4, "formula": "H2"}, {"id": "O2", "amount_mol": 1, "formula": "O2"}, {"id": "H2O", "amount_mol": 0, "formula": "H2O"}]}


@pytest.mark.parametrize("path,body,model_id", [("/api/chemistry/kinetics-run", first_order(1.0, 0.01), "chemical_kinetics_network"),
                                                ("/api/chemistry/stoichiometry-run", STOICH, "chemical_stoichiometry")])
def test_chemistry_runs_are_saved_verified_and_replayed_identically(call, path, body, model_id):
    code, d = call(path, body)
    assert code == 200 and d["model_id"] == model_id and d["engine"]["version"]
    record = d["history_record"]["id"]
    assert call(f"/api/history/{record}/verify")[1]["level"] == "full"
    assert model_id in call("/api/history/replayable")[1]["models"]
    code, replay = call(f"/api/history/{record}/replay", {})
    c = replay["replay_comparison"]
    assert code == 200 and c["identical_within_tolerance"] and c["compared_values"] >= 4 and c["max_abs_difference"] == 0.0


def test_stoichiometry_result_values_in_dossier(call):
    d = call("/api/chemistry/stoichiometry-run", STOICH)[1]
    assert d["limiting_reactants"] == ["O2"] and d["reaction_extent_mol"] == 1 and d["product_amounts_theoretical_mol"]["H2O"] == 2


def test_invalid_chemistry_is_refused_and_not_saved(call):
    bad = json.loads(json.dumps(STOICH)); bad["products"] = {"H2O": 1}
    code, body = call("/api/chemistry/stoichiometry-run", bad)
    assert code == 400 and "not atom-balanced" in body["error"]
    assert call("/api/history")[1]["experiments"] == []
