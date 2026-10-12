"""v6.3 — model fitting: published estimates reproduced, diagnostics, separate validation data, extrapolation flagged."""
from __future__ import annotations

import json
import math
import random
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import data_catalog
import experiment_service
import fitting
import history
from fitting import FitError


def _published(dataset_id):
    entry = data_catalog.get_entry(dataset_id)
    return entry, entry["published_analyses"][0]


def test_puromycin_fit_reproduces_bates_and_watts():
    entry, pub = _published("puromycin_treloar_1974")
    x = data_catalog.column_values(entry, "conc", {"state": "treated"})
    y = data_catalog.column_values(entry, "rate", {"state": "treated"})
    r = fitting.fit({"model": "michaelis_menten", "x": x, "y": y, "x_unit": "ppm", "y_unit": "counts/min/min"})
    for name, ref in pub["estimates"].items():
        assert r["parameters"][name]["value"] == pytest.approx(ref["value"], rel=5e-4), name  # published to 4 significant digits
        assert r["parameters"][name]["standard_error"] == pytest.approx(ref["standard_error"], rel=5e-4), name
        assert r["parameters"][name]["unit"] == ref["unit"]
    assert r["residual_standard_error"] == pytest.approx(pub["residual_standard_error"], rel=5e-4) and r["degrees_of_freedom"] == pub["degrees_of_freedom"]


def test_bod_fit_reproduces_the_published_estimates():
    entry, pub = _published("bod_marske_1967")
    r = fitting.fit({"model": "first_order_rise", "x": data_catalog.column_values(entry, "time"), "y": data_catalog.column_values(entry, "demand"),
                     "x_unit": "d", "y_unit": "mg/L"})
    assert r["parameters"]["A"]["value"] == pytest.approx(19.1426, rel=1e-4) and r["parameters"]["A"]["standard_error"] == pytest.approx(2.4959, rel=1e-4)
    assert r["parameters"]["k"]["value"] == pytest.approx(math.exp(-0.6328), rel=2e-4)
    assert r["parameters"]["k"]["standard_error"] == pytest.approx(pub["estimates"]["k"]["standard_error"], rel=2e-3)
    assert r["parameters"]["k"]["unit"] == "1/d" and r["residual_standard_error"] == pytest.approx(2.549, rel=2e-4)


@pytest.mark.parametrize("model,true,xs", [
    ("michaelis_menten", [10.0, 2.0], [0.5, 1, 2, 4, 8, 16]),
    ("first_order_rise", [5.0, 0.3], [1, 2, 4, 6, 10, 15]),
    ("exponential_decay", [3.0, 0.7], [0, 0.5, 1, 2, 3, 5]),
    ("linear", [1.5, -0.25], [0, 1, 2, 3, 4]),
    ("logistic", [100.0, 5.0, 0.8], [0, 2, 4, 6, 8, 10, 14]),
    ("arrhenius", [1e7, 50000.0], [280, 300, 320, 340, 360]),
    ("power_law", [2.0, 1.5], [1, 2, 3, 5, 8]),
])
def test_noise_free_data_return_the_true_parameters(model, true, xs):
    f = fitting.MODELS[model]["f"]
    r = fitting.fit({"model": model, "x": xs, "y": [f(x, true) for x in xs], "x_unit": "K" if model == "arrhenius" else "s"})
    for name, value in zip(fitting.MODELS[model]["params"], true):
        assert r["parameters"][name]["value"] == pytest.approx(value, rel=1e-6), (model, name)


def test_t_quantiles_match_statistical_tables():
    assert fitting.t_quantile(0.975, 10) == pytest.approx(2.228139, abs=1e-6)
    assert fitting.t_quantile(0.975, 4) == pytest.approx(2.776445, abs=1e-6)
    assert fitting.t_quantile(0.975, 1e6) == pytest.approx(1.959966, abs=1e-5)


def test_confidence_intervals_have_their_nominal_coverage():
    rng, hits, trials = random.Random(3), 0, 400
    xs = [0, 1, 2, 3, 4, 5, 6, 7]
    for _ in range(trials):
        ys = [2.0 + 0.5 * x + rng.gauss(0, 0.3) for x in xs]
        lo, hi = fitting.fit({"model": "linear", "x": xs, "y": ys})["parameters"]["b"]["ci95"]
        hits += lo <= 0.5 <= hi
    assert 0.92 <= hits / trials <= 0.98, hits / trials  # binomial 95 % band for p = 0.95, n = 400


def test_wrong_model_form_shows_in_the_residual_diagnostics():
    xs = [i * 0.5 for i in range(20)]
    r = fitting.fit({"model": "linear", "x": xs, "y": [math.exp(0.4 * x) for x in xs]})
    assert r["diagnostics"]["durbin_watson"] < 1.0 and r["diagnostics"]["runs_test"]["z"] < -2


