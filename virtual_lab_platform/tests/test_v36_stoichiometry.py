import math
import pytest

from reaction_stoichiometry import (
    StoichiometryError,
    calculate_stoichiometry,
    parse_formula,
)


def test_neutralization_checks_atom_balance_and_calculates_extent():
    result = calculate_stoichiometry({
        "reaction_id": "neutralization",
        "reactants": {"HCl": 1, "NaOH": 1},
        "products": {"NaCl": 1, "H2O": 1},
        "species": [
            {"id": "HCl", "amount_mol": 0.2, "formula": "HCl"},
            {"id": "NaOH", "amount_mol": 0.15, "formula": "NaOH"},
            {"id": "NaCl", "amount_mol": 0, "formula": "NaCl"},
            {"id": "H2O", "amount_mol": 0, "formula": "H2O"},
        ],
    })
    assert result["validation_level"] == "L1"
    assert result["atom_balance"]["status"] == "balanced"
    assert result["limiting_reactants"] == ["NaOH"]
    assert math.isclose(result["reaction_extent_mol"], 0.15)
    assert math.isclose(result["reactant_amounts_remaining_mol"]["HCl"], 0.05)
    assert math.isclose(result["product_amounts_theoretical_mol"]["NaCl"], 0.15)
    assert result["checks"]["limiting_reactant_exhausted"]


def test_formula_parser_supports_parenthesized_groups():
    assert parse_formula("Ca(OH)2") == {"Ca": 1, "O": 2, "H": 2}
    assert parse_formula("Al2(SO4)3") == {"Al": 2, "S": 3, "O": 12}


def test_rejects_atom_unbalanced_equation_before_result_is_returned():
    with pytest.raises(StoichiometryError, match="not atom-balanced"):
        calculate_stoichiometry({
            "reactants": {"H2": 1},
            "products": {"H2O": 1},
            "species": [
                {"id": "H2", "amount_mol": 1, "formula": "H2"},
                {"id": "H2O", "amount_mol": 0, "formula": "H2O"},
            ],
        })


def test_missing_formula_is_reported_as_not_checked_not_as_balanced():
    result = calculate_stoichiometry({
        "reactants": {"A": 1},
        "products": {"B": 1},
        "species": [{"id": "A", "amount_mol": 1}, {"id": "B", "amount_mol": 0}],
    })
    assert result["validation_level"] == "L0"
    assert result["atom_balance"]["status"] == "not_checked_missing_formula"
    assert result["checks"]["equation_atom_balanced"] is None


def test_rejects_negative_amount_and_duplicate_species():
    with pytest.raises(StoichiometryError, match="non-negative"):
        calculate_stoichiometry({
            "reactants": {"A": 1}, "products": {"B": 1},
            "species": [{"id": "A", "amount_mol": -1}, {"id": "B", "amount_mol": 0}],
        })
    with pytest.raises(StoichiometryError, match="unique"):
        calculate_stoichiometry({
            "reactants": {"A": 1}, "products": {"B": 1},
            "species": [{"id": "A", "amount_mol": 1}, {"id": "A", "amount_mol": 2}, {"id": "B", "amount_mol": 0}],
        })


def test_workbench_reaction_ui_calls_server_engine_and_does_not_mutate_on_error():
    from pathlib import Path
    html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text(encoding="utf-8")
    assert "fetch('/api/chemistry/stoichiometry'" in html
    assert "No bench amounts were changed" in html
    assert "bilan atomique équilibré" in html


def test_api_exposes_v36_stoichiometry_route():
    from pathlib import Path
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert '"version": "4.1"' in app
    assert '"/api/chemistry/stoichiometry"' in app
