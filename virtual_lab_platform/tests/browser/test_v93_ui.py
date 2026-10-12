"""v9.3 — projects panel: create, add an experiment, export link."""
from __future__ import annotations

import io
import zipfile


def test_project_panel(page, bench, evidence):
    bench.reference_circuit(); bench.solve()
    page.fill("#prName", "Projet navigateur")
    page.click("#prCreate")
    page.wait_for_selector("#prList [data-pr-add]")
    pid = page.get_attribute("#prList [data-pr-add]", "data-pr-add")
    page.fill(f"#prAdd{pid}", "1")
    page.click(f'[data-pr-add="{pid}"]')
    page.wait_for_selector(f'[data-pr-export="{pid}"]')
    with page.expect_download() as info:
        page.click(f'[data-pr-export="{pid}"]')
    names = zipfile.ZipFile(io.BytesIO(open(info.value.path(), "rb").read())).namelist()
    assert "project.json" in names and any(n.startswith("packages/") for n in names)
    evidence("Projets et partage", "Créer un projet, ajouter l'expérience n° 1, exporter", "ZIP avec dossiers vérifiables et paquets reproductibles", f"{len(names)} fichiers")
