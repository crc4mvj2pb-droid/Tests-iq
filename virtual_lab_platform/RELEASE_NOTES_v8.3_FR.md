# Notes de version — Virtual Lab Platform v8.3

**Objectif (feuille de route) :**
- exécuter les étapes dans un graphe de tâches traçable ;
- valider les entrées avant chaque étape, avec des limites de temps et de ressources ;
- annuler réellement les tâches lorsque c'est possible, sinon dire honnêtement ce qui continue en arrière-plan.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Graphe de tâches traçable | `task_graph.py` enchaîne 6 nœuds : validation, référence, double, balayage, sensibilité et analyse. Chaque nœud indique ses dépendances, son état (en attente, terminé, échoué, arrêté, ignoré, annulé), sa durée, sa sortie ou son erreur. L'ordre des dépendances est vérifié par un test. |
| Validation avant chaque étape | Le plan entier est validé d'abord par le contrat. **Chaque exécution du modèle est validée à nouveau juste avant d'être lancée.** Si le double diffère de la référence, le nœud échoue (déterminisme non prouvé) et les dépendants sont ignorés. |
| Limites | Budget de temps (par défaut 120 s, plafond 600 s) et nombre maximal d'exécutions du modèle (par défaut 200, plafond 2 000 ; l'analyse de sensibilité compte pour ses 5 exécutions). Quand une limite est atteinte, le nœud en cours s'arrête, la cause est indiquée, les nœuds restants sont ignorés et **aucun résultat n'est extrapolé** (tests pour chaque limite). |
| Annulation réelle | Un plan lancé comme tâche de fond (`POST /api/jobs`, `kind = research_plan`) vérifie l'annulation entre deux exécutions. Mesure : arrêt environ 0,1 s après la demande (3 essais), état `cancelled`, **aucun résultat partiel publié**. Rien ne continue en arrière-plan. |
| Résultats | Effet de la résistance sur la constante de temps : croissant, sensibilité normalisée 1,000. Effet de la puissance sur cette même constante : **sortie constante, sensibilité nulle**. C'est un cas H0 réel, car τ = R·C ne dépend pas de P. |
| Interface | Boutons « Exécuter le plan » et « Annuler » dans le panneau de l'assistant, avec le tableau des tâches. |

## Tests
- `tests/test_v83_task_graph.py` : 7 tests.
- `tests/browser/test_v83_ui.py` : 1 test en navigateur réel.

## Limites
- L'annulation est vérifiée entre deux exécutions du modèle. Une exécution individuelle très longue (par exemple Hodgkin–Huxley sur 5 s) va jusqu'à son terme avant l'arrêt.
