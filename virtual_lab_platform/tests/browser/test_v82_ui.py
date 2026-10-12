"""v8.2 — protocol design from the assistant panel."""
from __future__ import annotations


def test_protocol_panel(page, evidence):
    page.fill("#asQuestion", "Effet de la résistance sur la constante de temps")
    page.click("#asDesign")
    page.wait_for_selector('#asAnswer [data-pd-status="designed"]')
    rows = page.locator("#asAnswer [data-pd-runs] tbody tr").count()
    text = page.inner_text("#asAnswer")
    assert rows == 9 and "control: determinism" in text and "Non simulé" in text
    evidence("Conception de protocole", "« Effet de la résistance sur la constante de temps » → Concevoir le protocole",
             "7 points de balayage + 2 témoins, répétitions justifiées, parties non simulées", f"{rows} essais")
