# Notes de version — Virtual Lab Platform v7.6

**Objectif (feuille de route) :**
- relier deux modèles ou plus au moyen d'adaptateurs testés ;
- montrer l'effet de chaque hypothèse et les incertitudes propagées.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Modèles reliés par des adaptateurs testés | Chaîne interdisciplinaire « circuit électrique → échauffement thermique → Arrhenius → cinétique chimique » (v5.8). Tous ses maillons sont désormais vérifiés (v7.1). |
| Incertitudes propagées | `pipeline_analysis.monte_carlo` tire les entrées incertaines (lois normale, uniforme, log-normale, triangulaire) et exécute la chaîne entière à chaque tirage. Il fournit pour chaque sortie : valeur nominale, moyenne, écart-type et intervalle 2,5–97,5 %. Les tirages en échec sont **comptés**, jamais cachés. Les résultats sont reproductibles avec la graine. **Contrôles** : l'écart-type de la température correspond à la propagation analytique au premier ordre (±6 % sur 1 500 tirages) ; avec seule l'énergie d'activation incertaine, la moyenne de k suit la loi log-normale exacte, exp(σ²/2) (±5 %). La portée est écrite : seule l'incertitude paramétrique est propagée, pas celle des formes de modèle. |
| Effet de chaque hypothèse | `hypothesis_effects` relance la chaîne pour chaque hypothèse alternative et donne la variation de chaque sortie : ambiance à 20 °C (−5 K), chauffage coupé (−12 K, effet le plus fort sur la température), isolation doublée (+12 K, effet le plus fort sur la vitesse de réaction). Une note rappelle que les effets ne s'additionnent pas en général. |
| Exposition | `POST /api/pipelines/uncertainty`, `POST /api/pipelines/hypotheses`, `GET /api/pipelines/uncertainty-example`. Deux boutons dans le panneau multi-modèles : « Propager les incertitudes » et « Effet des hypothèses ». |

## Tests
- `tests/test_v76_interdisciplinary.py` : 9 tests.
- `tests/browser/test_v76_ui.py` : 1 test en navigateur réel.

## Limites
- Les incertitudes des entrées de l'exemple sont illustratives, pas mesurées.
- Monte Carlo est synchrone et plafonné à 5 000 tirages. Les tâches de fond annulables de la v5.5 restent prévues pour les modèles uniques.
