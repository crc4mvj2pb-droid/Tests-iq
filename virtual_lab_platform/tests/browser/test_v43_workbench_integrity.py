"""v4.3 — workbench state integrity: deletion, restore cleanup, invalid values, canonical state."""
from __future__ import annotations

import json


def _orphans(state):
    present = {x["instanceId"] for x in state["items"]}
    return [e for e in state["connections"] if e["a"] not in present or e["b"] not in present]


def _load_save(page, payload):
    page.evaluate("data => localStorage.setItem('vl-bench', JSON.stringify(data))", payload)
    page.reload()
    page.wait_for_function("document.querySelector('#apiConnectionStatus').textContent.includes('connectée')")


def _item(iid, item_id, **extra):
    return {"instanceId": iid, "id": item_id, "cat": "electrical", "displayName": iid, "qty": extra.pop("qty", 1), **extra}


def test_deleting_a_container_removes_contents_and_their_wires(page, bench, evidence):
    _load_save(page, {"workspace_schema": 3, "items": [
        {"instanceId": "box", "id": "beaker", "cat": "equipment", "displayName": "Bécher"},
        _item("r_in", "resistor", qty=100, parentInstanceId="box"), _item("r_out", "resistor", qty=100)],
        "connections": [{"a": "r_in", "pinA": "A", "b": "r_out", "pinB": "A"}]})
    page.click('[data-remove="box"]')
    state = bench.export_state()
    names = sorted(x["instanceId"] for x in state["items"])
    assert names == ["r_out"] and state["connections"] == [] and _orphans(state) == []
    evidence("Suppression d'un contenant", "Supprimer un bécher contenant une résistance câblée", "Contenu et fils supprimés, 0 orphelin",
             f"restant : {names} ; {len(state['connections'])} fil")


def test_restore_drops_and_reports_invalid_references(page, bench, evidence):
    _load_save(page, {"workspace_schema": 3, "items": [
        _item("s", "dc-source", qty=9), _item("r", "resistor", qty=1000), _item("r", "resistor", qty=5), {"id": "resistor"}],
        "connections": [{"a": "s", "pinA": "P", "b": "r", "pinB": "A"}, {"a": "r", "pinA": "A", "b": "s", "pinB": "P"},
                        {"a": "s", "pinA": "N", "b": "ghost", "pinB": "A"}, {"a": "s", "pinA": "Z", "b": "r", "pinB": "B"}]})
    message = page.inner_text("#wbResult")
    state = bench.export_state()
    assert len(state["items"]) == 2 and len(state["connections"]) == 1 and _orphans(state) == []
    for fragment in ("1 élément(s) invalide(s)", "1 identifiant(s) dupliqué(s)", "2 fil(s) orphelin(s) ou invalide(s)", "1 fil(s) en double"):
        assert fragment in message
    evidence("Restauration d'une sauvegarde altérée", "Charger une sauvegarde avec ID dupliqué, élément invalide, fils orphelins/invalides/en double",
             "Nettoyage et compte rendu visibles", message.replace("\n", " "))


def test_v42_browser_save_format_is_still_restored(page, bench, evidence):
    _load_save(page, {"version": 4, "lang": "fr", "question": "ancienne", "bench": [_item("s", "dc-source", qty=9), _item("r", "resistor", qty=1000), _item("g", "ground", qty=0)],
                      "connections": [{"a": "s", "pinA": "P", "b": "r", "pinB": "A", "kind": "ideal-wire", "resistance_ohm": 0},
                                      {"a": "r", "pinA": "B", "b": "g", "pinB": "GND"}, {"a": "s", "pinA": "N", "b": "g", "pinB": "GND"}]})
    assert "0.0090000 A" in bench.solve()
    evidence("Compatibilité des sauvegardes v4.0–v4.2", "Charger une sauvegarde au format {version:4, bench}", "Restaurée et calculable", "I = 0.0090000 A")


def test_empty_value_is_flagged_and_refused_without_saving(page, bench, evidence):
    src, res, gnd = bench.reference_circuit()
    bench.set_value(res, "")
    assert page.get_attribute("#wbPropQty", "aria-invalid") == "true"
    hint = page.inner_text("#wbPropQtyHint")
    bench.solve()
    message = page.inner_text("#wbResult p")
    assert "strictement positive" in message and len(bench.history()) == 0
    assert bench.export_state()["items"][1]["qty"] is None
    evidence("Valeur vide", "Effacer la valeur de la résistance puis résoudre", "Champ signalé, message clair, aucun dossier, valeur non convertie en 0",
             f"indice : {hint} | message : {message}")


def test_unsupported_components_are_visibly_marked(page, bench, evidence):
    cap, res = bench.add("capacitor"), bench.add("resistor")
    assert page.locator(f'[data-unsupported="{cap}"]').is_visible()
    assert page.locator(f'[data-unsupported="{res}"]').count() == 0
    evidence("Marquage des composants non calculés", "Ajouter un condensateur et une résistance", "Seul le condensateur est marqué", "condensateur marqué, résistance non marquée")


def test_duplicate_copies_values_without_wires(page, bench, evidence):
    src, res, gnd = bench.reference_circuit()
    page.click(f'[data-instance="{res}"] > strong')
    page.click("#wbDuplicate")
    state = bench.export_state()
    copies = [x for x in state["items"] if x["id"] == "resistor"]
    assert len(copies) == 2 and copies[0]["instanceId"] != copies[1]["instanceId"] and copies[1]["qty"] == 1000
    assert len(state["connections"]) == 3
    evidence("Duplication", "Dupliquer une résistance câblée", "Nouvelle instance, même valeur, aucun fil copié", f"{len(copies)} résistances, {len(state['connections'])} fils")


def test_clear_removes_every_wire(page, bench, evidence):
    bench.reference_circuit()
    page.click("#wbClear")
    page.wait_for_function("document.querySelectorAll('#wbBench [data-instance]').length === 0")
    page.click('#wbTabs [data-cat="electrical"]')
    src = bench.add("dc-source")
    state = bench.export_state()
    assert len(state["items"]) == 1 and state["connections"] == []
    evidence("Vider la paillasse", "Vider puis ajouter un composant", "Aucun fil résiduel", f"{len(state['connections'])} fil")


def test_saved_state_round_trips_identically(page, bench, evidence):
    bench.reference_circuit()
    exported = bench.export_state()
    page.click("#wbSave")
    page.reload()
    page.wait_for_function("document.querySelectorAll('#wbBench [data-instance]').length === 3")
    again = bench.export_state()
    assert again["items"] == exported["items"] and again["connections"] == exported["connections"]
    assert again["workspace_schema"] == 3
    evidence("Représentation canonique", "Exporter, sauvegarder, recharger, exporter", "Composants et fils identiques", "identiques" if again["items"] == exported["items"] else "différents")
