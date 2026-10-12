"""v5.5 — parameter analyses from the interface: sweep, cancellation, export, Monte Carlo."""
from __future__ import annotations

from pathlib import Path


def _wait_done(page):
    page.wait_for_function("!document.querySelector('#anSweep').disabled")


def test_sweep_plot_table_and_csv_export(page, bench, evidence):
    page.select_option("#anModel", "rc_rl_step_response")
    page.select_option("#anParam", "resistance_ohm"); page.select_option("#anOutput", "time_constant")
    page.fill("#anStart", "100"); page.fill("#anStop", "1000"); page.fill("#anCount", "10")
    page.click("#anSweep"); _wait_done(page)
    rows = page.locator("#anResult [data-an-table] tbody tr").count()
    assert rows == 10 and page.locator("#anResult svg polyline").count() == 1
    with page.expect_download() as info:
        page.click("#anExport")
    csv = Path(info.value.path()).read_text(encoding="utf-8").splitlines()
    assert csv[0].startswith("resistance_ohm (Ω),") and len(csv) == 11
    evidence("Balayage paramétrique", "Modèle RC, R de 100 à 1000 Ω, 10 points ; export CSV", "Courbe, tableau de 10 lignes, CSV avec unités", f"{rows} lignes ; en-tête CSV : {csv[0]}")


def test_long_monte_carlo_can_be_cancelled(page, bench, evidence):
    page.select_option("#anModel", "series_rlc_frequency_sweep")
    page.select_option("#anParam", "resistance_ohm")
    page.fill("#anSamples", "5000")
    page.click("#anMonteCarlo")
    page.wait_for_function("document.querySelector('#anStatus').textContent.includes('running')")
    page.click("#anCancel")
    page.wait_for_function("document.querySelector('#anStatus').textContent.includes('annulée')")
    status = page.inner_text("#anStatus")
    assert "aucun résultat partiel" in status and page.locator("#anResult table").count() == 0
    evidence("Annulation d'une analyse longue", "Lancer 5 000 tirages Monte Carlo puis cliquer « Annuler »", "Arrêt, aucun résultat partiel publié", status)


def test_monte_carlo_and_sensitivity_results(page, bench, evidence):
    page.select_option("#anModel", "rc_rl_step_response")
    page.select_option("#anParam", "resistance_ohm"); page.select_option("#anOutput", "time_constant")
    page.fill("#anSamples", "200"); page.click("#anMonteCarlo"); _wait_done(page)
    mc = page.inner_text("#anResult")
    assert "200/200 échantillons valides" in mc
    page.click("#anSensitivity"); _wait_done(page)
    sens = page.inner_text("#anResult [data-an-table]")
    assert "1.00000" in sens  # τ = R·C: normalised coefficients equal to 1
    evidence("Monte Carlo et sensibilité", "Monte Carlo 200 tirages puis sensibilité locale sur τ", "Statistiques affichées ; coefficients = 1 pour τ = RC", sens.replace("\n", " ")[:200])
