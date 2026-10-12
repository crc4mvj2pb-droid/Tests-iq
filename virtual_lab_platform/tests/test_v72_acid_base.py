"""v7.2 — aqueous acid–base equilibria with sourced pKa values, verified against independent solutions."""
from __future__ import annotations

import math

import pytest

import acid_base
import data_catalog
import model_registry


def pka(acid):
    entry = data_catalog.get_entry("pka_aqueous_25c")
    rows = sorted((r for r in entry["rows"] if r[0] == acid), key=lambda r: r[1])
    return [r[2] for r in rows]


def run(model, inputs):
    return model_registry.run_model(model, inputs)["result"]


def _newton_weak_acid(c, ka, kw=1e-14):
    """Independent: h³ + Ka·h² − (Kw + Ka·C)·h − Ka·Kw = 0 solved by Newton from h = √(Ka·C)."""
    h = math.sqrt(ka * c)
    for _ in range(100):
        f = h ** 3 + ka * h ** 2 - (kw + ka * c) * h - ka * kw
        df = 3 * h ** 2 + 2 * ka * h - (kw + ka * c)
        h -= f / df
    return -math.log10(h)


@pytest.mark.parametrize("c", [1e-1, 1e-3, 1e-6])
def test_weak_acid_against_independent_cubic_solution(c):
    p = pka("acetic acid")
    d = run("aqueous_acid_base", {"weak_systems": [{"name": "acetic", "pka": p, "total_concentration_mol_l": c}]})
    assert d["ph"] == pytest.approx(_newton_weak_acid(c, 10 ** -p[0]), abs=1e-9)


def test_strong_acid_and_base_closed_forms():
    for c in (1e-2, 1e-7):
        h = (c + math.sqrt(c * c + 4e-14)) / 2  # h = C + Kw/h
        assert run("aqueous_acid_base", {"strong_acid_mol_l": c})["ph"] == pytest.approx(-math.log10(h), abs=1e-9)
    assert run("aqueous_acid_base", {})["ph"] == pytest.approx(7.0, abs=1e-9)


def test_charge_and_mass_balances_hold():
    d = run("aqueous_acid_base", {"weak_systems": [{"name": "phosphate", "pka": pka("phosphoric acid"), "total_concentration_mol_l": 0.05},
                                                       {"name": "ammonium", "pka": pka("ammonium"), "total_concentration_mol_l": 0.02, "charge_of_fully_protonated": 1}],
                                      "strong_base_mol_l": 0.07, "strong_acid_mol_l": 0.02})
    assert abs(d["checks"]["charge_balance_residual_mol_l"]) < 1e-12 and d["checks"]["fractions_sum_to_one"]
    total_p = sum(s["concentration_mol_l"] for s in d["species"] if s["system"] == "phosphate")
    assert total_p == pytest.approx(0.05, rel=1e-12)


def test_known_textbook_situations():
    assert run("aqueous_acid_base", {"weak_systems": [{"pka": pka("acetic acid"), "total_concentration_mol_l": 0.1}]})["ph"] == pytest.approx(2.88, abs=0.005)
    ammonium = run("aqueous_acid_base", {"weak_systems": [{"pka": pka("ammonium"), "total_concentration_mol_l": 0.1, "charge_of_fully_protonated": 1}],
                                             "strong_acid_mol_l": 0.1})
    assert ammonium["ph"] == pytest.approx(5.125, abs=0.01)
    p = pka("phosphoric acid")
    amphiprotic = run("aqueous_acid_base", {"weak_systems": [{"pka": p, "total_concentration_mol_l": 0.1}], "strong_base_mol_l": 0.1})
    assert amphiprotic["ph"] == pytest.approx((p[0] + p[1]) / 2, abs=0.03)  # H2PO4⁻: pH ≈ (pKa1 + pKa2)/2


def test_buffer_reports_henderson_hasselbalch_only_as_comparison():
    d = run("aqueous_acid_base", {"weak_systems": [{"pka": [4.756], "total_concentration_mol_l": 0.2}], "strong_base_mol_l": 0.05})
    assert d["henderson_hasselbalch_ph"] == pytest.approx(4.756 + math.log10(0.05 / 0.15)) and abs(d["ph"] - d["henderson_hasselbalch_ph"]) < 0.01
    assert "Approximation" in d["henderson_hasselbalch_note"]


def test_titration_landmarks():
    d = run("aqueous_titration", {"analyte": {"pka": [4.756], "total_concentration_mol_l": 0.1}, "analyte_volume_ml": 25.0,
                                    "titrant_concentration_mol_l": 0.1, "max_titrant_ml": 50.0, "points": 101})
    assert d["equivalence_volumes_ml"] == [pytest.approx(25.0, abs=1e-12)]
    half = next(r for r in d["rows"] if r["titrant_ml"] == 12.5)
    assert half["ph"] == pytest.approx(4.756, abs=0.01)
    phs = [r["ph"] for r in d["rows"]]
    assert all(a < b for a, b in zip(phs, phs[1:]))  # monotonic curve
    eq = next(r for r in d["rows"] if r["titrant_ml"] == 25.0)
    # at equivalence: 0.05 mol/L acetate, pOH from Kb = Kw/Ka
    kb = 1e-14 / 10 ** -4.756
    assert eq["ph"] == pytest.approx(14 + math.log10(math.sqrt(kb * 0.05)), abs=0.01)


@pytest.mark.parametrize("systems,code", [([{"pka": [7, 3], "total_concentration_mol_l": 0.1}], "invalid_systems"),
                                          ([{"pka": [4.7]}], "invalid_systems"), ([{"pka": [4.7], "total_concentration_mol_l": -1}], "invalid_systems")])
def test_invalid_inputs(systems, code):
    with pytest.raises(acid_base.AcidBaseError) as exc:
        run("aqueous_acid_base", {"weak_systems": systems})
    assert exc.value.code == code


def test_pka_dataset_is_sourced_and_flagged_approximate():
    entry = data_catalog.get_entry("pka_aqueous_25c")
    assert entry["data_kind"] == "reference" and entry["source_ids"] == ["haynes_crc_2016"] and entry["approximate"] is True
    assert data_catalog.lock_problems() == []
