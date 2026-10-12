"""v8.5 — reaching a target and recording the decision from the assistant panel."""
from __future__ import annotations


def test_reach_target_and_record_decision(page, evidence):
    page.fill("#asQuestion", "Effet de la résistance sur la constante de temps")
    page.fill("#asTarget", "0.0047")
    page.click("#asReach")
    page.wait_for_selector('#asAnswer [data-ip-status="found"]')
    text = page.inner_text("#asAnswer")
    assert "resistance_ohm = 4700.00" in text
    page.click("#asKeep")
    page.wait_for_function("document.querySelector('#asKept').textContent.includes('enregistrée')")
    evidence("Planification vers un objectif", "Cible τ = 4,7 ms, puis « Retenir ce plan »", "R = 4 700 Ω trouvé ; décision enregistrée", text.splitlines()[0][:120])
