"""v5.6 — SBML compatibility analysis from the interface."""
from __future__ import annotations

from pathlib import Path

RULE_MODEL = """<sbml xmlns="http://www.sbml.org/sbml/level3/version2/core" level="3" version="2"><model id="with_rule">
<listOfCompartments><compartment id="c" size="1" constant="true"/></listOfCompartments>
<listOfSpecies><species id="A" compartment="c" initialConcentration="1" hasOnlySubstanceUnits="false" boundaryCondition="false" constant="false"/>
<species id="B" compartment="c" initialConcentration="0" hasOnlySubstanceUnits="false" boundaryCondition="false" constant="false"/></listOfSpecies>
<listOfParameters><parameter id="k" value="0.5" constant="true"/></listOfParameters>
<listOfRules><assignmentRule variable="B"><math xmlns="http://www.w3.org/1998/Math/MathML"><apply><times/><cn>2</cn><ci>A</ci></apply></math></assignmentRule></listOfRules>
<listOfReactions><reaction id="r" reversible="false"><listOfReactants><speciesReference species="A" stoichiometry="1" constant="true"/></listOfReactants>
<listOfProducts><speciesReference species="B" stoichiometry="1" constant="true"/></listOfProducts>
<kineticLaw><math xmlns="http://www.w3.org/1998/Math/MathML"><apply><times/><ci>k</ci><ci>A</ci></apply></math></kineticLaw></reaction></listOfReactions></model></sbml>"""


def test_model_with_rule_is_reported_and_refused(page, bench, evidence, tmp_path):
    path = tmp_path / "with_rule.xml"; path.write_text(RULE_MODEL, encoding="utf-8")
    page.set_input_files("#sbmlFile", str(path))
    page.click("#importSbmlBtn")
    page.wait_for_function("[...document.querySelectorAll('#sbmlRunModel option')].some(o => o.textContent.includes('with_rule') || o.textContent.includes('with_rule.xml'))")
    value = page.eval_on_selector_all("#sbmlRunModel option", "opts => opts.find(o => o.textContent.includes('with_rule')).value")
    page.select_option("#sbmlRunModel", value)
    page.click("#analyzeSbml")
    page.wait_for_selector("[data-sbml-report]")
    blocking = page.inner_text("[data-sbml-blocking]")
    assert "assignment rules" in blocking and "Non simulable" in page.inner_text("[data-sbml-report]")
    page.click("#runSbmlSimulation")
    page.wait_for_function("document.querySelector('#sbmlSimulationStatus').textContent.toLowerCase().includes('assignment rules')")
    evidence("SBML : fonctionnalité non prise en charge", "Importer un modèle avec une règle d'affectation, analyser, simuler", "Signalé non simulable ; simulation refusée",
             blocking.replace("\n", " "))
