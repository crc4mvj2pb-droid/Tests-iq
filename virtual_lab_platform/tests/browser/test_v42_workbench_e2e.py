"""v4.2 — end-to-end electrical workbench path, clicked in Chromium."""
from __future__ import annotations

import re

import pytest


def _metric(text, unit):
    match = re.search(r"([0-9.]+(?:e[-+]?\d+)?) " + re.escape(unit), text)
    return float(match.group(1)) if match else None


def test_reference_circuit_full_path(page, bench, evidence):
    src, res, gnd = bench.reference_circuit()
    state = bench.export_state()
    assert sorted(f"{x['id']}={x['qty']}" for x in state["items"]) == ["dc-source=9", "ground=0", "resistor=1000"]
    assert len(state["connections"]) == 3
    evidence("Paillasse : ajout, édition, câblage", "Ajouter source, résistance, masse ; saisir 9 V et 1000 Ω ; relier P–A, B–GND, N–GND",
             "3 composants, valeurs saisies, 3 fils", f"{len(state['items'])} composants, {len(state['connections'])} fils")

    text = bench.solve()
    current, power = _metric(text, "A"), _metric(text, "W")
    assert "Circuit CC calculé et enregistré" in text
    assert "0.0090000 A" in text and "0.081000 W" in text
    evidence("Calcul depuis l'interface", "Cliquer « Résoudre le circuit CC câblé »", "I = 0.0090000 A ; P = 0.081000 W",
             f"I = {current} A ; P = {power} W")

    records = bench.history()
    assert len(records) == 1 and records[0]["model_id"] == "electrical_workbench_dc"
    evidence("Enregistrement SQLite", "Lire /api/history après le calcul", "1 dossier electrical_workbench_dc", f"{len(records)} dossier(s)")

    original = records[0]["id"]
    page.click(f'[data-history-verify="{original}"]')
    page.wait_for_function(f"document.querySelector('[data-history-message=\"{original}\"]').textContent.startsWith('✓') || document.querySelector('[data-history-message=\"{original}\"]').textContent.startsWith('⚠')")
    verify_text = page.inner_text(f'[data-history-message="{original}"]')
    assert verify_text.startswith("✓")
    evidence("Vérification d'empreinte", "Cliquer « Verify integrity »", "Message ✓", verify_text)

    page.click(f'[data-history-replay="{original}"]')
    page.wait_for_function(f"(document.querySelector('[data-history-message=\"{original}\"]')||{{textContent:''}}).textContent.includes('Replayed')")
    page.wait_for_timeout(2000)
    replay_text = page.inner_text(f'[data-history-message="{original}"]')
    assert "Replayed as dossier #" in replay_text
    records = bench.history()
    assert len(records) == 2
    replay = page.request.get(f"{page.base_url}/api/history/{records[0]['id']}").json()
    first = page.request.get(f"{page.base_url}/api/history/{original}").json()
    assert replay["replay_of"] == original
    assert abs(replay["source_current_a"] - first["source_current_a"]) < 1e-12
    evidence("Rejeu", "Cliquer « Replay circuit » puis attendre 2 s", "Nouveau dossier replay_of = original ; |ΔI| < 1e-12 ; confirmation visible ≥ 2 s",
             f"{replay_text} ; replay_of = {replay['replay_of']} ; ΔI = {abs(replay['source_current_a'] - first['source_current_a'])}")

    page.click("#wbSave")
    page.reload()
    page.wait_for_function("document.querySelectorAll('#wbBench [data-instance]').length === 3")
    bench.page.click('#wbTabs [data-cat="electrical"]')
    restored = bench.export_state()
    assert len(restored["items"]) == 3 and len(restored["connections"]) == 3
    assert "0.0090000 A" in bench.solve()
    evidence("Sauvegarde et rechargement", "Enregistrer, recharger la page, résoudre à nouveau", "3 composants, 3 fils, même courant",
             f"{len(restored['items'])} composants, {len(restored['connections'])} fils, I = 0.0090000 A")

    resistor_after_reload = next(x["instanceId"] for x in restored["items"] if x["id"] == "resistor")
    page.click(f'[data-remove="{resistor_after_reload}"]')
    after_delete = bench.export_state()
    present = {x["instanceId"] for x in after_delete["items"]}
    orphans = [e for e in after_delete["connections"] if e["a"] not in present or e["b"] not in present]
    assert orphans == []
    evidence("Suppression", "Supprimer la résistance câblée", "0 fil orphelin", f"{len(orphans)} fil orphelin ; {len(after_delete['connections'])} fil restant")

    assert page.console_errors == []
    evidence("Console navigateur", "Parcours nominal complet", "0 erreur", f"{len(page.console_errors)} erreur(s)")


