"""v8.5 — iterative planning: next experiment by an explicit criterion, optimisation under constraints, plan comparison, decision log."""
from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import history
import iterative_planning as ip
import model_registry


def test_d_optimal_criterion_reproduces_duggleby_two_point_design():
    k, x_max, vm = 0.0641, 1.1, 212.7
    grid = [i * x_max / 20000 for i in range(1, 20000)]
    best = max(grid, key=lambda a: ip._det2([a, x_max], vm, k))
    assert best == pytest.approx(ip.duggleby_two_point_design(k, x_max)[0], rel=1e-3)


def test_next_measurement_on_puromycin_stays_in_range_unless_allowed():
    r = ip.next_measurement("puromycin_treloar_1974", "conc", "rate", {"state": "treated"})
    assert not r["proposal"]["extrapolation"] and r["proposal"]["det_gain"] == max(c["det_gain"] for c in r["candidates"] if not c["extrapolation"])
    assert "D-optimality" in r["criterion"] and r["current_points"] == 12
    wide = ip.next_measurement("puromycin_treloar_1974", "conc", "rate", {"state": "treated"}, allow_extrapolation=True)
    assert wide["proposal"]["extrapolation"] and wide["proposal"]["det_gain"] >= r["proposal"]["det_gain"]


def test_reach_target_finds_the_parameter_and_checks_it():
    r = ip.reach_target("Effet de la résistance sur la constante de temps", 4.7e-3)
    assert r["status"] == "found" and r["value"] == pytest.approx(4700.0, rel=1e-6)  # τ = R·C, C = 1 µF
    assert model_registry.run_model("rc_rl_step_response", {"resistance_ohm": r["value"]})["outputs"]["time_constant"]["value"] == pytest.approx(4.7e-3, rel=1e-6)


def test_constraints_are_respected_and_unreachable_targets_reported():
    bounded = ip.reach_target("Effet de la résistance sur la constante de temps", 4.7e-3, lower=100.0, upper=1000.0)
    assert bounded["status"] == "unreachable" and "outside the range" in bounded["reason"]
    assert ip.reach_target("Effet de la puissance sur la constante de temps", 30.0)["status"] == "unreachable"  # τ does not depend on P
    assert ip.reach_target("Effet de la couleur", 1.0)["status"] == "not_planned"


def test_plans_are_compared_by_a_stated_criterion():
    plans = [{"name": "A", "det_gain": 1.1}, {"name": "B", "det_gain": 1.3}]
    assert [p["name"] for p in ip.compare_plans(plans, "det_gain")] == ["B", "A"]
    with pytest.raises(ValueError):
        ip.compare_plans([{"name": "A"}], "det_gain")


def test_user_decisions_are_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v85.sqlite3")
    d = ip.record_decision("estimate K", [{"name": "x=0.06"}, {"name": "x=1.1"}], "x=0.06", "closest to the theoretical design")
    assert d["id"] == 1 and ip.decisions()[0]["chosen"] == "x=0.06"
    with pytest.raises(ValueError):
        ip.record_decision("estimate K", [{"name": "x=0.06"}], "x=9")


def test_api(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v85api.sqlite3")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    try:
        target = post("/api/research/target", {"question": "Effet de la résistance sur la constante de temps", "target": 0.002})
        nxt = post("/api/research/next-measurement", {"dataset_id": "puromycin_treloar_1974", "x_column": "conc", "y_column": "rate", "where": {"state": "treated"}})
        dec = post("/api/research/decisions", {"objective": "o", "alternatives": [{"name": "a"}, {"name": "b"}], "chosen": "b"})
        with urllib.request.urlopen(base + "/api/research/decisions", timeout=10) as resp:
            listed = json.loads(resp.read())
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)
    assert target["value"] == pytest.approx(2000.0, rel=1e-6) and nxt["proposal"] and dec["id"] == 1 and listed["decisions"][0]["chosen"] == "b"
