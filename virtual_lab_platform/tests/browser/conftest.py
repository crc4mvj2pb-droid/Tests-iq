"""Real-browser (Chromium/Playwright) fixtures for end-to-end interface tests.

These tests click the actual interface served by app.Handler against an isolated
temporary SQLite database. They are skipped, and reported as skipped, when the
optional development dependency `playwright` is not installed.
"""
from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

try:
    import playwright.sync_api as playwright_api
    PLAYWRIGHT_MISSING = None
except ImportError as exc:  # each browser test is then reported as skipped, with this reason
    playwright_api = None
    PLAYWRIGHT_MISSING = f"Playwright non installé ({exc.name}) : pip install -r requirements-dev.txt puis python -m playwright install chromium"


def pytest_collection_modifyitems(config, items):
    if PLAYWRIGHT_MISSING:
        marker = pytest.mark.skip(reason=PLAYWRIGHT_MISSING)
        for item in items:
            if "tests/browser" in str(item.fspath).replace("\\", "/"):
                item.add_marker(marker)

import app
import history

ARTIFACTS = Path(__file__).resolve().parents[2] / "test-artifacts"


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "browser_history.sqlite3")
    # Imported SBML/CSV files go to a temporary copy of the library, never into the project folder.
    import shutil, sbml_engine, scientific_imports
    library = tmp_path / "scientific_library" / "imported_assets"
    shutil.copytree(Path(scientific_imports.ASSET_DIR), library)
    for module in (scientific_imports, sbml_engine):
        monkeypatch.setattr(module, "BASE", tmp_path); monkeypatch.setattr(module, "ASSET_DIR", library)
    monkeypatch.setattr(scientific_imports, "INDEX", library / "index.json")
    import maintenance  # v9.0: backups made during browser tests go to the temporary folder
    monkeypatch.setattr(maintenance, "backup_dir", lambda: tmp_path / "backups")
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


@pytest.fixture(scope="session")
def browser():
    with playwright_api.sync_playwright() as p:
        try:
            instance = p.chromium.launch()
        except Exception as exc:  # Browser binary missing: report as skipped, not passed.
            pytest.skip(f"Chromium could not be launched: {exc}")
        yield instance
        instance.close()


@pytest.fixture
def page(browser, live_server, request):
    context = browser.new_context(accept_downloads=True, viewport={"width": 1400, "height": 1000}, locale="fr-FR")
    context.add_init_script("try{localStorage.setItem('vl-lang','fr')}catch(e){}")
    pg = context.new_page()
    pg.console_errors = []
    pg.on("console", lambda m: m.type == "error" and pg.console_errors.append(m.text))
    pg.on("pageerror", lambda e: pg.console_errors.append("pageerror: " + str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.base_url = live_server
    pg.goto(live_server + "/")
    pg.wait_for_function("document.querySelector('#apiConnectionStatus') && document.querySelector('#apiConnectionStatus').textContent.includes('connectée')")
    yield pg
    failed = getattr(request.node, "rep_call", None)
    if failed is not None and failed.failed:
        ARTIFACTS.mkdir(exist_ok=True)
        pg.screenshot(path=str(ARTIFACTS / f"{request.node.name}.png"), full_page=True)
    context.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item.rep_call = report


@pytest.fixture
def evidence(request):
    """Record feature / steps / expected / observed rows for the generated validation matrix."""
    def record(feature: str, steps: str, expected: str, observed: str) -> None:
        request.node.user_properties.append(("evidence", json.dumps(
            {"feature": feature, "steps": steps, "expected": expected, "observed": observed}, ensure_ascii=False)))
    return record


class Bench:
    """Drive the workbench only through visible controls, like a user."""

    def __init__(self, page):
        self.page = page
        page.click('#wbTabs [data-cat="electrical"]')

    def instances(self):
        return self.page.eval_on_selector_all("#wbBench [data-instance]", "els => els.map(e => e.dataset.instance)")

    def add(self, item_id):
        before = set(self.instances())
        self.page.click(f'#wbCatalog [data-add="{item_id}"]')
        (new,) = set(self.instances()) - before
        return new

    def set_value(self, instance, value):
        self.page.click(f'[data-instance="{instance}"] > strong')
        self.page.fill("#wbPropQty", str(value))

    def wire(self, a, pin_a, b, pin_b):
        self.page.click(f'[data-terminal-instance="{a}"][data-terminal-pin="{pin_a}"]')
        self.page.click(f'[data-terminal-instance="{b}"][data-terminal-pin="{pin_b}"]')

    def solve(self):
        self.page.click("#wbSolveCircuit")
        self.page.wait_for_function("!document.querySelector('#wbSolveCircuit').disabled && !document.querySelector('#wbResult h3').textContent.includes('en cours')")
        return self.page.inner_text("#wbResult")

    def export_state(self):
        with self.page.expect_download() as info:
            self.page.click("#wbExport")
        return json.loads(Path(info.value.path()).read_text(encoding="utf-8"))

    def history(self):
        return self.page.request.get(self.page.base_url + "/api/history").json()["experiments"]

    def reference_circuit(self, volts=9, ohms=1000):
        src, res, gnd = self.add("dc-source"), self.add("resistor"), self.add("ground")
        self.set_value(res, ohms); self.set_value(src, volts)
        self.wire(src, "P", res, "A"); self.wire(res, "B", gnd, "GND"); self.wire(src, "N", gnd, "GND")
        return src, res, gnd


@pytest.fixture
def bench(page):
    return Bench(page)
