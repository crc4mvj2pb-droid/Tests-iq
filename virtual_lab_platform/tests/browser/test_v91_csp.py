"""v9.1 — the interface works under its real Content-Security-Policy (no bypass) without any violation."""
from __future__ import annotations


def test_interface_runs_under_the_content_security_policy(browser, live_server, evidence):
    context = browser.new_context(viewport={"width": 1400, "height": 1000}, locale="fr-FR")  # no bypass_csp
    page = context.new_page()
    errors = []
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("window.__cspViolations = []; document.addEventListener('securitypolicyviolation', e => window.__cspViolations.push(e.violatedDirective + ' ' + e.blockedURI));")
    response = page.goto(live_server + "/")
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    page.locator("#apiConnectionStatus").filter(has_text="connectée").wait_for()
    page.fill("#asQuestion", "Quelle est la constante de temps d'un circuit RC avec R = 2 kΩ et C = 3 µF ?")
    page.click("#asAsk")
    page.locator("#asAnswer [data-as-calls]").wait_for()
    page.click("#dcSearch")
    page.locator("#dcResult [data-dc-table]").wait_for()
    violations = page.evaluate("window.__cspViolations")
    context.close()
    assert violations == [] and errors == []
    evidence("Interface sous CSP réelle", "Charger la page sans contournement, utiliser l'assistant et le catalogue",
             "Aucune violation de la politique de sécurité, aucune erreur console", "0 violation, 0 erreur")