def test_double_click_creates_one_dossier(page, bench, evidence):
    bench.reference_circuit()
    page.dblclick("#wbSolveCircuit")
    page.wait_for_function("!document.querySelector('#wbSolveCircuit').disabled && document.querySelector('#wbResult h3').textContent.includes('calculé')")
    page.wait_for_timeout(500)
    count = len(bench.history())
    assert count == 1
    evidence("Double soumission", "Double-cliquer sur « Résoudre »", "1 dossier", f"{count} dossier(s)")


def _build(bench, case):
    s, r, g = bench.add("dc-source"), bench.add("resistor"), bench.add("ground")
    bench.set_value(r, 1000); bench.set_value(s, 9)
    if case == "source_short":
        bench.wire(s, "P", g, "GND"); bench.wire(s, "N", g, "GND"); bench.wire(r, "A", s, "P"); bench.wire(r, "B", g, "GND")
    elif case == "bypassed":
        # Two resistors in series; an ideal wire shunts only the first one.
        r2, w = bench.add("resistor"), bench.add("wire")
        bench.set_value(r2, 2000)
        bench.wire(s, "P", r, "A"); bench.wire(r, "B", r2, "A"); bench.wire(r2, "B", g, "GND"); bench.wire(s, "N", g, "GND")
        bench.wire(w, "A", r, "A"); bench.wire(w, "B", r, "B")
    elif case == "open_terminal":
        bench.wire(s, "P", r, "A"); bench.wire(s, "N", g, "GND")
    elif case == "two_sources":
        bench.add("battery")
        bench.wire(s, "P", r, "A"); bench.wire(r, "B", g, "GND"); bench.wire(s, "N", g, "GND")
    elif case == "capacitor":
        c = bench.add("capacitor")
        bench.wire(s, "P", r, "A"); bench.wire(r, "B", g, "GND"); bench.wire(s, "N", g, "GND"); bench.wire(c, "A", s, "P"); bench.wire(c, "B", g, "GND")


ERROR_CASES = {
    "source_short": "court-circuit",
    "bypassed": "shunt",
    "open_terminal": "pas câblée",
    "two_sources": "une seule source",
    "capacitor": "pas encore pris en charge",
}


@pytest.mark.parametrize("case", list(ERROR_CASES))
def test_topology_errors_are_explained_and_not_saved(page, bench, evidence, case):
    _build(bench, case)
    text = bench.solve()
    assert "Circuit non résolu" in text
    message = page.inner_text("#wbResult p")
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", message), "internal identifiers must not be shown"
    assert ERROR_CASES[case] in message.lower()
    assert len(bench.history()) == 0
    evidence(f"Erreur de topologie : {case}", "Construire le circuit invalide puis résoudre", "Message compréhensible, sans UUID, aucun dossier", message)


def test_network_failure_is_reported_and_not_saved(page, bench, evidence):
    bench.reference_circuit()
    page.route("**/api/electrical/workbench-run", lambda route: route.abort())
    text = bench.solve()
    message = page.inner_text("#wbResult p")
    assert "Circuit non résolu" in text
    assert "serveur local" in message
    page.unroute("**/api/electrical/workbench-run")
    evidence("Erreur réseau", "Couper la requête de calcul", "Message indiquant que le serveur local est injoignable", message)
