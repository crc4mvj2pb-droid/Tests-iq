# Notes de version — Virtual Lab Platform v5.2

**Objectif (feuille de route) :** définir les tolérances, les critères d'arrêt et la gestion des erreurs numériques ; distinguer l'erreur du solveur, l'incertitude des paramètres et l'incertitude de mesure ; tester la stabilité, la convergence et les cas limites ; donner un diagnostic clair en cas de non-convergence.

## Critères d'acceptation et résultat
| Critère | Résultat |
|---|---|
| Tolérances et critères d'arrêt explicites | `numerics.Tolerances` : `rtol` (1e-14 à 1e-2), `atol`, budget de pas, pas minimal relatif. Valeurs hors bornes refusées (`invalid_tolerance`). |
| Erreurs typées et diagnostics | `NumericalError` avec les codes `max_steps_exceeded`, `step_size_underflow`, `non_convergence` (Newton) et `non_finite`. Les diagnostics accompagnent l'erreur : pas acceptés et rejetés, évaluations, itérations de Newton, pas minimal et maximal. **Aucun résultat partiel n'est renvoyé comme s'il était valide.** |
| Intégrateurs adaptatifs | `dopri5` : Dormand–Prince 5(4), estimation d'erreur intégrée, pour les systèmes non raides. `implicit_euler` : Euler implicite avec Newton et **extrapolation de Richardson** (ordre 2, L-stable), pour les systèmes **raides**. |
| Cinétique | Paramètre `method` (`rk4` par défaut, inchangé ; `dopri5` ; `implicit_euler`), avec `rtol`, `atol` et `max_steps`. Méthode et diagnostics renvoyés, affichés dans l'interface et enregistrés dans les dossiers. Moteur 2.2. |
| Types d'incertitude séparés | `uncertainty_breakdown` : `numerical` (estimée par la méthode), `parameter` (évaluée en v5.5) et `measurement` (mesures simulées seulement). |
| Convergence | Ordre observé de RK4 : entre 3,8 et 4,2 (attendu 4). Pour les méthodes adaptatives, l'erreur ne croît pas quand la tolérance est resserrée, et elle décroît globalement. Oscillateur harmonique sur 10 périodes : erreur < 1e-7. |
| Problème raide de référence | **Problème de Robertson** (Hairer & Wanner, 1996) jusqu'à t = 40 : la méthode implicite reproduit les valeurs publiées à 0,2 % près, et l'invariant A + B + C reste à 1 à 1e-8 près. Les méthodes explicites **refusent** ce problème avec un message qui conseille la méthode implicite, au lieu de produire un faux résultat. |
| Cas limites | Explosion de la solution (y' = y², singularité en t = 1) signalée ; budget de pas épuisé signalé ; constante de vitesse nulle ; sortie à l'instant initial. |

## Défauts trouvés et corrigés pendant cette version
- **L'estimation d'erreur pouvait valoir 0** quand les instants de sortie imposaient les pas : les deux résolutions faisaient alors exactement les mêmes pas. L'estimation retient maintenant aussi les erreurs locales accumulées (dopri5) ou un plancher d'arrondi (méthode implicite). Elle n'est plus nulle quand une erreur existe.
- Euler implicite d'ordre 1 : l'erreur globale accumulée dépassait 100 × la tolérance. L'extrapolation de Richardson corrige cela.
- **Oubli de la v5.1** : `concentration_unit` n'était pas enregistré dans la configuration d'une cinétique, donc un rejeu aurait affiché la mauvaise unité. Corrigé, avec un test de rejeu qui vérifie la méthode et l'unité.
- Contrats : nouvelle propriété `unit_from` (la tolérance absolue est exprimée dans l'unité de concentration choisie).

## Tests
`tests/test_v52_numerics.py` (13 tests) et un test navigateur (choix de l'intégrateur).

## Limites
- Les estimations d'erreur globale sont **a posteriori**. Ce ne sont pas des bornes garanties.
- Le jacobien de la méthode implicite est calculé par différences finies : son coût croît avec le carré du nombre d'espèces (20 au maximum).
- Le solveur de circuits est direct (raffinement itératif, v4.4) et n'a pas besoin de ces intégrateurs.
