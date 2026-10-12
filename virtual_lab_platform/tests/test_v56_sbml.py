"""v5.6 — SBML compatibility analysis, unit checks, refusal of unsupported features, analytical validation."""
from __future__ import annotations

import json
import math

import pytest

import sbml_engine as se
import scientific_imports as si

MATH = 'xmlns="http://www.w3.org/1998/Math/MathML"'


@pytest.fixture(autouse=True)
def isolated_library(tmp_path, monkeypatch):
    assets = tmp_path / "scientific_library" / "imported_assets"
    (assets / "models").mkdir(parents=True); (assets / "datasets").mkdir(parents=True)
    (assets / "index.json").write_text(json.dumps({"schema_version": "1.0", "assets": []}), encoding="utf-8")
    for module in (si, se):
        monkeypatch.setattr(module, "BASE", tmp_path); monkeypatch.setattr(module, "ASSET_DIR", assets)
    monkeypatch.setattr(si, "INDEX", assets / "index.json")


def sbml(extra_model="", reactions=None, units=True, level3=True, comp_size='size="2"', species_a='initialConcentration="1.5"', kinetic=None, root_extra="", species_extra=""):
    unit_defs = """<listOfUnitDefinitions><unitDefinition id="per_second"><listOfUnits><unit kind="second" exponent="-1" scale="0" multiplier="1"/></listOfUnits></unitDefinition></listOfUnitDefinitions>""" if units else ""
    model_units = 'substanceUnits="mole" timeUnits="second" volumeUnits="litre" extentUnits="mole"' if units else ""
    k_units = 'units="per_second"' if units else ""
    law = kinetic or f'<apply><times/><ci>k</ci><ci>A</ci><ci>c</ci></apply>'
    reactions = reactions or f"""<reaction id="r1" reversible="false"><listOfReactants><speciesReference species="A" stoichiometry="1" constant="true"/></listOfReactants>
      <listOfProducts><speciesReference species="B" stoichiometry="1" constant="true"/></listOfProducts><kineticLaw><math {MATH}>{law}</math></kineticLaw></reaction>"""
    head = '<sbml xmlns="http://www.sbml.org/sbml/level3/version2/core" level="3" version="2"' if level3 else '<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4"'
    return f"""{head} {root_extra}><model id="m" {model_units}>{unit_defs}
    <listOfCompartments><compartment id="c" {comp_size} constant="true" spatialDimensions="3"/></listOfCompartments>
    <listOfSpecies><species id="A" compartment="c" {species_a} hasOnlySubstanceUnits="false" boundaryCondition="false" constant="false" {species_extra}/>
    <species id="B" compartment="c" initialConcentration="0" hasOnlySubstanceUnits="false" boundaryCondition="false" constant="false"/></listOfSpecies>
    <listOfParameters><parameter id="k" value="0.4" constant="true" {k_units}/></listOfParameters>
    {extra_model}<listOfReactions>{reactions}</listOfReactions></model></sbml>"""


def load(xml):
    return si.import_sbml("model.xml", xml)["id"]


@pytest.mark.parametrize("method", ["rk4", "dopri5", "implicit_euler"])
def test_first_order_model_matches_analytical_solution(method):
    asset = load(sbml())
    report = se.analyze_sbml(asset)
    assert report["simulatable"] and report["unit_checks"] == [{"reaction": "r1", "status": "consistent", "dimension": "T^-1·N"}]
    out = se.simulate_sbml(asset, 3.0, 0.01, method)
    for row in out["rows"]:
        assert row["A_concentration"] == pytest.approx(1.5 * math.exp(-0.4 * row["time"]), rel=1e-6, abs=1e-9)
    assert out["provenance"]["sha256"] == report["provenance"]["sha256"] and out["engine"]["version"] == "2.0"


def test_second_order_model_matches_analytical_solution():
    reactions = f"""<reaction id="r1" reversible="false"><listOfReactants><speciesReference species="A" stoichiometry="2" constant="true"/></listOfReactants>
      <listOfProducts><speciesReference species="B" stoichiometry="1" constant="true"/></listOfProducts><kineticLaw><math {MATH}><apply><times/><ci>k2</ci><ci>A</ci><ci>A</ci><ci>c</ci></apply></math>
      <listOfLocalParameters><localParameter id="k2" value="0.3"/></listOfLocalParameters></kineticLaw></reaction>"""
    out = se.simulate_sbml(load(sbml(reactions=reactions)), 4.0, 0.01, "dopri5")
    # d[A]/dt = −2·k2·[A]² ⇒ [A] = A0/(1 + 2·k2·A0·t)
    for row in out["rows"]:
        assert row["A_concentration"] == pytest.approx(1.5 / (1 + 2 * 0.3 * 1.5 * row["time"]), rel=1e-6)


RULES = {
    "assignment rules": f'<listOfRules><assignmentRule variable="B"><math {MATH}><apply><times/><cn>2</cn><ci>A</ci></apply></math></assignmentRule></listOfRules>',
    "rate rules": f'<listOfRules><rateRule variable="B"><math {MATH}><cn>1</cn></math></rateRule></listOfRules>',
    "algebraic rules": f'<listOfRules><algebraicRule><math {MATH}><ci>A</ci></math></algebraicRule></listOfRules>',
    "events": f'<listOfEvents><event id="e" useValuesFromTriggerTime="true"><trigger initialValue="true" persistent="true"><math {MATH}><true/></math></trigger></event></listOfEvents>',
    "function definitions": f'<listOfFunctionDefinitions><functionDefinition id="f"><math {MATH}><lambda><bvar><ci>x</ci></bvar><ci>x</ci></lambda></math></functionDefinition></listOfFunctionDefinitions>',
    "initial assignments": f'<listOfInitialAssignments><initialAssignment symbol="A"><math {MATH}><cn>3</cn></math></initialAssignment></listOfInitialAssignments>',
    "constraints": f'<listOfConstraints><constraint><math {MATH}><true/></math></constraint></listOfConstraints>',
}


