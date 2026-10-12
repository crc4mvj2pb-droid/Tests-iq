"""v8.1 — formulating a research question from the assistant panel."""
from __future__ import annotations


def test_formulation_panel(page, evidence):
    page.fill("#asQuestion", "Quel est l'effet de la résistance sur la constante de temps ?")
    page.click("#asFormulate")
    page.wait_for_selector('#asAnswer [data-rq-status="formulated"]')
    text = page.inner_text("#asAnswer")
    assert "resistance_ohm" in text and "time_constant" in text and "H0" in text
    page.fill("#asQuestion", "Effet de la couleur sur la constante de temps")
    page.click("#asFormulate")
    page.wait_for_selector('#asAnswer [data-rq-status="clarification_needed"]')
    evidence("Formulation d'une question de recherche", "« Effet de la résistance sur la constante de temps » puis une variable inconnue",
             "Variables, hypothèses H1/H2/H0 et critère ; demande de précision sinon", text.splitlines()[1][:120])
