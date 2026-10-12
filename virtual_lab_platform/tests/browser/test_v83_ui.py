"""v8.3 — executing a research plan from the assistant panel (task graph with node states)."""
from __future__ import annotations


def test_plan_execution(page, evidence):
    page.fill("#asQuestion", "Effet de la résistance sur la constante de temps")
    page.click("#asExecute")
    page.wait_for_selector('#asAnswer [data-tg-status="completed"]', timeout=60000)
    rows = page.locator("#asAnswer [data-tg-nodes] tbody tr").count()
    text = page.inner_text("#asAnswer")
    assert rows == 6 and "increasing" in text
    evidence("Exécution planifiée", "Bouton « Exécuter le plan »", "6 tâches tracées avec dépendances, état et durée", text.splitlines()[0])
