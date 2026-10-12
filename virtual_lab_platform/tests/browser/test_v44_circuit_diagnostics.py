"""v4.4 — topology diagnostics and warnings shown in the interface."""
from __future__ import annotations


def test_floating_subnetwork_is_named_and_not_saved(page, bench, evidence):
    src, res, gnd = bench.reference_circuit()
    a, b = bench.add("resistor"), bench.add("resistor")
    bench.wire(a, "A", b, "A"); bench.wire(a, "B", b, "B")
    bench.solve()
    message = page.inner_text("#wbResult p")
    assert "reliée ni à la source ni à la masse" in message and len(bench.history()) == 0
    evidence("Sous-réseau flottant", "Ajouter deux résistances reliées entre elles seulement", "Composants nommés, aucun dossier", message)


def test_ignored_component_and_conventions_are_displayed(page, bench, evidence):
    bench.reference_circuit()
    bench.add("led")
    text = bench.solve()
    warning = page.inner_text('[data-warning="ignored_components"]')
    assert "0.0090000 A" in text and "non pris en compte" in warning
    assert page.locator("[data-conventions]").count() == 1
    evidence("Composant ignoré signalé", "Ajouter une DEL non câblée au circuit de référence puis résoudre", "Résultat inchangé + avertissement visible", warning)
