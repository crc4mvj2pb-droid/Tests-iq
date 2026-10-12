# Notes de version — Virtual Lab Platform v7.0

**Objectif (feuille de route) :**
- interfaces communes pour les unités, les solveurs, les jeux de données, les paramètres et les visualisations ;
- un catalogue où les niveaux de maturité sont visibles.

Règle du jalon D : n'élargir qu'un domaine à la fois, chacun avec un périmètre limité, validé avant le suivant.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Domaines définis | `domains.py` définit 7 domaines : circuits électriques linéaires, cinétique et stœchiométrie, thermique, biologie quantitative, neurosciences computationnelles, biomédical exploratoire, processus environnementaux. Chacun a un **périmètre** et des **exclusions explicites**, par exemple « aucun jumeau du cerveau humain » ou « aucune prédiction clinique ». Le domaine biomédical porte un avertissement. |
| Interfaces communes | Les unités et paramètres viennent des contrats v5.0. Les jeux de données sont des identifiants du catalogue v6.0, et leur existence est vérifiée. Les **spécifications de graphiques** (lignes, x, y) sont contrôlées sur le résultat réel de chaque modèle (`plot_problems()` vide). |
| Chaque modèle dans un seul domaine | Vérifié par un test : les 19 contrats sont répartis sans doublon ni oubli. |
| Banc d'essai par domaine | Chaque domaine doit avoir **au moins un cas indépendant** dans `benchmarks/independent_suite.py`. **Le contrôle a révélé un manque** : le domaine « processus environnementaux » n'en avait aucun. Deux cas ont été ajoutés : charge après trois demi-vies (exact), et aire sous la courbe pharmacocinétique = dose/clairance (écart 2,4e-4, conforme à l'erreur prévue des trapèzes et de la queue tronquée). Le banc compte désormais **35 cas**. |
| Statut de validation explicite et dérivé | Le niveau d'un domaine est **calculé** à partir de la maturité de ses modèles : le plus bas l'emporte. Il est accompagné des comptes par niveau, dont le nombre de modèles validés sur données. Il n'est jamais saisi à la main. |
| Exposition | `GET /api/domains` (domaines et problèmes éventuels). Section « Domaines scientifiques » de l'interface : périmètre, exclusions, nombre de cas de référence, données et statut. |

## Tests
- `tests/test_v70_domains.py` : 6 tests.
- `tests/browser/test_v70_domains_ui.py` : 1 test en navigateur réel.

## Limites
- Aujourd'hui, tous les domaines sont au niveau « vérifié » au mieux : aucun modèle n'est encore validé sur données (prévu en v7.3).
