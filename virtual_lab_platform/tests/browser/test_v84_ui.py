"""v8.4 — critical analysis from the assistant panel."""
from __future__ import annotations


def test_critical_analysis_panel(page, evidence):
    page.fill("#asQuestion", "Effet de la puissance sur la constante de temps")
    page.click("#asAnalyze")
    page.wait_for_selector('#asAnswer [data-ca-status="analyzed"]', timeout=60000)
    assert page.get_attribute("#asAnswer [data-ca-verdict]", "data-ca-verdict") == "H0"
    text = page.inner_text("#asAnswer")
    assert "Texte généré par règles" in text and "not validated on measured data" in text
    evidence("Analyse critique", "« Effet de la puissance sur la constante de temps » → Analyse critique",
             "H0 retenue dans le modèle ; sections séparées ; données manquantes listées", page.inner_text("#asAnswer [data-ca-verdict]")[:120])
