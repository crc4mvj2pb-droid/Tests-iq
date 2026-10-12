"""v5.1 — units, dimensions, constants and dimensional consistency of the engines' equations."""
from __future__ import annotations

import math

import pytest

import chemical_kinetics
import constants
import model_registry
import units
from contracts import ContractError
from units import UnitError, convert, dimension, parse


@pytest.mark.parametrize("value,src,dst,expected", [
    (1, "kΩ", "Ω", 1000), (1, "MΩ", "Ω", 1e6), (1, "mA", "A", 1e-3), (2.5, "nA", "pA", 2500), (25, "°C", "K", 298.15), (300, "K", "°C", 26.85),
    (1, "M", "mol/L", 1), (1, "mol/L", "mol/m^3", 1000), (1, "mM", "mol/L", 1e-3), (1, "L·mol⁻¹·cm⁻¹", "m^2/mol", 0.1),
    (1, "kW·h", "J", 3.6e6), (1, "eV", "J", 1.602176634e-19), (1, "atm", "bar", 1.01325), (90, "min", "h", 1.5), (1, "d", "s", 86400),
    (1, "J/(mol·K)", "J·mol^-1·K^-1", 1), (1, "m2/s", "cm^2/s", 1e4), (1, "s-1", "1/s", 1), (1, "µF", "F", 1e-6), (1, "uF", "nF", 1000),
    (1, "Hz", "1/s", 1), (1, "V/A", "Ω", 1), (1, "W", "V·A", 1), (1, "C", "A·s", 1), (1, "F", "C/V", 1), (1, "H", "V·s/A", 1),
])
def test_conversions(value, src, dst, expected):
    assert convert(value, src, dst) == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("src,dst", [("V", "A"), ("mol/L", "mol"), ("s", "Hz"), ("Ω", "S"), ("K", "J"), ("m^2/s", "m/s")])
def test_incompatible_dimensions_are_refused(src, dst):
    with pytest.raises(UnitError) as exc:
        convert(1, src, dst)
    assert exc.value.code == "incompatible_dimensions"


def test_arbitrary_units_are_never_converted_to_physical_units():
    assert convert(3, "a.u.", "a.u.") == 3
    for other in ("1", "mol/L", "s"):
        with pytest.raises(UnitError):
            convert(1, "a.u.", other)


def test_affine_units_cannot_be_combined_and_unknown_units_are_reported():
    with pytest.raises(UnitError) as exc:
        parse("°C/s")
    assert exc.value.code == "affine_in_expression"
    for bad in ("furlong", "kg/", "(m", "", "m^x"):
        with pytest.raises(UnitError):
            parse(bad)


def test_every_unit_declared_by_a_contract_is_understood():
    for contract in model_registry.list_contracts():
        for item in contract["parameters"] + contract["outputs"]:
            if item.get("unit"):
                parse(item["unit"])


def test_constants_are_versioned_sourced_and_internally_consistent():
    for c in constants.all_constants():
        assert c["source"] and c["reference_date"] and isinstance(c["exact"], bool) and c["relative_standard_uncertainty"] >= 0
        parse(c["unit"])
        assert (c["relative_standard_uncertainty"] == 0) == c["exact"]
    assert constants.GAS_CONSTANT == pytest.approx(constants.AVOGADRO * constants.BOLTZMANN, rel=1e-15)
    assert constants.FARADAY == pytest.approx(constants.AVOGADRO * constants.ELEMENTARY_CHARGE, rel=1e-15)
    assert dimension("J/(mol·K)") == dimension(constants.get("gas_constant")["unit"])
    assert chemical_kinetics.R_GAS is constants.GAS_CONSTANT or chemical_kinetics.R_GAS == constants.GAS_CONSTANT
    assert not any(c["id"].endswith("_approx") for c in constants.all_constants())


