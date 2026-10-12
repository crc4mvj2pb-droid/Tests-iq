# Bilan du grand jalon B — « Moteurs scientifiques robustes et contrats communs » (v5.0 → v5.9)

**Porte de sortie (feuille de route) :** plusieurs moteurs au moins sont validés sur des références indépendantes, les unités et les contrats sont cohérents, et les expériences multi-modèles ne masquent pas les limites de chaque moteur.

| Exigence | Preuve reproductible |
|---|---|
| Plusieurs moteurs vérifiés sur références indépendantes | `BENCHMARK_REPORT_FR.md` (v5.9) : 33 cas sur 15 moteurs ou modules. La matrice de maturité (v5.7) compte 21 modèles vérifiés, et chaque preuve cite un test qui doit réussir dans la validation générée. `KINETICS_VALIDATION_FR.md` (v5.3) donne 7 solutions analytiques × 3 intégrateurs. |
| Contrats cohérents | `contracts.py` et `model_registry.py` (v5.0) : 19 contrats. Paramètres typés avec unités et bornes, sorties avec unités, codes d'erreur stables. Chaque contrat est contrôlé contre son moteur (`tests/test_v50_contracts.py`). |
| Unités cohérentes | `units.py` (v5.1) : 7 dimensions SI et refus des dimensions incompatibles. Les constantes ont une source et une date (`scientific_library/physical_constants.json`). Tests dimensionnels : `tests/test_v51_units.py`. |
| Numérique maîtrisé | `numerics.py` (v5.2) : tolérances, diagnostics, codes de non-convergence ; méthode implicite pour les systèmes raides ; estimation d'erreur. |
| Expériences multi-modèles sans limite masquée | `pipelines.py` (v5.8, 1.1 en v5.9) : liaisons à unités vérifiées et refus des variables incompatibles ; écarts d'échelle de temps et conditions incohérentes signalés ; maturité = étape la plus faible (exemple « calculable » à cause d'un adaptateur non vérifié). |
| Résultats négatifs documentés | Le banc de la v5.9 documente 4 limites ou refus. Le catalogue (v5.7) affiche 33 maquettes et 0 modèle validé sur données. |

**Évaluation :** la porte de sortie est franchie pour le périmètre testé, avec ces réserves explicites :
- aucune validation sur données réelles n'existe encore, seulement des vérifications mathématiques. C'est l'objet du jalon C ;
- aucun logiciel de référence externe (ngspice) n'a pu être utilisé ;
- l'incertitude n'est pas propagée dans les chaînes multi-modèles (prévu en v7.6).

## Chiffres
- Tests : 600 en v4.9, puis **901 en v5.8**. Le total de la v5.9 figure dans `VALIDATION_MATRIX_v5.9.md`. Aucun test n'a été supprimé.
- Défauts réels trouvés pendant le jalon B et corrigés :
  - règles SBML ignorées silencieusement ;
  - paramètres locaux SBML mélangés aux paramètres globaux ;
  - estimation d'erreur nulle de Dormand–Prince ;
  - unité de concentration absente du dossier de cinétique ;
  - réponse CSV réécrite par l'interface ;
  - affirmation erronée sur le catalogue (« 30 » modèles au lieu de 33) ;
  - température par défaut incohérente dans une chaîne multi-modèles.
