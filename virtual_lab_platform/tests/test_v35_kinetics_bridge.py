from pathlib import Path
import math

from chemical_kinetics import simulate_reaction_network

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def test_abstract_kinetic_species_are_explicitly_catalogued():
    for species_id in ("kinetic-a", "kinetic-b", "kinetic-c"):
        assert f"id:'{species_id}'" in HTML
    assert "ne représente aucune molécule réelle" in HTML


def test_workbench_concentrations_can_be_loaded_into_kinetics_panel():
    assert 'id="kinAddSpecies"' in HTML
    assert 'id="kinLoadBench"' in HTML
    assert "function loadKineticsFromBench()" in HTML
    assert "x.concentrationM" in HTML
    assert "kinEl('kinA0').value=a;kinEl('kinB0').value=b" in HTML


def test_kinetics_panel_calls_existing_server_engine_and_exports_results():
    # v4.6: the panel now calls the saving endpoint (behaviour covered in tests/browser/test_v46_chemistry_path.py).
    assert "fetch('/api/chemistry/kinetics-run'" in HTML
    assert "kinEl('kinExportInline').onclick" in HTML
    assert "simulate_reaction_network(request)" in APP


def test_kinetics_model_output_is_numerical_and_conserves_abstract_amount():
    result = simulate_reaction_network({
        "species": [
            {"id": "A", "initial_concentration": 1.0, "atoms": {"X": 1}},
            {"id": "B", "initial_concentration": 0.0, "atoms": {"X": 1}},
        ],
        "reactions": [
            {"id": "A_to_B", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.4}
        ],
        "duration": 2.0,
        "dt": 0.01,
        "temperature_k": 298.15,
    })
    final = result["summary"]["final_concentrations"]
    assert result["validation_level"] == "L1"
    assert math.isclose(final["A"], math.exp(-0.8), abs_tol=2e-8)
    assert math.isclose(final["A"] + final["B"], 1.0, abs_tol=2e-8)