# Dimensional consistency of the main equations used by the engines (each side must have the same dimension).
EQUATIONS = [
    ("τ = R·C (RC step)", "Ω·F", "s"), ("τ = L/R (RL step)", "H/Ω", "s"), ("I = V/R (Ohm, nodal analysis)", "V/Ω", "A"),
    ("P = V·I", "V·A", "W"), ("P = R·I²", "Ω·A^2", "W"), ("X_L = ω·L", "1/s·H", "Ω"), ("X_C = 1/(ω·C)", "1/(1/s·F)", "Ω"),
    ("Kirchhoff: G·v = i", "S·V", "A"), ("first order: k·[A]", "1/s·mol/L", "mol/(L·s)"), ("second order: k·[A]²", "L/(mol·s)·(mol/L)^2", "mol/(L·s)"),
    ("Arrhenius exponent Ea/(R·T)", "(J/mol)/(J/(mol·K)·K)", "1"), ("Beer–Lambert A = ε·l·c", "L·mol⁻¹·cm⁻¹·cm·mol/L", "1"),
    ("Fourier number α·dt/dx²", "m^2/s·s/m^2", "1"), ("LIF: R·I", "MΩ·nA", "mV"), ("ideal gas: n·R·T", "mol·J/(mol·K)·K", "Pa·m^3"),
    ("Faraday: N_A·e", "1/mol·C", "C/mol"), ("SIR: β·S·I/N", "1/d", "1/s"), ("Heat flux density: k·ΔT/Δx", "W/(m·K)·K/m", "W/m^2"),
]


@pytest.mark.parametrize("name,left,right", EQUATIONS, ids=[e[0] for e in EQUATIONS])
def test_equation_dimensions(name, left, right):
    assert units.compatible(left, right), (name, dimension(left), dimension(right))


def test_quantities_with_units_in_the_standard_run():
    env = model_registry.run_model("rc_rl_step_response", {"resistance_ohm": {"value": 1, "unit": "kΩ"}, "capacitance_f": {"value": 2, "unit": "µF"}})
    assert env["inputs"]["resistance_ohm"] == 1000 and env["outputs"]["time_constant"]["value"] == pytest.approx(2e-3)
    with pytest.raises(ContractError) as exc:
        model_registry.run_model("rc_rl_step_response", {"resistance_ohm": {"value": 5, "unit": "mA"}})
    assert exc.value.code == "incompatible_dimensions"
    with pytest.raises(ContractError) as exc:
        model_registry.run_model("rc_rl_step_response", {"resistance_ohm": {"value": 5, "unit": "zorks"}})
    assert exc.value.code == "unknown_unit"
    with pytest.raises(ContractError) as exc:  # arbitrary model units refuse physical quantities
        model_registry.run_model("logistic_growth", {"duration": {"value": 5, "unit": "s"}})
    assert exc.value.code == "incompatible_dimensions"
    env = model_registry.run_model("heat_diffusion_1d", {"left_temp_c": {"value": 373.15, "unit": "K"}})
    assert env["inputs"]["left_temp_c"] == pytest.approx(100.0)


def kin(**extra):
    return {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}, {"id": "C", "initial_concentration": 0.0}],
            "reactions": [{"id": "r1", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5},
                          {"id": "r2", "reactants": {"A": 1, "B": 1}, "products": {"C": 1}, "rate_constant": 0.1}], "duration": 1, "dt": 0.01, **extra}


def test_kinetics_declares_concentration_unit_and_derives_rate_constant_units():
    d = chemical_kinetics.simulate_reaction_network(kin(concentration_unit="mmol/L"))
    assert d["concentration_unit"] == "mmol/L"
    assert [(r["order"], r["unit"]) for r in d["rate_constant_units"]] == [(1, "1/s"), (2, "(mmol/L)^-1/s")]
    assert units.compatible("(mmol/L)^-1/s", "L/(mol·s)")
    assert chemical_kinetics.simulate_reaction_network(kin(concentration_unit="a.u."))["rate_constant_units"][1]["unit"] == "a.u."
    for bad in ("mol/s", "kg", "nonsense"):
        with pytest.raises(chemical_kinetics.ChemicalKineticsError):
            chemical_kinetics.simulate_reaction_network(kin(concentration_unit=bad))
