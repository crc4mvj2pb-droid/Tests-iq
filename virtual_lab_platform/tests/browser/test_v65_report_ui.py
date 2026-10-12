"""v6.5 — report and reproducible package reachable from the saved history."""
from __future__ import annotations

import io
import zipfile


def test_history_offers_report_and_package(page, bench, evidence):
    bench.reference_circuit()
    bench.solve()
    page.click("#refreshHistory")
    link = page.locator("[data-history-report]").first
    link.wait_for()
    href = link.get_attribute("href")
    # The link is opened by navigation (the page's fetch wrapper deliberately treats HTML API answers as proxy errors).
    response = page.request.get(page.base_url + href)
    text = response.text()
    assert response.status == 200 and "Conclusions" in text and "À rédiger par le chercheur" in text
    with page.expect_download() as info:
        page.locator("[data-history-package]").first.click()
    data = open(info.value.path(), "rb").read()
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert "reproduce.py" in names and "MANIFEST.json" in names
    evidence("Rapport et paquet depuis l'historique", "Résoudre un circuit, ouvrir « Rapport », télécharger « Paquet reproductible »",
             "Rapport avec sections séparées ; ZIP avec reproduce.py et manifeste", f"{href} ; {len(names)} fichiers dans le paquet")
