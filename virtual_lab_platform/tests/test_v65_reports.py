"""v6.5 — scientific reports: method, parameters, results, uncertainties, sources; observations, calculations,
interpretation and conclusions kept apart; nothing invented."""
from __future__ import annotations

import re
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app
import experiment_service
import history
import reports

KINETICS = {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
            "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5}], "duration": 4.0, "dt": 0.1,
            "question": "Quelle fraction de A reste après 4 s ?"}
ORDER = ["Question et objet", "Méthode", "Paramètres", "Observations (données mesurées ou importées)", "Calculs (valeurs produites par le moteur)",
         "Incertitudes", "Hypothèses et limites", "Interprétation (règles automatiques, à vérifier)", "Conclusions", "Références", "Traçabilité"]


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "v65.sqlite3")


def section(report, title):
    return dict(report["sections"])[title]


def test_kinetics_report_structure_and_content(db):
    d = experiment_service.run_kinetics(KINETICS)
    r = reports.build(d["history_record"]["id"])
    assert [t for t, _ in r["sections"]] == ORDER
    assert "Quelle fraction de A reste après 4 s ?" in " ".join(section(r, "Question et objet"))
    assert section(r, "Observations (données mesurées ou importées)") == ["Aucune donnée observée : ce dossier ne contient que des calculs."]
    final_a = d["summary"]["final_concentrations"]["A"]
    assert any(f"A = {final_a:.6g}" in line for line in section(r, "Calculs (valeurs produites par le moteur)"))
    assert section(r, "Conclusions")[0].startswith("À rédiger par le chercheur")
    assert section(r, "Interprétation (règles automatiques, à vérifier)")[0].startswith("Les phrases ci-dessous sont produites par des règles fixes")
    refs = " ".join(section(r, "Références"))
    assert "Guldberg" in refs and "Arrhenius" in refs
    assert any(d["dossier_hash"] in line for line in section(r, "Traçabilité")) and any(line.endswith("saved") for line in section(r, "Traçabilité"))


def test_fit_report_separates_observations_from_calculations(db):
    d = experiment_service.run_fit({"dataset_id": "puromycin_treloar_1974", "x_column": "conc", "y_column": "rate", "where": {"state": "treated"},
                                    "model": "michaelis_menten", "validation": {"method": "alternate"}})
    r = reports.build(d["history_record"]["id"])
    obs = " ".join(section(r, "Observations (données mesurées ou importées)"))
    assert "puromycin_treloar_1974" in obs and "mesure expérimentale publiée" in obs and '"state": "treated"' in obs
    calc = " ".join(section(r, "Calculs (valeurs produites par le moteur)"))
    vm = d["parameters"]["Vm"]
    assert f"Vm = {vm['value']:.6g} ± {vm['standard_error']:.6g} counts/min/min" in calc
    interp = " ".join(section(r, "Interprétation (règles automatiques, à vérifier)"))
    assert "points non utilisés pour l'ajustement" in interp
    refs = " ".join(section(r, "Références"))
    assert "Treloar" in refs and "Bates" in refs and "Michaelis" in refs
    assert "s²(JᵀJ)⁻¹" in " ".join(section(r, "Incertitudes"))


def test_numbers_in_the_calculations_come_from_the_dossier(db):
    d = experiment_service.run_fit({"dataset_id": "bod_marske_1967", "x_column": "time", "y_column": "demand", "model": "first_order_rise"})
    r = reports.build(d["history_record"]["id"])
    dossier_numbers = {f"{v:.6g}" for v in _numbers(d)}
    for line in section(r, "Calculs (valeurs produites par le moteur)"):
        for token in re.findall(r"-?\d+\.\d+(?:e[-+]\d+)?", line):
            assert token in dossier_numbers, (token, line)


def _numbers(value):
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, dict):
        return [n for v in value.values() for n in _numbers(v)]
    if isinstance(value, list):
        return [n for v in value for n in _numbers(v)]
    return []


def test_markdown_and_self_contained_html(db):
    d = experiment_service.run_kinetics(KINETICS)
    r = reports.build(d["history_record"]["id"])
    md = reports.to_markdown(r)
    assert md.startswith("# Rapport — ") and "## Données de base du graphique" in md and "| time | A | B |" in md
    page = reports.to_html(r)
    assert page.startswith("<!doctype html>") and "<svg" in page and "<polyline" in page
    assert not re.search(r"(src|href)=\"https?:", page) and "<script" not in page  # no external resource, no script


def test_unknown_experiment():
    with pytest.raises(reports.ReportError) as exc:
        reports.build(987654)
    assert exc.value.code == "not_found"


@pytest.fixture
def base(db):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown(); srv.server_close(); thread.join(timeout=3)


def test_report_api(base):
    d = experiment_service.run_kinetics(KINETICS)
    eid = d["history_record"]["id"]
    with urllib.request.urlopen(f"{base}/api/history/{eid}/report.md", timeout=10) as r:
        assert r.headers["Content-Type"].startswith("text/markdown") and r.read().decode().startswith("# Rapport")
    with urllib.request.urlopen(f"{base}/api/history/{eid}/report.html", timeout=10) as r:
        assert r.headers["Content-Type"].startswith("text/html") and "<svg" in r.read().decode()
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/api/history/424242/report.html", timeout=10)
    assert exc.value.code == 404
