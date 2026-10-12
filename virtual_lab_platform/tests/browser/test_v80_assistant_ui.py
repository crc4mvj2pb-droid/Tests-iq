"""v8.0 — the assistant panel shows tool results, their trace, and refuses to answer out of scope."""
from __future__ import annotations


def test_assistant_panel(page, evidence):
    page.fill("#asQuestion", "Quelle est la constante de temps d'un circuit RC avec R = 2 kΩ et C = 3 µF ?")
    page.click("#asAsk")
    page.wait_for_selector("#asAnswer [data-as-calls]")
    text = page.inner_text("#asAnswer")
    assert "time_constant = 0.006 s [c1]" in text and "run_model" in text and page.locator('#asAnswer [role="alert"]').count() == 0
    page.fill("#asQuestion", "Quelle dose de chimiothérapie pour ce patient ?")
    page.click("#asAsk")
    page.wait_for_selector('#asAnswer [data-as-status="out_of_scope"]')
    assert page.locator("#asAnswer [data-as-calls]").count() == 0
    evidence("Assistant relié aux outils", "Question RC puis question médicale", "Valeur tracée [c1] avec l'appel d'outil ; refus hors périmètre",
             text.splitlines()[1][:120])
