"""v9.4 — installation check: the real server started with temporary data passes every check."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_install_check_passes():
    proc = subprocess.run([sys.executable, "scripts/install_check.py"], cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[FAIL]" not in proc.stdout and "checks passed" in proc.stdout


def test_documentation_exists_and_points_to_the_guides():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in ("GUIDE_UTILISATEUR_FR.md", "GUIDE_ADMINISTRATION_FR.md", "INSTALLATION_FR.md"):
        assert (ROOT / name).is_file() and name in readme + (ROOT / "GUIDE_ADMINISTRATION_FR.md").read_text(encoding="utf-8")
    admin = (ROOT / "GUIDE_ADMINISTRATION_FR.md").read_text(encoding="utf-8")
    assert "Procédure de support" in admin and "hors de l'ordinateur" in admin and "mode récupération" in admin
