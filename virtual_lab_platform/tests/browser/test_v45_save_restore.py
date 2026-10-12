"""v4.5 — verification levels, replay comparison, history export/import and workspace import in the browser."""
from __future__ import annotations

import json
from pathlib import Path

import history


def _wait_message(page, record, prefix_options):
    js = " || ".join(f"t.includes({json.dumps(p)})" for p in prefix_options)
    page.wait_for_function(f"(()=>{{const m=document.querySelector('[data-history-message=\"{record}\"]');const t=m?m.textContent:'';return {js};}})()")
    return page.inner_text(f'[data-history-message="{record}"]')


def test_full_verification_and_replay_comparison_are_shown(page, bench, evidence):
    bench.reference_circuit(); bench.solve()
    record = bench.history()[0]["id"]
    page.click(f'[data-history-verify="{record}"]')
    verified = _wait_message(page, record, ["✓", "⚠"])
    assert "Dossier complet vérifié" in verified
    page.click(f'[data-history-replay="{record}"]')
    replayed = _wait_message(page, record, ["Replayed", "failed"])
    assert "résultats identiques" in replayed
    evidence("Vérification complète et comparaison du rejeu", "Vérifier puis rejouer le dossier du circuit de référence",
             "« Dossier complet vérifié » ; rejeu identique à la tolérance près", f"{verified} | {replayed}")


def test_history_export_then_import_into_an_empty_database(page, bench, evidence, tmp_path, monkeypatch):
    bench.reference_circuit(); bench.solve(); bench.solve()
    with page.expect_download() as info:
        page.click("#exportHistory")
    exported = Path(info.value.path())
    assert json.loads(exported.read_text(encoding="utf-8"))["record_count"] == 2
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "empty.sqlite3")
    page.click("#refreshHistory")
    page.set_input_files("#importHistoryFile", str(exported))
    page.wait_for_function("document.querySelector('#historyStatus').textContent.includes('importé')")
    status = page.inner_text("#historyStatus")
    assert "2 dossier(s) importé(s)" in status and len(bench.history()) == 2
    page.set_input_files("#importHistoryFile", str(exported))
    page.wait_for_function("document.querySelector('#historyStatus').textContent.includes('déjà présent')")
    again = page.inner_text("#historyStatus")
    assert "0 dossier(s) importé(s), 2 déjà présent(s)" in again
    evidence("Export puis import de l'historique", "Exporter 2 dossiers, vider la base, importer deux fois le fichier",
             "2 importés puis 0 importé / 2 déjà présents", f"{status} | {again}")


def test_altered_history_file_is_refused(page, bench, evidence, tmp_path):
    bench.reference_circuit(); bench.solve()
    bundle = page.request.get(page.base_url + "/api/history/export").json()
    bundle["records"][0]["dossier"]["source_current_a"] = 42
    altered = tmp_path / "altered.json"; altered.write_text(json.dumps(bundle), encoding="utf-8")
    page.set_input_files("#importHistoryFile", str(altered))
    page.wait_for_function("document.querySelector('#historyStatus').textContent.includes('refusé')")
    status = page.inner_text("#historyStatus")
    assert "dossier_hash" in status and len(bench.history()) == 1
    evidence("Fichier d'historique altéré", "Modifier un résultat dans l'export puis l'importer", "Import refusé, aucun dossier ajouté", status)


def test_workspace_file_import_restores_a_solvable_circuit(page, bench, evidence):
    bench.reference_circuit()
    with page.expect_download() as info:
        page.click("#wbExport")
    saved = Path(info.value.path())
    page.click("#wbClear")
    page.wait_for_function("document.querySelectorAll('#wbBench [data-instance]').length === 0")
    page.set_input_files("#wbImportFile", str(saved))
    page.wait_for_function("document.querySelectorAll('#wbBench [data-instance]').length === 3")
    page.click('#wbTabs [data-cat="electrical"]')
    state = bench.export_state()
    assert len(state["connections"]) == 3 and "0.0090000 A" in bench.solve()
    evidence("Import d'une paillasse", "Exporter, vider, importer le fichier, résoudre", "3 composants, 3 fils, I = 9 mA", f"{len(state['items'])} composants, {len(state['connections'])} fils")
