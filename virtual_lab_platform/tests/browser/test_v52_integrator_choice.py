"""v5.2 — choosing the integration method in the kinetics panel."""
from __future__ import annotations


def test_implicit_method_from_the_interface(page, bench, evidence):
    page.select_option("#kinMethod", "implicit_euler")
    page.click("#kinRun")
    page.wait_for_selector("#kinResult [data-method]")
    text = page.inner_text("#kinResult [data-method]")
    assert "implicit_euler" in text and "pas acceptés" in text
    saved = page.request.get(page.base_url + f"/api/history/{bench.history()[0]['id']}").json()
    assert saved["method"] == "implicit_euler" and saved["configuration"]["method"] == "implicit_euler"
    evidence("Choix de l'intégrateur", "Choisir « Euler implicite extrapolé » puis lancer la simulation", "Méthode, diagnostics affichés et enregistrés", text)
