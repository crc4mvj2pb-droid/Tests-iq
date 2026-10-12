"""v6.2 — import a data file from the interface: quality report first, then an 'imported' catalogue entry."""
from __future__ import annotations


def test_preview_report_then_import(page, tmp_path, evidence):
    data = tmp_path / "bench.csv"
    data.write_text("time (s),signal [mV]\n0,1.0\n1,1.1\n2,1.2\n2,1.2\n3,\n4,1.3\n5,9.9\n6,1.4\n", encoding="utf-8")
    page.click("#dcImport summary")
    page.set_input_files("#diFile", str(data))
    page.click("#diPreview")
    page.wait_for_selector("#diReport [data-di-issues]")
    issues = page.eval_on_selector_all("#diReport [data-issue]", "els => els.map(e => e.dataset.issue)")
    assert set(issues) == {"duplicate_rows", "missing_values", "outliers"}
    assert "mV" in page.inner_text("#diReport [data-di-columns]")
    page.fill("#diId", "bench_run"); page.fill("#diTitle", "Banc"); page.fill("#diLicense", "données personnelles"); page.fill("#diApplicability", "essai")
    page.click("#diImport")
    page.wait_for_function("document.querySelector('#diStatus').textContent.startsWith('Importé')")
    page.wait_for_selector('#dcResult [data-dc-id="bench_run"]')
    row = page.inner_text('#dcResult [data-dc-id="bench_run"]')
    assert "importée" in row and "signal (mV)" in row
    evidence("Import de données avec contrôle qualité", "Choisir un CSV, « Aperçu », puis « Importer »",
             "Doublon, valeur manquante et aberrante signalés ; entrée « importée » dans le catalogue", f"{issues} ; {row.splitlines()[0]}")
