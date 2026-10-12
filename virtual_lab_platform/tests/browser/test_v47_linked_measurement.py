"""v4.7 — measuring a saved circuit result with a virtual multimeter, clicked in Chromium."""
from __future__ import annotations


def test_measure_saved_node_voltage_with_multimeter(page, bench, evidence):
    bench.reference_circuit(); bench.solve()
    record = bench.history()[0]["id"]
    page.click("#lmReload")
    page.wait_for_selector(f'#lmSource option[value="{record}"]', state="attached")
    page.select_option("#lmSource", str(record))
    page.wait_for_function("!document.querySelector('#lmQuantity').disabled")
    page.select_option("#lmQuantity", "node_voltage:SOURCE_PLUS")
    assert page.input_value("#lmInstrument") == "dmm_dc_voltage"
    page.click("#lmRun")
    page.wait_for_selector("[data-linked-reading]")
    text = page.inner_text("[data-linked-reading]")
    assert "Mesure simulée — non expérimentale" in text and "Valeur du modèle : 9.000000 V" in text
    readings = [r for r in bench.history() if r["model_id"] == "instrument_reading"]
    assert len(readings) == 1
    page.click(f'[data-history-replay="{readings[0]["id"]}"]')
    page.wait_for_function(f"(document.querySelector('[data-history-message=\"{readings[0]['id']}\"]')||{{textContent:''}}).textContent.includes('Replayed')")
    replay = page.inner_text(f'[data-history-message="{readings[0]["id"]}"]')
    assert "résultats identiques" in replay
    evidence("Instrument relié à un résultat", "Résoudre le circuit, choisir le dossier, la tension SOURCE+ et le multimètre, mesurer, rejouer",
             "Lecture simulée à partir de 9 V, provenance affichée, dossier enregistré et rejeu identique", text.replace("\n", " ")[:300])
