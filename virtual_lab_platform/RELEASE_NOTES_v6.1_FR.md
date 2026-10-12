# Notes de version — Virtual Lab Platform v6.1

**Objectif (feuille de route) :**
- référencer chaque constante et chaque paramètre de modèle ;
- stocker la version et les métadonnées de chaque source ;
- ne jamais présenter une valeur approximative sans l'étiqueter.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Une bibliographie unique et complète | `data_catalog/sources.json` (schéma 1.1) compte **36 sources**. Chacune a un type, une référence complète, une année, une licence ou des conditions d'usage, et une version ou une date de consultation. Le contrôle a trouvé deux thèses sans version : c'est maintenant indiqué explicitement (« thèse originale non consultée ; valeurs reprises de Bates & Watts 1988 »). Aucune source orpheline : chacune est citée par au moins un élément (test). |
| Chaque modèle référencé | Les 19 contrats citent des identifiants de source qui existent (`data_catalog/contract_references.json`). Par exemple : Arrhenius 1889, Michaelis & Menten 1913, Kermack & McKendrick 1927, Verhulst 1838, Lotka 1925, Volterra 1926, Lapicque 1907, Fourier 1822. Les méthodes numériques citent Butcher, Dormand & Prince et Hairer & Wanner. Les références de vérification sont Hindmarsh, Carslaw & Jaeger et Murray. Les adaptateurs multi-modèles citent Beer (1852) et Incropera (2007). |
| Chaque paramètre étiqueté | Les **valeurs par défaut numériques** de tous les contrats portent `default_provenance = illustrative`, avec la mention : « valeur choisie pour démontrer le modèle, pas une propriété sourcée d'un système réel ». Aucune valeur par défaut n'est présentée comme sourcée. |
| Chaque constante référencée | Chaque constante de `physical_constants.json` porte un `source_id` : la Brochure SI pour les constantes exactes, CODATA 2018 pour les autres. Une constante mesurée doit avoir une incertitude non nulle (test). |
| Valeurs approchées étiquetées | Chaque unité hors SI acceptée par `units.py` a une définition documentée (`units.DEFINITIONS`) avec sa source et un indicateur exact ou approché. Le dalton est la seule unité approchée (CODATA 2018, incertitude relative 3,0e-10). L'ambiguïté de `ppm` est signalée. Un test vérifie que **toute unité acceptée est documentée**. |
| Contrôle automatique | `references.problems()` liste tout manquement. La suite de tests exige une liste vide, et les cas d'erreur sont testés : source inconnue, valeur par défaut sans étiquette. |
| Exposition | `GET /api/sources` (sources, éléments qui citent chaque source et problèmes éventuels), `GET /api/sources/{id}`. Les contrats exposent `reference_ids` et `default_provenance`. Dans l'interface : section « Bibliographie » du catalogue. |

## Tests
- `tests/test_v61_references.py` : 9 tests.
- 1 test navigateur ajouté dans `tests/browser/test_v60_catalog_ui.py`.

## Limites
- Les références bibliographiques ont été saisies d'après mes connaissances. Je ne les ai pas revérifiées en ligne dans cet environnement (aucun accès aux éditeurs). Les années, revues et pages sont celles couramment citées. **Une relecture par une personne qui a accès aux publications reste recommandée.**
- Étiqueter une valeur « illustrative » ne la rend pas réaliste. Les études réelles doivent remplacer ces valeurs par des données sourcées, par exemple à partir du catalogue de données.
