"""v4.8 — accessibility audit, keyboard-only use, double submission, network errors and console cleanliness."""
from __future__ import annotations

from pathlib import Path

AXE = Path(__file__).resolve().parent / "vendor" / "axe-core-4.10.2" / "axe.min.js"


def _axe(page):
    page.add_script_tag(path=str(AXE))
    return page.evaluate("async () => (await axe.run(document, {resultTypes: ['violations']})).violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length}))")


def test_no_serious_accessibility_violations_before_and_after_results(page, bench, evidence):
    before = _axe(page)
    bench.reference_circuit(); bench.solve()
    page.click("#kinRun"); page.wait_for_selector("#kinResult [data-dossier-id]")
    after = _axe(page)
    severe = [v for v in before + after if v["impact"] in ("critical", "serious")]
    assert severe == [], severe
    evidence("Accessibilité (axe-core 4.10.2)", "Audit de la page au chargement puis après affichage de résultats",
             "0 violation critique ou sérieuse", f"avant : {len(before)} type(s) de violation, après : {len(after)} ; critiques/sérieuses : {len(severe)}")


def _tab_to(page, selector, limit=1500):
    for _ in range(limit):
        if page.evaluate("s => document.activeElement && document.activeElement.matches(s)", selector):
            return
        page.keyboard.press("Tab")
    raise AssertionError(f"{selector} is not reachable with the Tab key")


def test_reference_circuit_with_keyboard_only(page, bench, evidence):
    def press(selector):
        _tab_to(page, selector); page.keyboard.press("Enter")
    press('#wbTabs [data-cat="electrical"]')
    for item in ("dc-source", "resistor", "ground"):
        press(f'#wbCatalog [data-add="{item}"]')
    src, res, gnd = bench.instances()
    press(f'[data-instance="{res}"]'); _tab_to(page, "#wbPropQty"); page.keyboard.press("Control+A"); page.keyboard.type("1000")
    press(f'[data-instance="{src}"]'); _tab_to(page, "#wbPropQty"); page.keyboard.press("Control+A"); page.keyboard.type("9")
    for a, pa, b, pb in ((src, "P", res, "A"), (res, "B", gnd, "GND"), (src, "N", gnd, "GND")):
        press(f'[data-terminal-instance="{a}"][data-terminal-pin="{pa}"]')
        press(f'[data-terminal-instance="{b}"][data-terminal-pin="{pb}"]')
    press("#wbSolveCircuit")
    page.wait_for_function("document.querySelector('#wbResult h3') && document.querySelector('#wbResult h3').textContent.includes('calculé')")
    assert "0.0090000 A" in page.inner_text("#wbResult")
    evidence("Utilisation au clavier seul", "Tab + Entrée pour ajouter, sélectionner, saisir, câbler et résoudre", "I = 9 mA sans souris", "I = 0.0090000 A")


def test_lab_run_double_click_saves_once(page, bench, evidence):
    page.locator("#labRun").scroll_into_view_if_needed()
    page.dblclick("#labRun")
    page.wait_for_function("!document.querySelector('#labRun').disabled")
    page.wait_for_timeout(500)
    saved = [r for r in bench.history() if r["model_id"] not in ("electrical_workbench_dc",)]
    assert len(saved) <= 1
    evidence("Double soumission (concepteur)", "Double-cliquer sur « Run »", "Au plus 1 dossier", f"{len(saved)} dossier(s)")


def test_network_failure_message_in_another_panel(page, bench, evidence):
    page.route("**/api/experiments", lambda route: route.abort())
    page.click("#run")
    page.wait_for_function("document.querySelector('#result').textContent.includes('injoignable')")
    message = page.inner_text("#result")
    page.unroute("**/api/experiments")
    page.route("**/api/experiments", lambda route: route.fulfill(status=502, body="<html>proxy</html>", content_type="text/html"))
    page.click("#run")
    page.wait_for_function("document.querySelector('#result').textContent.includes('Réponse inattendue')")
    message2 = page.inner_text("#result")
    evidence("Erreurs réseau hors paillasse", "Couper puis simuler une réponse HTML sur « Run experiment »", "Messages compréhensibles",
             f"{message.strip()} | {message2.strip()}")


def test_default_actions_produce_no_console_error(page, bench, evidence):
    page.click("#run"); page.wait_for_function("document.querySelector('#result').textContent.length > 40")
    page.click("#kinRun"); page.wait_for_selector("#kinResult [data-dossier-id]")
    page.select_option("#reactionSelect", "water"); page.click("#reactionAddReactants"); page.click("#reactionRun")
    page.wait_for_selector("#reactionResult [data-dossier-id]")
    page.click("#runValidationSuite"); page.wait_for_function("document.querySelector('#validationSuiteResult').textContent.includes('Passed')")
    page.click("#viRun"); page.wait_for_function("document.querySelector('#viOutput').textContent.includes('simulée')")
    page.click("#refreshHistory"); page.wait_for_timeout(300)
    assert page.console_errors == [], page.console_errors
    evidence("Console sans erreur", "Exécuter les actions par défaut de 6 panneaux", "0 erreur console / JavaScript", f"{len(page.console_errors)} erreur(s)")
