# Notes de version — Virtual Lab Platform v8.5

**Objectif (feuille de route) :**
- proposer l'expérience suivante en fonction d'un objectif explicite ;
- optimiser des paramètres sous contraintes connues, en expliquant le critère d'optimisation ;
- comparer plusieurs plans et conserver la décision de l'utilisateur.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Expérience suivante, objectif explicite | Objectif « estimer précisément Vm et K » sur un jeu du catalogue. `next_measurement` ajuste le modèle, puis classe les concentrations candidates selon le **critère D-optimal** : gain de det(JᵀJ) du plan augmenté (Puromycine : 12 points actuels). **Vérification** : le critère retrouve le plan D-optimal analytique à 2 points de Duggleby (1979), à 1e-3 près, par recherche sur une grille fine. Par défaut, seules les propositions **dans la plage déjà mesurée** sont retenues ; l'extrapolation doit être autorisée explicitement et reste alors signalée. |
| Optimisation sous contraintes | Objectif « atteindre une valeur cible » : `reach_target` cherche par dichotomie la valeur du paramètre qui donne la sortie voulue, dans les bornes du contrat ou dans des bornes fournies. Exemple : τ = 4,7 ms donne R = 4 700 Ω, valeur recontrôlée par une exécution du modèle. Une cible hors de portée est déclarée **inatteignable** avec la plage atteignable : bornes trop étroites, ou τ visé en faisant varier P alors que τ n'en dépend pas. |
| Critère expliqué | Chaque proposition indique son critère et ses réserves : optimalité locale qui dépend des estimations actuelles ; hypothèse de monotonie pour la dichotomie. |
| Comparer les plans et conserver la décision | `compare_plans` classe des plans selon un critère numérique déclaré ; un plan qui ne le déclare pas est refusé. `record_decision` enregistre l'objectif, les alternatives, le choix et sa justification dans SQLite (table `research_decisions`). Un choix qui n'est pas parmi les alternatives est refusé. |
| Exposition | `POST /api/research/next-measurement`, `POST /api/research/target`, `POST` et `GET /api/research/decisions`. Dans le panneau de l'assistant : champ « Valeur cible », bouton « Trouver le paramètre », puis « Retenir ce plan ». |

## Tests
- `tests/test_v85_iterative_planning.py` : 7 tests.
- `tests/browser/test_v85_ui.py` : 1 test en navigateur réel.

## Limites
- Le plan D-optimal est local : il suppose les estimations actuelles proches des vraies valeurs. Il ne remplace pas un plan robuste ou bayésien.
- La dichotomie suppose une sortie monotone sur l'intervalle. Dans le cas contraire, une seule des solutions possibles est trouvée.
