"""Run an axe-core accessibility audit of the interface in Chromium (requires Playwright).

Usage:  python scripts/accessibility_audit.py [--contrast]
Prints violations by impact; with --contrast, lists each colour pair failing WCAG AA contrast.
"""
from __future__ import annotations

import sys
import tempfile
import threading
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AXE = ROOT / "tests" / "browser" / "vendor" / "axe-core-4.10.2" / "axe.min.js"
ORDER = ["critical", "serious", "moderate", "minor"]


def audit(page) -> list[dict]:
    page.add_script_tag(path=str(AXE))
    return page.evaluate("""async () => (await axe.run(document, {resultTypes: ['violations']})).violations.map(v => ({
        id: v.id, impact: v.impact, help: v.help,
        nodes: v.nodes.map(n => ({target: n.target.join(' '), data: (n.any[0] || {}).data || null}))}))""")


def main() -> int:
    import history
    history.DB_PATH = Path(tempfile.mkdtemp()) / "audit.sqlite3"
    import app
    from playwright.sync_api import sync_playwright
    app.Handler.log_message = lambda *a: None
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(); page = browser.new_page()
            page.goto(f"http://127.0.0.1:{srv.server_address[1]}/"); page.wait_for_timeout(1500)
            violations = sorted(audit(page), key=lambda v: ORDER.index(v["impact"]))
            browser.close()
    finally:
        srv.shutdown()
    for v in violations:
        print(f"{v['impact']:9} {v['id']:40} {len(v['nodes']):3}  {v['help']}  e.g. {v['nodes'][0]['target']}")
    if "--contrast" in sys.argv:
        pairs = Counter()
        for v in violations:
            if v["id"] == "color-contrast":
                for n in v["nodes"]:
                    d = n["data"] or {}
                    pairs[(d.get("fgColor"), d.get("bgColor"), d.get("contrastRatio"), d.get("expectedContrastRatio"))] += 1
        for (fg, bg, ratio, expected), count in pairs.most_common():
            print(f"contrast {count:3}× fg {fg} on bg {bg}: {ratio} (needs {expected})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
