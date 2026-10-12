"""v9.2 — diagnostics panel."""
from __future__ import annotations


def test_diagnostics_panel(page, evidence):
    page.click("#bkDiag")
    page.wait_for_selector("#bkList [data-diag]")
    text = page.inner_text("#bkList [data-diag]")
    assert "Mode récupération" in text and "non" in text and "intègre" in text
    evidence("Diagnostic de l'installation", "Bouton « Diagnostic »", "Versions, état de la base, sauvegardes, requêtes, espace disque", text.replace("\n", " ")[:160])
