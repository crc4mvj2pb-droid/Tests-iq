"""v5.7 — maturity badges in the model catalogue."""
from __future__ import annotations


def test_catalogue_shows_maturity_levels(page, bench, evidence):
    page.wait_for_selector("#catalog [data-maturity]")
    verified = page.locator('#catalog [data-maturity="verified"]').count()
    concept = page.locator('#catalog [data-maturity="concept"]').count()
    assert verified == 9 and concept == 33  # v7.3: enzyme_kinetics moved from verified to validated_on_data
    assert "Modèle vérifié" in page.inner_text('#catalog [data-maturity="verified"] >> nth=0')
    assert page.locator('#catalog [data-maturity="validated_on_data"]').count() == 1
    evidence("Niveaux de maturité visibles", "Ouvrir le catalogue des modèles", "Badge de maturité sur chaque modèle", f"{verified} vérifiés, {concept} maquettes, 0 validé sur données")
