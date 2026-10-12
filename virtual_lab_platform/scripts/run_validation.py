"""Run the full test suite and generate the validation matrix from the observed results.

Usage:  python scripts/run_validation.py
Writes: test-artifacts/junit.xml, VALIDATION_MATRIX_v<version>.md and TEST_RESULTS_v<version>.txt
No number in the generated files is written by hand: everything comes from this run.
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from version import APP_VERSION  # noqa: E402

NOT_COVERED = [
    "Safari / macOS et Windows : non exécutés par cette commande (Chromium headless uniquement).",
    "Glisser-déposer à la souris : non couvert ; les composants sont ajoutés par les boutons « + Ajouter ».",
    "Lanceurs launch_macos_linux.sh / launch_windows.bat : non exécutés par cette commande.",
    "Les résultats sont des calculs simulés, pas des mesures expérimentales.",
]


def _status(case: ET.Element) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return "échoué"
    if case.find("skipped") is not None:
        return "ignoré"
    return "passé"


def main() -> int:
    artifacts = ROOT / "test-artifacts"
    artifacts.mkdir(exist_ok=True)
    junit = artifacts / "junit.xml"
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}", "-o", "junit_family=xunit1"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(proc.stdout[-3000:]); print(proc.stderr[-2000:], file=sys.stderr)
    if not junit.exists():
        print("pytest did not produce a JUnit report", file=sys.stderr)
        return proc.returncode or 1

    cases = list(ET.parse(junit).getroot().iter("testcase"))
    counts = {"passé": 0, "échoué": 0, "ignoré": 0}
    rows = []
    for case in cases:
        status = _status(case); counts[status] += 1
        for prop in case.iter("property"):
            if prop.get("name") == "evidence":
                ev = json.loads(prop.get("value"))
                rows.append((ev, status, f"{case.get('classname')}::{case.get('name')}"))
        if status == "ignoré" and "browser" in (case.get("classname") or ""):
            msg = case.find("skipped").get("message", "")
            rows.append(({"feature": case.get("name"), "steps": "—", "expected": "—", "observed": "non exécuté : " + msg}, "impossible à lancer", f"{case.get('classname')}::{case.get('name')}"))

    try:
        import playwright  # noqa: F401
        from importlib.metadata import version as pkg_version
        pw = pkg_version("playwright")
    except Exception:
        pw = "non installé"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    env = f"Python {platform.python_version()} · {platform.platform()} · Playwright {pw}"
    summary = f"{counts['passé']} passés, {counts['échoué']} échoués, {counts['ignoré']} ignorés (total {len(cases)})"

    esc = lambda t: str(t).replace("|", "\\|").replace("\n", " ")
    lines = [f"# Matrice de validation — Virtual Lab Platform v{APP_VERSION}", "",
             f"Générée automatiquement par `python scripts/run_validation.py` le {now}.", f"Environnement : {env}.", "",
             f"**Résultat global : {summary}.** Code de sortie pytest : {proc.returncode}.", "",
             "| Fonctionnalité | Étapes | Attendu | Observé | Statut | Preuve (test) |", "|---|---|---|---|---|---|"]
    lines += [f"| {esc(ev['feature'])} | {esc(ev['steps'])} | {esc(ev['expected'])} | {esc(ev['observed'])} | {status} | `{esc(test)}` |" for ev, status, test in rows]
    lines += ["", "## Non couvert par cette commande", ""] + [f"- {x}" for x in NOT_COVERED]
    (ROOT / f"VALIDATION_MATRIX_v{APP_VERSION}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    failed = [f"{c.get('classname')}::{c.get('name')}" for c in cases if _status(c) == "échoué"]
    skipped = [f"{c.get('classname')}::{c.get('name')} — {c.find('skipped').get('message', '')}" for c in cases if _status(c) == "ignoré"]
    report = [f"Virtual Lab Platform v{APP_VERSION} — rapport de tests généré", f"Date : {now}", f"Environnement : {env}",
              f"Commande : {' '.join(['python'] + cmd[1:])}", f"Résultat : {summary} ; code de sortie {proc.returncode}", "",
              "Échecs :"] + ([f"- {x}" for x in failed] or ["- aucun"]) + ["", "Ignorés :"] + ([f"- {x}" for x in skipped] or ["- aucun"]) + \
             ["", "Non couvert :"] + [f"- {x}" for x in NOT_COVERED]
    (ROOT / f"TEST_RESULTS_v{APP_VERSION}.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Matrix: VALIDATION_MATRIX_v{APP_VERSION}.md — {summary}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