def test_validation_points_are_not_used_for_the_estimates():
    entry = data_catalog.get_entry("puromycin_treloar_1974")
    x = data_catalog.column_values(entry, "conc", {"state": "treated"})
    y = data_catalog.column_values(entry, "rate", {"state": "treated"})
    held = [1, 3, 5, 7, 9, 11]  # second replicate at each concentration
    a = fitting.fit({"model": "michaelis_menten", "x": x, "y": y, "validation": {"method": "indices", "indices": held}})
    y2 = list(y); y2[1] += 1000.0
    b = fitting.fit({"model": "michaelis_menten", "x": x, "y": y2, "validation": {"method": "indices", "indices": held}})
    assert a["parameters"]["Vm"]["value"] == b["parameters"]["Vm"]["value"] and a["fit_points"] == 6
    assert a["validation"]["points"] == 6 and b["validation"]["rmse"] > a["validation"]["rmse"]
    alt = fitting.fit({"model": "michaelis_menten", "x": x, "y": y, "validation": {"method": "alternate"}})
    assert alt["validation"]["indices"] == held and alt["parameters"]["Vm"]["value"] == a["parameters"]["Vm"]["value"]
    h = fitting.fit({"model": "michaelis_menten", "x": x, "y": y, "validation": {"method": "holdout", "fraction": 0.25, "seed": 4}})
    assert h["validation"]["points"] == 3 and h["fit_points"] == 9


def test_extrapolation_is_flagged():
    r = fitting.fit({"model": "linear", "x": [1, 2, 3, 4], "y": [2, 4.1, 5.9, 8]})
    flags = [p["extrapolation"] for p in fitting.predict(r, [0.5, 1, 2.5, 4, 10])]
    assert flags == [True, False, False, False, True]


def test_strongly_correlated_parameters_are_warned():
    xs = [10, 11, 12, 13]  # MM far below saturation: Vm and K poorly separated
    r = fitting.fit({"model": "michaelis_menten", "x": [0.01, 0.02, 0.03, 0.04], "y": [1.0, 2.01, 2.98, 4.02]})
    assert any(w["code"] == "highly_correlated_parameters" for w in r.get("warnings", []))
    assert xs


@pytest.mark.parametrize("request_,code", [
    ({"model": "spline", "x": [1, 2, 3], "y": [1, 2, 3]}, "unknown_model"),
    ({"model": "linear", "x": [1, 2], "y": [1, 2]}, "too_few_points"),
    ({"model": "linear", "x": [1, 2, None], "y": [1, 2, 3]}, "invalid_data"),
    ({"model": "linear", "x": [1, 2, 3], "y": [1, 2]}, "invalid_data"),
    ({"model": "linear", "x": [2, 2, 2, 2], "y": [1, 2, 3, 4]}, "not_identifiable"),
    ({"model": "arrhenius", "x": [1, 2, 3, 4], "y": [1, 2, 3, 4], "x_unit": "s"}, "incompatible_unit"),
    ({"model": "linear", "x": [1, 2, 3, 4], "y": [1, 2, 3, 4], "x_unit": "parsecs"}, "invalid_unit"),
    ({"model": "linear", "x": [1, 2, 3, 4], "y": [1, 2, 3, 4], "validation": {"method": "indices", "indices": [9]}}, "invalid_split"),
])
def test_invalid_requests_are_refused(request_, code):
    with pytest.raises(FitError) as exc:
        fitting.fit(request_)
    assert exc.value.code == code


def test_fit_from_catalogue_is_saved_and_replayed(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v63.sqlite3")
    d = experiment_service.run_fit({"dataset_id": "puromycin_treloar_1974", "x_column": "conc", "y_column": "rate", "where": {"state": "treated"},
                                    "model": "michaelis_menten"})
    assert d["model_id"] == "model_fit" and d["data"]["content_sha256"] == data_catalog.get_entry("puromycin_treloar_1974")["content_sha256"]
    assert d["data"]["data_kind"] == "experimental" and d["x_unit"] == "ppm"
    replay = experiment_service.replay(d["history_record"]["id"])
    assert replay["replay_comparison"]["identical_within_tolerance"]


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v63api.sqlite3")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_fit_api(base):
    code, d = post(base + "/api/data/fit", {"dataset_id": "bod_marske_1967", "x_column": "time", "y_column": "demand", "model": "first_order_rise"})
    assert code == 200 and d["parameters"]["A"]["unit"] == "mg/L" and d["history_record"]["id"] > 0
    code, err = post(base + "/api/data/fit", {"dataset_id": "bod_marske_1967", "x_column": "nope", "y_column": "demand", "model": "linear"})
    assert code == 400 and err["error_code"] == "unknown_column"
