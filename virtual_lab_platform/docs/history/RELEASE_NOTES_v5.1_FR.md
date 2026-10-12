# Notes de version — Virtual Lab Platform v5.1

**Objectif (feuille de route) :** un traitement systématique des unités et des conversions, la détection des dimensions incompatibles plutôt qu'une conversion silencieuse, des constantes versionnées avec leur source et leur date, et des tests dimensionnels des équations principales.

## Critères d'acceptation et résultat
| Critère | Résultat |
|---|---|
| Système d'unités réel | `units.py` : dimensions sur les 7 grandeurs de base du SI, préfixes (de a à Y), expressions composées (`J/(mol·K)`, `m^2/s`, `L·mol⁻¹·cm⁻¹`, `mol L-1`), températures affines (°C), unités usuelles (min, h, d, atm, bar, eV, M). |
| Dimensions incompatibles refusées | Conversion refusée avec le code `incompatible_dimensions`. Les unités arbitraires `a.u.` ne se convertissent qu'en elles-mêmes. °C est refusé à l'intérieur d'une expression composée (`affine_in_expression`). |
| Unités des contrats | Toutes les unités déclarées par les 17 contrats sont comprises par le système (test). |
| Entrées avec unités | `POST /api/models/{id}/run` accepte `{"value": 1, "unit": "kΩ"}`. La valeur est convertie dans l'unité du contrat, ou refusée si la dimension diffère ou si l'unité est inconnue. |
| Constantes versionnées | `scientific_library/physical_constants.json` (schéma 2.0, « SI-2019+CODATA-2018 ») : source, date de référence, statut exact ou mesuré, incertitude relative. `constants.py` les expose. **Les moteurs lisent R depuis cette source unique**, au lieu de deux valeurs codées en dur. La constante de Faraday « approximative » est remplacée par sa valeur exacte (N_A·e). La permittivité du vide est ajoutée comme exemple de constante mesurée, avec son incertitude. |
| Tests dimensionnels | 18 équations utilisées par les moteurs, chacune vérifiée côté gauche contre côté droit : τ = RC, τ = L/R, loi d'Ohm, P = VI, réactances, KCL, lois de vitesse d'ordre 1 et 2, exposant d'Arrhenius, Beer–Lambert, nombre de Fourier, R·I du neurone, gaz parfait, Faraday, SIR, flux thermique. |
| Cinétique | Nouveau paramètre `concentration_unit` (dimension quantité/volume ou `a.u.`, vérifiée). **L'unité de chaque constante de vitesse est déduite de l'ordre de la réaction** (`rate_constant_units`) et contrôlée dimensionnellement. Moteur 2.1. |
| Mesures reliées | Les conversions passent par le module d'unités, au lieu de la table fixe de la v4.7. |

## Tests
`tests/test_v51_units.py` : 56 tests. Tous les tests précédents passent.

## Limites
- Les températures en °C sont traitées comme des températures absolues décalées. **Les différences de température** ne sont pas distinguées : 10 °C d'écart = 10 K, mais la conversion de « 10 °C » donne 283,15 K. Une telle grandeur doit être exprimée en K.
- Les moteurs anciens qui travaillent en unités arbitraires (`a.u.`) restent sans dimension physique. C'est le cas de plusieurs modèles du catalogue.
- Pas de parcours dans l'interface spécifique à cette version (API et moteurs).
