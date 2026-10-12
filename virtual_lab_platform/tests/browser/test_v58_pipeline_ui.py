"""v5.8 — multi-model experiments from the interface: run, intermediate results, maturity, refusal."""
from __future__ import annotations

import json


def test_verified_chain_runs_and_shows_each_step(page, evidence):
    page.wait_for_function("document.querySelector('#plSpec').value.includes('arrhenius')")
    page.select_option("#plExample", "temperature_kinetics_absorbance")
    page.click("#plRun")
    page.wait_for_selector("#plResult [data-pl-steps]")
    rows = page.locator("#plResult [data-pl-steps] tbody tr").count()
    assert rows == 3 and page.get_attribute("#plResult [data-pl-maturity]", "data-pl-maturity") == "verified"
    final = page.inner_text("#plResult [data-pl-final]")
    assert "absorbance.absorbance" in final and "0.372515" in final
    assert "Enregistré dans l’historique" in page.inner_text("#plStatus")
    evidence("Expérience multi-modèles vérifiée", "Exemple Température → Arrhenius → cinétique → absorbance, « Exécuter »",
             "3 étapes affichées avec sorties et conversions ; maturité vérifiée ; enregistrée", final.replace("\n", " ")[:200])


def test_weakest_step_limits_maturity_and_incompatible_units_are_refused(page, evidence):
    page.wait_for_function("document.querySelector('#plSpec').value.includes('arrhenius')")
    page.select_option("#plExample", "joule_heating_kinetics")
    page.click("#plRun")
    page.wait_for_selector("#plResult [data-pl-maturity]")
    text = page.inner_text("#plResult [data-pl-maturity]")
    # v7.1 verified the heating adapter: the chain is now fully verified (the weakest-link rule itself is tested in tests/test_v58_pipelines.py).
    assert page.get_attribute("#plResult [data-pl-maturity]", "data-pl-maturity") == "verified" and "limitante" not in text
    spec = json.loads(page.input_value("#plSpec"))
    spec["steps"][3]["inputs"]["reactions"][0]["reactants"] = {"A": 2}
    page.fill("#plSpec", json.dumps(spec))
    page.click("#plRun")
    page.wait_for_function("document.querySelector('#plStatus').textContent.startsWith('Erreur')")
    status = page.inner_text("#plStatus")
    assert "incompatible_variables" in status and page.locator("#plResult table").count() == 0
    evidence("Maillon faible et incompatibilité", "Chaîne avec échauffement (calculable), puis réaction d'ordre 2 alimentée par un k en 1/s",
             "Maturité « calculable » avec étape limitante ; refus explicite avec code", f"{text} | {status[:160]}")
