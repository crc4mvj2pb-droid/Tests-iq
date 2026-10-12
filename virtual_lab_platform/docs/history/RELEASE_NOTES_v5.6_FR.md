# Notes de version — Virtual Lab Platform v5.6

**Objectif (feuille de route) :** vérifier la prise en charge SBML réellement implémentée et signaler les éléments non pris en charge ; valider les unités, paramètres, espèces, réactions et conditions initiales importés ; préserver le fichier source et sa provenance ; tester des fichiers valides, invalides et des fonctionnalités inconnues.

## Défaut grave trouvé par l'audit de cette version, et corrigé
Le moteur SBML annonçait refuser les règles, mais **il cherchait une balise `rule` qui n'existe pas en SBML** (les vraies balises sont `assignmentRule`, `rateRule` et `algebraicRule`). Un modèle contenant une règle sur un paramètre déclaré constant était donc **simulé en ignorant la règle, sans aucun avertissement**. Reproduit : avec une règle imposant k = 5, le moteur calculait avec k = 0,5. Ce modèle est maintenant refusé, avec la liste des éléments en cause.

## Critères d'acceptation et résultat
| Critère | Résultat |
|---|---|
| Signaler les éléments non pris en charge | `analyze_sbml` (et `POST /api/sbml/analyze`, et le bouton « Analyser la compatibilité ») : rapport « simulable » ou « non simulable », avec la liste des éléments bloquants. Sont détectés : règles d'affectation, de taux et algébriques, événements, définitions de fonctions, affectations initiales, contraintes, `stoichiometryMath`, `piecewise`, `delay`, réactions rapides, facteurs de conversion, **paquets SBML** (`fbc`, `comp`… sur les éléments comme sur les attributs). Les paquets graphiques `layout` et `render` sont ignorés avec un avertissement. La simulation est refusée si un élément est bloquant. |
| Unités | Les `unitDefinition` sont converties dans le système d'unités de la v5.1 (kind, exposant, échelle, multiplicateur). **Les lois cinétiques sont contrôlées dimensionnellement** : chacune doit avoir la dimension étendue/temps. Résultat par réaction : `consistent`, `inconsistent` (avec la dimension trouvée et celle attendue) ou `unchecked` (unité non déclarée). |
| Paramètres | Les paramètres globaux (`listOfParameters` du modèle) sont séparés des paramètres locaux. **Avant, les paramètres locaux étaient mélangés aux globaux** et pouvaient être « surchargés » par erreur. |
| Conditions initiales | En SBML niveau 3, une taille de compartiment ou une valeur initiale absente est **refusée** : ce niveau n'a pas de valeur par défaut, alors que l'ancien moteur prenait 1 ou 0 en silence. Au niveau 2, la valeur par défaut est appliquée avec un avertissement. |
| Fichier source et provenance | Le fichier est conservé tel quel, son empreinte SHA-256 est revérifiée à chaque lecture, et une modification est détectée. La provenance (fichier, empreinte, source, licence, date d'import) figure dans l'analyse et dans chaque simulation. |
| Intégrateurs | `rk4` (inchangé par défaut), `dopri5` et `implicit_euler` (v5.2). |
| Tests | Modèles valides comparés à leurs **solutions analytiques** (premier ordre avec les 3 méthodes, second ordre), 12 fonctionnalités non prises en charge, valeurs manquantes, unités incohérentes ou non déclarées, paramètres locaux, falsification du fichier, refus des entités XML. |

## Autre défaut corrigé (trouvé par le test navigateur)
Après l'import d'un modèle SBML, la liste des modèles à simuler n'était pas rafraîchie : il fallait recharger la page.

## Tests
`tests/test_v56_sbml.py` (22 tests) et un test navigateur. Les tests navigateur isolent maintenant aussi la bibliothèque de fichiers importés. Moteur SBML 2.0.

## Limites
- Il s'agit d'un **sous-ensemble** de SBML : réseaux de réactions à compartiments fixes, sans règles ni événements ni fonctions.
- Pas de validation contre la suite de tests officielle de SBML (non disponible ici). Elle pourra servir de benchmark en v5.9 si elle devient accessible.
- Le contrôle d'unités ne porte que sur les lois cinétiques. Les nombres sans unité déclarée rendent le contrôle « non vérifié ».
