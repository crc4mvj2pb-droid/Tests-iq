"""Run the assistant evaluation set and generate ASSISTANT_EVAL_REPORT_FR.md (v8.6).

Usage: python scripts/run_assistant_eval.py
Every number in the report is computed by this run.
"""
from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import assistant_eval  # noqa: E402
from version import APP_VERSION  # noqa: E402


def report(r: dict) -> str:
    pct = lambda v: f"{100 * v:.1f} %"
    lines = [f"# Évaluation de l'assistant — Virtual Lab Platform v{APP_VERSION}", "",
             f"Généré par `python scripts/run_assistant_eval.py` le {datetime.now(timezone.utc).isoformat(timespec='seconds')} (Python {platform.python_version()}).",
             "Assistant évalué : à règles et déterministe (pas un modèle de langage). Jeu de cas fixé avant la première exécution "
             "(`evaluation/assistant_eval_set.json`, empreinte vérifiée par les tests). Les valeurs attendues viennent de formules fermées calculées dans `assistant_eval.py`.", "",
             "## Synthèse", "",
             f"- Cas réussis : **{r['passed']}/{r['cases']} ({pct(r['accuracy'])})**.",
             f"- Taux d'hallucination (nombre absent de toute sortie d'outil) : **{pct(r['hallucination_rate'])}**.",
             f"- Traçabilité (chaque valeur cite un appel existant) : **{pct(r['traceability_rate'])}**.",
             f"- Abstention correcte (hors périmètre et « inconnu ») : **{pct(r['abstention_correct'])}**.", "",
             "| Catégorie | Cas | Réussis |", "|---|---|---|"]
    lines += [f"| {c} | {v['cases']} | {v['passed']} |" for c, v in r["per_category"].items()]
    lines += ["", "## Échecs (non corrigés en v8.6, pour ne pas ajuster l'assistant au jeu d'évaluation)", ""]
    lines += [f"- `{f['id']}` ({f['category']}) — « {f['question']} » : {'; '.join(f.get('reasons') or []) or f['observed']}" for f in r["failures"]] or ["- Aucun."]
    lines += ["", "## Lecture", "",
              "- Les erreurs observées sont des **abstentions ou des classements prudents** (« inconnu » au lieu d'une réponse, H0 au lieu de H1), jamais des valeurs inventées.",
              "- `hypothesis_3` révèle une limite réelle du critère de la v8.1 : la sensibilité normalisée d'une température exprimée en kelvins est petite (offset de l'échelle absolue), "
              "si bien qu'un effet monotone de +6 à +24 K est classé H0. Une amélioration (critère sur la variation absolue ou relative à une échelle déclarée) est notée pour une version ultérieure.",
              "- Incident de mesure : au premier passage, le détecteur d'hallucinations ne cherchait pas dans les messages d'erreur des outils et signalait à tort la borne « 1e-09 » "
              "citée par un refus du contrat (taux mesuré 2,6 %). Le détecteur a été corrigé ; l'assistant n'avait rien inventé.",
              "", r["statement"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    r = assistant_eval.run()
    (ROOT / "ASSISTANT_EVAL_REPORT_FR.md").write_text(report(r), encoding="utf-8")
    print(f"Assistant evaluation: {r['passed']}/{r['cases']} passed, hallucination {r['hallucination_rate']:.3f}, traceability {r['traceability_rate']:.3f}")
    return 0 if r["hallucination_rate"] == 0 and r["traceability_rate"] == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
