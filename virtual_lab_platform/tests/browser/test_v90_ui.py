"""v9.0 — backups from the interface."""
from __future__ import annotations


def test_create_and_verify_a_backup(page, bench, evidence):
    bench.reference_circuit(); bench.solve()
    page.click("#bkCreate")
    page.wait_for_function("document.querySelector('#bkStatus').textContent.startsWith('Sauvegarde créée')")
    page.locator("[data-bk-verify]").first.click()
    page.wait_for_function("document.querySelector('#bkStatus').textContent.startsWith('Sauvegarde intacte')")
    status = page.inner_text("#bkStatus")
    assert "1 expériences" in status or "1 expérience" in status
    evidence("Sauvegarde depuis l'interface", "Résoudre un circuit, « Créer une sauvegarde », « Vérifier »", "Sauvegarde créée puis vérifiée intacte", status)
