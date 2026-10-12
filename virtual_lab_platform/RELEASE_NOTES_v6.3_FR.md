# Notes de version — Virtual Lab Platform v6.3

**Objectif (feuille de route) :**
- régression avec hypothèses, métriques, résidus et diagnostics ;
- données d'ajustement et de validation tenues séparées ;
- limites de l'extrapolation affichées.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Ajustement correct, contrôlé sur des références publiées | `fitting.py` : moindres carrés non linéaires (Levenberg–Marquardt) sur 7 formes de modèle (Michaelis–Menten, montée du premier ordre, décroissance exponentielle, linéaire, logistique, Arrhenius, loi de puissance). **Puromycine (cellules traitées) : Vm = 212,68 ± 6,947 et K = 0,06412 ± 0,008281, erreur résiduelle 10,93 sur 10 degrés de liberté, soit exactement les valeurs de Bates & Watts (1988).** DBO : A = 19,143 ± 2,496 et erreur résiduelle 2,549, comme publié. Sur des données sans bruit, les 7 formes retrouvent leurs paramètres (écart relatif < 1e-6). |
| Incertitudes et diagnostics | Erreurs types et IC 95 % (approximation linéaire s²(JᵀJ)⁻¹, quantile de Student calculé sans bibliothèque externe et contrôlé contre les tables). La **couverture des IC est vérifiée** : 400 simulations, couverture entre 92 et 98 %. Sont aussi fournis : matrice de corrélation (avertissement si \|r\| > 0,95), résidus bruts et standardisés, R², RMSE, AIC, statistique de Durbin–Watson et test des suites. **Une forme de modèle fausse se voit** : une droite ajustée sur une exponentielle donne DW < 1 et z < −2. |
| Unités | Les unités des paramètres sont déduites de celles des données (Vm en counts/min/min, K en ppm, k en 1/d). Arrhenius exige une température compatible avec le kelvin. |
| Ajustement et validation séparés | Trois méthodes : indices explicites, « un point sur deux » (par exemple le second réplicat) ou fraction tenue à l'écart avec une graine. **Un test montre que modifier un point de validation ne change pas les estimations.** On obtient RMSE et biais de validation, ainsi que le rapport à l'erreur résiduelle. |
| Extrapolation | `predict` signale toute prédiction hors de la plage ajustée. Les points de validation hors plage sont comptés. La plage est affichée avec le résultat. |
| Traçabilité | `POST /api/data/fit` ajuste un jeu du catalogue (colonnes x et y, filtre facultatif, exclusion explicite des valeurs manquantes) et enregistre un dossier `model_fit` avec l'identifiant, la version, la nature et **l'empreinte du jeu de données**. Le rejeu est refusé si le jeu a changé (`dataset_changed`) ; sinon il reproduit les estimations à 1e-9. |
| Interface | Panneau « Ajustement de modèles aux données » : estimations avec erreurs types et IC, graphique des résidus standardisés (lignes ±2), diagnostics, validation et plage ajustée. |
| Maturité | Le moteur d'ajustement (`model_fit`) est « vérifié » par des références publiées et une propriété statistique, preuves à l'appui dans la matrice. |

## Tests
- `tests/test_v63_fitting.py` : 25 tests.
- `tests/browser/test_v63_fit_ui.py` : 2 tests en navigateur réel.

## Limites
- Moindres carrés non pondérés : erreurs supposées indépendantes, de variance constante. Les intervalles de l'approximation linéaire peuvent être inexacts pour des paramètres très non linéaires ou de petits échantillons (par exemple k de la DBO, 6 points).
- Une optimisation locale part d'une valeur initiale heuristique documentée. Le résultat peut dépendre du point de départ, qui peut être fourni (`start`).
- Un bon ajustement ne prouve pas le mécanisme. La validation d'un modèle sur données (niveau « validé sur données ») est traitée en v7.3, avec un critère fixé a priori.
