"""v6.3 — fit a model to catalogue data from the interface: published estimates, residual plot, separate validation."""
from __future__ import annotations


def _setup(page):
    page.wait_for_function("document.querySelectorAll('#ftDataset option').length >= 2")
    page.select_option("#ftDataset", "puromycin_treloar_1974")
    page.select_option("#ftX", "conc"); page.select_option("#ftY", "rate")
    page.fill("#ftWhere", "state=treated"); page.select_option("#ftModel", "michaelis_menten")


def test_puromycin_fit_from_the_interface(page, evidence):
    _setup(page)
    page.click("#ftRun")
    page.wait_for_selector("#ftResult [data-ft-params]")
    vm = page.inner_text('#ftResult [data-param="Vm"]')
    k = page.inner_text('#ftResult [data-param="K"]')
    assert "212.68" in vm and "6.9472" in vm and "counts/min/min" in vm and "0.064121" in k
    assert page.locator("#ftResult svg[data-ft-residuals] circle").count() == 12
    assert "Enregistré" in page.inner_text("#ftStatus")
    evidence("Ajustement Michaelis–Menten sur données publiées", "Puromycine, cellules traitées, modèle Michaelis–Menten",
             "Vm = 212,7 ± 6,95 et K = 0,0641 ± 0,0083 (Bates & Watts 1988)", f"{vm} | {k}".replace("\n", " ").replace("\t", " "))


def test_validation_on_points_not_used(page, evidence):
    _setup(page)
    page.select_option("#ftValidation", "alternate")
    page.click("#ftRun")
    page.wait_for_selector("#ftResult [data-ft-validation]")
    text = page.inner_text("#ftResult [data-ft-validation]")
    assert "6 point(s) non utilisés" in text and page.locator("#ftResult svg[data-ft-residuals] circle").count() == 6
    evidence("Validation séparée", "Même ajustement, un point sur deux tenu à l'écart", "Ajustement sur 6 points, RMSE de validation sur les 6 autres", text)
