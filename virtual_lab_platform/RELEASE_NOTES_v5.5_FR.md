# Notes de version — Virtual Lab Platform v5.5

**Objectif (feuille de route) :** rendre les balayages robustes, annulables et exportables ; séparer la variation de paramètre, l'incertitude instrumentale et l'incertitude de modèle ; vérifier les graines aléatoires, la reproductibilité et les intervalles ; éviter d'interpréter une corrélation ou un ajustement comme une preuve causale.

## Critères d'acceptation et résultat
| Critère | Résultat |
|---|---|
| Balayages robustes | `analysis.parameter_sweep` fonctionne pour **tout modèle à contrat** (18 modèles), avec grille explicite, linéaire ou logarithmique. Un point en échec est enregistré avec son code (par exemple `out_of_range`) et le balayage continue. Les entrées sont validées par le contrat et les sorties portent leurs unités. |
| Annulables | `jobs.py` : tâches en arrière-plan avec progression et annulation réelle entre deux évaluations. Une évaluation déjà commencée se termine, puis la tâche s'arrête, et **aucun résultat partiel n'est publié**. Routes : `POST /api/jobs`, `GET /api/jobs/{id}`, `POST /api/jobs/{id}/cancel`. |
| Exportables | `GET /api/jobs/{id}.csv`, avec les unités dans les en-têtes, ainsi que l'export JSON par la tâche. |
| Sensibilité locale | Coefficients normalisés S = (∂y/∂p)(p/y) par différences centrées à h et h/2, combinées par extrapolation de Richardson, avec un indicateur de convergence. **Vérifiés contre des élasticités analytiques** : τ = RC (S = 1 pour R et pour C), ω₀ = 1/√(LC) (S = −0,5), Arrhenius (S_A = 1, S_Ea = −Ea/RT, S_T = +Ea/RT), à 1e-6 près. |
| Monte Carlo | Lois normale, uniforme, lognormale et triangulaire, avec graine. Résultats : moyenne, écart-type, erreur-type, quantiles 2,5/50/97,5 %, **intervalle bootstrap de la moyenne** et contrôle de convergence (première moitié contre ensemble). Les tirages hors des bornes du contrat sont refusés et comptés : les lois sont donc tronquées, et c'est indiqué. |
| Types d'incertitude séparés | `uncertainty_breakdown` : *paramètre* (la dispersion propagée), *numérique* (l'erreur de solveur estimée par le moteur pour les tirages, par exemple en cinétique) et *mesure* (combinaison quadratique avec l'écart-type d'un instrument, seulement si on le fournit). |
| Reproductibilité et intervalles | Même graine → résultats identiques ; graine différente → résultats différents. **Couverture de l'intervalle bootstrap de la moyenne vérifiée sur 100 graines** : il contient la vraie moyenne entre 88 et 99 % des fois, pour 95 % attendu. La dispersion de τ = R·C avec R ~ N(1000, 50) correspond à la valeur analytique (5e-5 s, à 15 % près). |
| Pas d'interprétation causale | Chaque résultat contient un avertissement : un balayage, une sensibilité, une corrélation ou un bon ajustement ne prouvent pas un mécanisme causal réel. |
| Interface | Panneau « Analyses paramétriques » : balayage avec courbe et tableau, sensibilité, Monte Carlo, barre de progression, bouton Annuler, export CSV. 3 tests navigateur. |

## Défaut trouvé et corrigé
**Gestionnaire central d'erreurs réseau (v4.8)** : il transformait **toute** réponse non JSON de l'API en erreur, y compris un export CSV légitime. Il ne réécrit plus que les pages HTML et les erreurs non JSON. Trouvé par le test navigateur d'export.

## Tests
`tests/test_v55_analysis.py` (18 tests) et `tests/browser/test_v55_analysis_ui.py` (3 tests).

## Limites
- Les tirages Monte Carlo sont **indépendants** : les corrélations entre paramètres ne sont pas modélisées.
- La sensibilité est **locale** (autour du point de base) : pas d'analyse globale (Sobol, Morris).
- Les tâches vivent en mémoire : elles disparaissent à l'arrêt du serveur. Les résultats sont à exporter.
- L'incertitude de **forme du modèle** (l'écart entre le modèle et la réalité) n'est pas estimée : elle demande des données (jalon C).
