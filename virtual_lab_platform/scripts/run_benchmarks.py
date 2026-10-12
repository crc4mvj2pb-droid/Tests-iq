"""Run the independent benchmark suite and generate BENCHMARK_REPORT_FR.md (v5.9).

Usage: python scripts/run_benchmarks.py [--output PATH]
Every number in the report is computed by this run; nothing is typed by hand. Exit code 1 if a
case fails, a known limit is no longer reproduced, or an expected refusal did not happen.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.independent_suite import CASES, GOOD_STATUSES, INCIDENTS, run_suite  # noqa: E402
from version import APP_VERSION  # noqa: E402

STATUS_FR = {"pass": "conforme", "fail": "**ÉCHEC**", "limit_reproduced": "limite reproduite", "limit_changed": "**limite modifiée**",
             "refused_as_expected": "refus attendu obtenu", "not_refused": "**non refusé**", "error": "**erreur**"}


def _num(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.10g}"
    return str(v)


def report(rows: list[dict]) -> str:
    counts = Counter(r["status"] for r in rows)
    domains = sorted({r["domain"] for r in rows})
    models = sorted({r["model"] for r in rows})
    lines = [f"# Banc d'essai indépendant — Virtual Lab Platform v{APP_VERSION}", "",
             f"Généré par `python scripts/run_benchmarks.py` le {datetime.now(timezone.utc).isoformat(timespec='seconds')} (Python {platform.python_version()}).",
             "Les références sont calculées dans `benchmarks/independent_suite.py` : formule fermée, table publiée ou intégrateur écrit à part. "
             "Ce fichier n'est importé par aucun test unitaire de moteur. Les tolérances ont été fixées avant la première exécution, à partir de l'erreur "
             "connue de chaque méthode (colonne « Base de la tolérance »).", "",
             "## Synthèse", "",
             f"- **{len(rows)} cas**, {len(models)} moteurs ou modules, {len(domains)} domaines ({', '.join(domains)}).",
             f"- Conformes : {counts['pass']} · limites connues reproduites : {counts['limit_reproduced']} · refus attendus obtenus : {counts['refused_as_expected']}.",
             f"- Échecs : {counts['fail']} · limites modifiées : {counts['limit_changed']} · non refusés : {counts['not_refused']} · erreurs : {counts['error']}.",
             f"- Verdict : **{'tous les cas ont le résultat attendu' if all(r['status'] in GOOD_STATUSES for r in rows) else 'AU MOINS UN CAS NE DONNE PAS LE RÉSULTAT ATTENDU'}**.", "",
             "## Résultats", "",
             "| Cas | Domaine | Moteur | Type de référence | Observé | Référence | Écart | Tolérance | Base de la tolérance | Statut |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        tol = "—" if r["tolerance"] is None else f"{r['tolerance']:g}{' (relative)' if r['relative'] else ' (absolue)'}"
        if r["expectation"] == "known_limit":
            tol = f"écart > {r['limit_threshold']:g}" + ("" if r["tolerance"] is None else f" et ≤ {r['tolerance']:g}")
        observed = _num(r["observed"]) if r["status"] not in ("refused_as_expected", "error") else f"refus : `{r['refusal'][:110]}`"
        lines.append(f"| {r['title']} | {r['domain']} | `{r['model']}` | {r['reference_kind']} — {r['source']} | {observed} | {_num(r['reference'])} | "
                     f"{_num(r['deviation'])} | {tol} | {r['tolerance_basis']} | {STATUS_FR[r['status']]} |")
    lines += ["", "## Résultats négatifs et limites documentées", ""]
    for r in rows:
        if r["expectation"] == "known_limit":
            lines.append(f"- **{r['title']}** : écart observé {_num(r['deviation'])} (seuil de limite {r['limit_threshold']:g}). {r['tolerance_basis']}.")
        elif r["expectation"] == "refused":
            lines.append(f"- **{r['title']}** : le moteur refuse au lieu de renvoyer un résultat faux (`{(r.get('refusal') or '')[:140]}`).")
    lines += ["", "## Incidents de la première exécution", ""] + [f"- {i}" for i in INCIDENTS]
    lines += ["", "## Ce que ce banc ne montre pas", "",
              "- Il vérifie que les moteurs résolvent correctement **leurs équations**. Il ne valide pas ces équations contre des mesures réelles (niveau « validé sur données », jalon C et v7).",
              "- Aucun solveur de circuits externe (ngspice) n'est disponible dans l'environnement : les références électriques sont analytiques.",
              "- Les cas de Robertson ne sont exacts qu'à 5 chiffres significatifs (précision de la table publiée)."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "BENCHMARK_REPORT_FR.md"))
    parser.add_argument("--json", default=None, help="optional path for the raw results")
    args = parser.parse_args()
    rows = run_suite()
    Path(args.output).write_text(report(rows), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = [r["id"] for r in rows if r["status"] not in GOOD_STATUSES]
    print(f"Benchmark: {len(rows) - len(bad)}/{len(CASES)} cases with the expected outcome -> {args.output}" + (f"; unexpected: {', '.join(bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
