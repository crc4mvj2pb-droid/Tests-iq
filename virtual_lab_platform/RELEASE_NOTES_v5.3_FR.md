# Notes de version — Virtual Lab Platform v5.3

**Objectif (feuille de route) :** valider les modèles A→B et A→B→C sur leurs solutions analytiques connues, tester la conservation de la matière, la positivité des concentrations et le pas de temps, comparer plusieurs pas et intégrateurs en mesurant l'erreur, et documenter l'usage de RK4 et ses limites.

## Critères d'acceptation et résultat
| Critère | Résultat |
|---|---|
| Solutions analytiques | 7 cas de référence (`benchmarks/kinetics_analytic.py`, séparés des tests unitaires) : A→B, A→B→C, A→B→C avec k₁ = k₂ (cas dégénéré), 2A→P, A+B→P avec A₀ ≠ B₀, A⇌B, réactions parallèles. Chaque formule est contrôlée à t = 0. |
| Toutes les méthodes | Pour les 7 cas et les 3 méthodes, l'écart maximal sur toute la trajectoire reste sous un seuil fixé : 2e-7 pour RK4 (dt = 0,05 s), 5e-8 pour dopri5 (rtol = 1e-8), 2e-6 pour la méthode implicite (rtol = 1e-6). 21 combinaisons testées. |
| Positivité | Toutes les concentrations échantillonnées restent ≥ 0, pour tous les cas et toutes les méthodes. |
| Conservation | Le moteur publie les totaux par élément (initial, final) et la **dérive relative maximale**. Testé sur N₂O₄ ⇌ 2 NO₂ : dérive < 1e-9 pour les 3 méthodes (observée : environ 1e-15 avec RK4). Rien n'est publié sans formules atomiques. |
| Comparaison des pas et intégrateurs | **`KINETICS_VALIDATION_FR.md`**, généré par `python scripts/kinetics_validation.py` : erreur maximale et erreur finale pour 4 pas RK4 et 3 tolérances par méthode adaptative, ordre observé, erreur estimée par le moteur. |
| Usage et limites de RK4 | Section dédiée dans le rapport. L'ordre observé est compris entre 3,97 et 4,12 sur les 7 cas. |

## Ce que montre le rapport (résultats, y compris défavorables)
- **RK4** : l'erreur finale estimée par le moteur (doublement du pas) coïncide presque exactement avec l'erreur réelle.
- **Euler implicite extrapolé** : l'estimation est proche, mais légèrement **inférieure** à l'erreur réelle (environ 0,9×).
- **dopri5** : l'estimation est **très prudente**, de 300 à 1 000 fois l'erreur réelle.
- **L'estimation porte sur l'instant final seulement.** L'erreur maximale sur la trajectoire peut être jusqu'à 100 fois plus grande, par exemple pour A→B→C avec RK4.

## Tests
`tests/test_v53_kinetics_validation.py` : 47 tests. Moteur de cinétique 2.3.

## Limites
- Les cas analytiques sont des systèmes simples. Les réseaux complexes n'ont pas de solution exacte : seule la comparaison entre méthodes (et Robertson pour un cas raide) les couvre.
- Aucune comparaison avec des données expérimentales : c'est une **vérification** du calcul, pas une validation sur données.
