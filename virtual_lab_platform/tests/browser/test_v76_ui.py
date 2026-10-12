"""v7.6 — uncertainty propagation and hypothesis effects from the multi-model panel."""
from __future__ import annotations


def test_uncertainty_and_hypotheses_buttons(page, evidence):
    page.wait_for_function("document.querySelector('#plSpec').value.includes('arrhenius')")
    page.click("#plUncertainty")
    page.wait_for_selector("#plResult [data-pl-mc]", timeout=60000)
    mc = page.inner_text("#plResult [data-pl-mc]")
    assert "heating.temperature_k" in mc and "310.15" in mc
    page.click("#plHypotheses")
    page.wait_for_selector("#plResult [data-pl-hyp]", timeout=60000)
    hyp = page.inner_text("#plResult [data-pl-hyp]")
    assert "no self-heating" in hyp and "-3.9 %" in hyp  # 298.15 K instead of 310.15 K
    evidence("Incertitudes et hypothèses dans une chaîne", "Boutons « Propager les incertitudes » puis « Effet des hypothèses »",
             "Moyenne, écart-type et intervalle par sortie ; variation par hypothèse", f"{mc.splitlines()[1][:100]} | {hyp.splitlines()[2][:100]}")
