"""Set the application version in version.py, the page title and the footer (one command per release)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    new = sys.argv[1]
    if not re.fullmatch(r"\d+\.\d+", new):
        print("usage: python scripts/set_version.py X.Y"); return 2
    (ROOT / "version.py").write_text(re.sub(r'APP_VERSION = "[^"]+"', f'APP_VERSION = "{new}"', (ROOT / "version.py").read_text(encoding="utf-8")), encoding="utf-8")
    html_path = ROOT / "static" / "index.html"
    html = html_path.read_text(encoding="utf-8")
    html = re.sub(r"<title>Virtual Lab Platform v[\d.]+</title>", f"<title>Virtual Lab Platform v{new}</title>", html)
    html = re.sub(r"<footer>Virtual Lab Platform v[\d.]+ ·", f"<footer>Virtual Lab Platform v{new} ·", html)
    html_path.write_text(html, encoding="utf-8")
    print(f"version set to {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
