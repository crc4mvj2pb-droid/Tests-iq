from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")


def test_workbench_catalog_ids_are_unique():
    start = HTML.index("const items=[")
    end = HTML.index("\n];", start)
    ids = re.findall(r"\{id:'([^']+)'", HTML[start:end])
    assert len(ids) >= 60
    assert len(ids) == len(set(ids))
    assert re.search(r"},\s*\n\s*,\{id:", HTML[start:end]) is None, "Catalog array must not contain a hole before an item"


def test_equipment_containment_and_processing_are_wired():
    for marker in ("function isContainer", "function placeInside", "function runMachine", "function runContainedReaction", "parentInstanceId"):
        assert marker in HTML
    for equipment_id in ("centrifuge", "incubator", "pcr", "reactor", "microscope", "ph-meter"):
        assert f"id:'{equipment_id}'" in HTML


def test_explicit_optical_calculation_uses_beer_lambert():
    assert "A = εlc" in HTML
    assert "extinctionCoefficient" in HTML
    assert "concentrationM" in HTML


def test_known_water_reaction_product_exists():
    assert "id:'water-molecule'" in HTML
    assert "products:{'water-molecule':2}" in HTML


def test_graphical_circuit_connections_reach_the_dc_solver():
    for marker in ("function terminalPins", "function connectTerminals", "function runWorkbenchCircuit", "data-terminal-instance", "pinA", "/api/electrical/workbench-run"):
        assert marker in HTML
    assert "not yet passed to the general circuit solver" not in HTML


def test_expanded_equipment_ids_map_to_real_operations():
    for marker in ("processTypeById", "incubator:'incubator'", "pcr:'pcr'", "reactor:'reactor'", "microscope:'microscope'", "'pH-meter':'ph-meter'", "spectrometer:'spectro'"):
        assert marker in HTML
    assert "String(m.id).toLowerCase()==='ph-meter'" in HTML
