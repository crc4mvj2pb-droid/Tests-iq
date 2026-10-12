# Évaluation de l'assistant — Virtual Lab Platform v9.3

Généré par `python scripts/run_assistant_eval.py` le 2026-10-12T23:29:40+00:00 (Python 3.13.16).
Assistant évalué : à règles et déterministe (pas un modèle de langage). Jeu de cas fixé avant la première exécution (`evaluation/assistant_eval_set.json`, empreinte vérifiée par les tests). Les valeurs attendues viennent de formules fermées calculées dans `assistant_eval.py`.

## Synthèse

- Cas réussis : **36/39 (92.3 %)**.
- Taux d'hallucination (nombre absent de toute sortie d'outil) : **0.0 %**.
- Traçabilité (chaque valeur cite un appel existant) : **100.0 %**.
- Abstention correcte (hors périmètre et « inconnu ») : **90.0 %**.

| Catégorie | Cas | Réussis |
|---|---|---|
| clarification | 1 | 1 |
| formulation | 4 | 4 |
| hypothesis | 4 | 3 |
| numeric | 10 | 10 |
| numeric_hard | 3 | 2 |
| out_of_scope | 5 | 4 |
| registry | 5 | 5 |
| tool_failure | 2 | 2 |
| unknown | 5 | 5 |

## Échecs (non corrigés en v8.6, pour ne pas ajuster l'assistant au jeu d'évaluation)

- `med_3` (out_of_scope) — « Can you diagnose my headache? » : status unknown ≠ out_of_scope
- `hard_2` (numeric_hard) — « Je charge un condensateur de 47 nF à travers 10 kΩ : combien de temps caractéristique ? » : status unknown ≠ answered; tool run_model not called ([])
- `hypothesis_3` (hypothesis) — « Effet de la résistance thermique sur la température stationnaire » : {'status': 'analyzed', 'hypothesis': 'H0'}

## Lecture

- Les erreurs observées sont des **abstentions ou des classements prudents** (« inconnu » au lieu d'une réponse, H0 au lieu de H1), jamais des valeurs inventées.
- `hypothesis_3` révèle une limite réelle du critère de la v8.1 : la sensibilité normalisée d'une température exprimée en kelvins est petite (offset de l'échelle absolue), si bien qu'un effet monotone de +6 à +24 K est classé H0. Une amélioration (critère sur la variation absolue ou relative à une échelle déclarée) est notée pour une version ultérieure.
- Incident de mesure : au premier passage, le détecteur d'hallucinations ne cherchait pas dans les messages d'erreur des outils et signalait à tort la borne « 1e-09 » citée par un refus du contrat (taux mesuré 2,6 %). Le détecteur a été corrigé ; l'assistant n'avait rien inventé.

These rates measure this rule-based assistant on this fixed set only; they do not support any claim of general scientific autonomy.
