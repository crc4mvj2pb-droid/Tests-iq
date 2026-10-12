"""v6.0 — data catalogue from the interface: search, data-kind filter, export."""
from __future__ import annotations

from pathlib import Path


def test_search_filter_and_export(page, evidence):
    page.wait_for_selector("#dcResult [data-dc-table]")
    page.fill("#dcQuery", "oxygen demand"); page.click("#dcSearch")
    page.wait_for_function("document.querySelectorAll('#dcResult [data-dc-id]').length === 1")
    row = page.inner_text('#dcResult [data-dc-id="bod_marske_1967"]')
    assert "expérimentale (publiée)" in row and "marske_1967" in row and "demand (mg/L)" in row
    with page.expect_download() as info:
        page.click('#dcResult [data-dc-id="bod_marske_1967"] a')
    lines = Path(info.value.path()).read_text(encoding="utf-8").splitlines()
    assert lines[1] == "time (d),demand (mg/L)" and len(lines) == 8
    page.fill("#dcQuery", ""); page.select_option("#dcKind", "simulated"); page.click("#dcSearch")
    page.wait_for_function("document.querySelector('#dcStatus').textContent.startsWith('0 entrée')")
    page.select_option("#dcKind", "reference"); page.click("#dcSearch")
    page.wait_for_function("document.querySelectorAll('#dcResult [data-dc-kind=reference]').length >= 9")
    kinds = page.eval_on_selector_all("#dcResult [data-dc-kind]", "els => [...new Set(els.map(e => e.dataset.dcKind))]")
    assert kinds == ["reference"]
    evidence("Catalogue de données", "Rechercher « oxygen demand », exporter le CSV, filtrer par nature", "Entrée sourcée, nature affichée, CSV avec unités, filtre strict",
             f"{row.splitlines()[0]} ; CSV {len(lines)} lignes ; filtre référence : {kinds}")
