"""v4.6 — chemistry from entry to result, saved dossier, history and replay, clicked in Chromium."""
from __future__ import annotations


def _replay_from_history(page, bench, model_id):
    record = next(r["id"] for r in bench.history() if r["model_id"] == model_id)
    page.click(f'[data-history-replay="{record}"]')
    page.wait_for_function(f"(document.querySelector('[data-history-message=\"{record}\"]')||{{textContent:''}}).textContent.includes('Replayed')")
    return page.inner_text(f'[data-history-message="{record}"]')


def test_stoichiometry_full_path(page, bench, evidence):
    page.select_option("#reactionSelect", "water")
    page.click("#reactionAddReactants")
    page.click("#reactionRun")
    page.wait_for_selector("#reactionResult [data-dossier-id]")
    text = page.inner_text("#reactionResult")
    assert "Dossier enregistré #" in text and "PASS" in text
    assert [r["model_id"] for r in bench.history()] == ["chemical_stoichiometry"]
    replay = _replay_from_history(page, bench, "chemical_stoichiometry")
    assert "résultats identiques" in replay
    evidence("Chimie : stœchiométrie de bout en bout", "Choisir 2 H₂ + O₂ → 2 H₂O, ajouter les réactifs, calculer, rejouer depuis l'historique",
             "Équation vérifiée, dossier enregistré, rejeu identique", replay)


def test_kinetics_full_path_with_error_estimate(page, bench, evidence):
    page.click("#kinRun")
    page.wait_for_selector("#kinResult [data-dossier-id]")
    estimate = page.inner_text("#kinResult [data-error-estimate]")
    assert "Erreur d’intégration estimée" in estimate
    assert [r["model_id"] for r in bench.history()] == ["chemical_kinetics_network"]
    replay = _replay_from_history(page, bench, "chemical_kinetics_network")
    assert "résultats identiques" in replay
    evidence("Chimie : cinétique de bout en bout", "Lancer la simulation par défaut puis rejouer depuis l'historique",
             "Dossier enregistré, erreur estimée affichée, rejeu identique", f"{estimate} | {replay}")


def test_coarse_time_step_is_flagged_in_the_interface(page, bench, evidence):
    page.fill("#kinK", "15"); page.fill("#kinDuration", "1"); page.fill("#kinDt", "0.1")
    page.uncheck("#kinEnableSecond") if page.is_checked("#kinEnableSecond") else None
    page.click("#kinRun")
    page.wait_for_selector('#kinResult [data-warning="coarse_time_step"]')
    warning = page.inner_text('#kinResult [data-warning="coarse_time_step"]')
    assert "Réduisez dt" in warning
    evidence("Pas de temps trop grand signalé", "k = 15 s⁻¹, dt = 0,1 s (cas de l'audit v4.1)", "Avertissement visible avec l'erreur estimée", warning)