@pytest.mark.parametrize("feature", list(RULES))
def test_unsupported_features_are_detected_and_simulation_refused(feature):
    asset = load(sbml(extra_model=RULES[feature]))
    report = se.analyze_sbml(asset)
    assert not report["simulatable"] and f"not supported: {feature}" in report["blocking_problems"]
    with pytest.raises(se.SBMLSimulationError, match=feature):
        se.simulate_sbml(asset, 1.0, 0.1)


@pytest.mark.parametrize("variant,expected", [
    ("piecewise", "piecewise MathML"), ("delay", "delay"), ("fast", "fast reaction"), ("conversion", "conversion factors"), ("fbc", "SBML package 'fbc'"),
])
def test_other_unsupported_constructs(variant, expected):
    if variant == "piecewise":
        xml = sbml(kinetic=f'<piecewise><piece><ci>k</ci><true/></piece><otherwise><cn>0</cn></otherwise></piecewise>')
    elif variant == "delay":
        xml = sbml(kinetic='<apply><csymbol encoding="text" definitionURL="http://www.sbml.org/sbml/symbols/delay">delay</csymbol><ci>A</ci><cn>1</cn></apply>')
    elif variant == "fast":
        xml = sbml().replace('<reaction id="r1" reversible="false">', '<reaction id="r1" reversible="false" fast="true">')
    elif variant == "conversion":
        xml = sbml(species_extra='conversionFactor="k"')
    else:
        xml = sbml(root_extra='xmlns:fbc="http://www.sbml.org/sbml/level3/version1/fbc/version2" fbc:required="false"', species_extra='fbc:charge="0"')
    report = se.analyze_sbml(load(xml))
    assert not report["simulatable"] and any(expected in p for p in report["blocking_problems"]), report["blocking_problems"]


def test_layout_package_is_ignored_with_a_warning():
    xml = sbml(root_extra='xmlns:layout="http://www.sbml.org/sbml/level3/version1/layout/version1" layout:required="false"',
               extra_model='<layout:listOfLayouts><layout:layout layout:id="l"/></layout:listOfLayouts>')
    report = se.analyze_sbml(load(xml))
    assert report["simulatable"] and any("layout" in w for w in report["warnings"])


def test_level3_missing_values_are_refused_and_level2_defaults_are_reported():
    assert "compartment c has no size (SBML Level 3 has no default)" in se.analyze_sbml(load(sbml(comp_size="")))["blocking_problems"]
    assert any("species A has no initial" in p for p in se.analyze_sbml(load(sbml(species_a="")))["blocking_problems"])
    report = se.analyze_sbml(load(sbml(comp_size="", level3=False, units=False)))
    assert report["simulatable"] and any("Level 2 default 1" in w for w in report["warnings"])


def test_unit_inconsistency_is_reported_and_undeclared_units_left_unchecked():
    wrong = sbml(kinetic='<apply><times/><ci>k</ci><ci>A</ci></apply>')  # missing the volume factor: mol/(L·s) instead of mol/s
    report = se.analyze_sbml(load(wrong))
    assert report["simulatable"] and report["unit_checks"][0]["status"] == "inconsistent"
    assert any("expected" in w for w in report["warnings"])
    report = se.analyze_sbml(load(sbml(units=False)))
    assert report["unit_checks"][0]["status"] == "unchecked" and any("units not declared" in w for w in report["warnings"])


def test_local_parameters_are_not_global_overrides():
    reactions = f"""<reaction id="r1" reversible="false"><listOfReactants><speciesReference species="A" stoichiometry="1" constant="true"/></listOfReactants>
      <listOfProducts><speciesReference species="B" stoichiometry="1" constant="true"/></listOfProducts><kineticLaw><math {MATH}><apply><times/><ci>kl</ci><ci>A</ci><ci>c</ci></apply></math>
      <listOfLocalParameters><localParameter id="kl" value="0.3"/></listOfLocalParameters></kineticLaw></reaction>"""
    asset = load(sbml(reactions=reactions))
    assert "kl" not in se.analyze_sbml(asset)["parameters"]
    with pytest.raises(se.SBMLSimulationError, match="non-global"):
        se.simulate_sbml(asset, 1.0, 0.1, parameter_overrides={"kl": 1.0})


def test_source_file_is_preserved_and_tampering_detected():
    asset = load(sbml())
    record = json.loads((se.ASSET_DIR / "index.json").read_text())["assets"][0]
    stored = se.BASE / record["stored_path"]
    assert stored.read_text(encoding="utf-8") == sbml()
    stored.write_text(sbml().replace('value="0.4"', 'value="9"'), encoding="utf-8")
    with pytest.raises(se.SBMLSimulationError, match="hash mismatch"):
        se.analyze_sbml(asset)


def test_imports_refuse_entities_and_non_sbml():
    with pytest.raises(ValueError, match="DOCTYPE"):
        si.import_sbml("x.xml", '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><sbml/>')
    with pytest.raises(ValueError, match="not SBML"):
        si.import_sbml("x.xml", "<html/>")
