# Notes de version — Virtual Lab Platform v8.1

**Objectif (feuille de route) :**
- transformer une question en variables, hypothèses testables et critères d'évaluation ;
- demander des précisions lorsque les données ou les objectifs manquent.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Variables | `research_question.formulate` (à règles, sans modèle de langage) repère dans la question un paramètre et une sortie de contrat. Il les accepte seulement si **un modèle les possède tous les deux**. Il en tire : la variable indépendante (unité, valeur de référence, bornes du contrat), la variable dépendante (unité), et les variables contrôlées (valeurs et étiquette « illustrative »). Les expressions plus longues l'emportent : « résistance thermique » n'est pas confondue avec « résistance ». |
| Hypothèses testables | Trois hypothèses : H1 (augmente), H2 (diminue), H0 (pas d'effet notable). Chacune a un **test calculable** : sensibilité normalisée S = (∂y/∂x)·(x/y), avec le seuil \|S\| < 0,05 pour H0, et sens de variation sur la plage balayée. |
| Précisions plutôt que suppositions | Variable observée absente, paramètre inconnu ou plusieurs modèles possibles : le statut est `clarification_needed`, avec la liste des choix valides. Une combinaison qu'aucun modèle ne possède donne `unknown`. |
| Portée | Une note rappelle que les hypothèses sont testées **sur le modèle, pas sur le système réel**, et précise si le modèle n'est pas validé sur données. |
| Exposition | `POST /api/research/formulate`. Bouton « Formuler une question de recherche » dans le panneau de l'assistant. |

## Tests
- `tests/test_v81_research_question.py` : 11 tests.
- `tests/browser/test_v81_ui.py` : 1 test en navigateur réel.

## Limites
- Vocabulaire limité à une table de synonymes français et anglais. Une formulation hors table donne une demande de précision.
