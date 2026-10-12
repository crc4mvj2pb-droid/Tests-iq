# Notes de version — Virtual Lab Platform v5.0

**Objectif (feuille de route, jalon B) :** une architecture commune aux moteurs scientifiques, c'est-à-dire un contrat par modèle, une validation des paramètres standardisée, une réponse API standard, des couches séparées et des tests de contrat pour tous les moteurs.

## Critères d'acceptation (fixés avant le code) et résultat
| Critère | Résultat |
|---|---|
| Chaque moteur a un contrat lisible par machine : identifiant, version, paramètres typés avec unités et bornes, sorties avec unités, hypothèses, validité, codes d'erreur, références | 17 contrats (`model_registry.py`) : 5 électriques, 2 chimiques et les 10 modèles du catalogue. Tous sont bien formés (`check_contract`). |
| Les entrées sont validées avant tout calcul | `validate_inputs` : paramètres inconnus refusés, types, bornes et choix vérifiés, défauts appliqués, codes stables. |
| Les contrats sont fidèles aux moteurs | Pour chaque modèle sans paramètre obligatoire, le résultat obtenu avec les défauts du contrat est **identique** à celui du moteur avec ses propres défauts. |
| Réponse API standard | `POST /api/models/{id}/run` renvoie l'enveloppe standard ; `GET /api/contracts` et `/api/contracts/{id}`. |
| Format d'erreur unique | Toute réponse d'erreur porte `error_code`, testé sur 8 types d'erreurs. |
| Couches séparées | Les moteurs n'importent ni l'interface ni la persistance (test statique). Voir `ARCHITECTURE_FR.md`. |

## Défaut trouvé par les tests de contrat
Mon premier contrat de `enzyme_kinetics` donnait des valeurs par défaut à `vmax`, `km` et `s_max`, alors que le moteur les exige. Le contrat les déclare maintenant obligatoires.

## Tests
`tests/test_v50_contracts.py` : 67 tests (contrats bien formés, sorties déclarées présentes, équivalence des défauts, bornes, types, codes d'erreur, API, séparation des couches).

## Limites
- **Pas de parcours dans l'interface** pour les contrats en v5.0 : ils sont servis par l'API. Ils seront visibles dans le catalogue en v5.7.
- La mesure reliée, le protocole et le concepteur restent exécutés par le service d'expériences : ils dépendent d'un dossier ou d'un catalogue. Ils n'ont pas de contrat `run_model`.
- Les unités sont déclarées, mais pas encore converties ni contrôlées dimensionnellement. C'est l'objet de la v5.1.
- Les références citées sont des sources générales (articles fondateurs, manuels). Le référencement précis par paramètre est prévu en v6.1.
