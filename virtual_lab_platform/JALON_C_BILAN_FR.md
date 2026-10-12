# Bilan du grand jalon C — « Données, provenance et validation scientifique » (v6.0 → v6.5)

**Porte de sortie (feuille de route) :** un tiers peut récupérer un dossier d'expérience et reproduire le calcul dans un environnement documenté.

| Exigence | Preuve reproductible |
|---|---|
| Récupérer un dossier complet | `GET /api/history/{id}/package` (v6.4) : dossier, configuration, données utilisées (fichier importé d'origine compris), dossiers sources, journal, environnement, code embarqué, manifeste SHA-256 et `README_REPRODUCE.md`. Le rapport (v6.5) décrit méthode, paramètres, résultats et sources. |
| Reproduire dans un environnement documenté | `tests/test_v64_traceability.py` extrait le paquet dans un répertoire vide et exécute `python -I reproduce.py` dans un processus séparé, sans accès au dépôt. Résultat : reproduction réussie pour une cinétique, un ajustement sur données publiées, un ajustement sur fichier importé et une lecture d'instrument avec son dossier source. Un paquet altéré est refusé. |
| Données sourcées et séparées par nature | Catalogue v6.0 : 5 natures contrôlées ; jeux publiés de la Puromycine et de la DBO ; verrou de version. Import v6.2 : rapport de qualité, fichier d'origine conservé. |
| Valeurs référencées | v6.1 : bibliographie sans orpheline ; chaque modèle, constante, adaptateur et unité cite sa source ; valeurs par défaut étiquetées « illustratives ». |
| Ajustement contrôlé | v6.3 : les estimations publiées de Bates & Watts sont reproduites ; couverture des IC vérifiée ; validation sur points séparés. |

**Évaluation :** la porte de sortie est franchie pour le périmètre testé (Linux, Python 3.13, reproduction en processus isolé).

Réserves :
- je n'ai pas fait d'essai sur une autre machine ni sur un autre système. Le paquet ne dépend que de la bibliothèque standard, mais **un essai de reproduction sur votre Mac est recommandé** ;
- le manifeste garantit l'intégrité, pas l'authenticité ;
- aucun modèle n'est encore « validé sur données ». La v7.3 fera la première validation, avec un critère fixé a priori.
