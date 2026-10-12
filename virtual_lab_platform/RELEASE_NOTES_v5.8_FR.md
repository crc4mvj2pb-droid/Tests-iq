# Notes de version — Virtual Lab Platform v5.8

**Objectif (feuille de route) :** expériences multi-modèles. Des adaptateurs aux unités explicites relient les modèles. Les variables incompatibles et les écarts d'échelle de temps sont détectés. Chaque résultat intermédiaire et sa provenance sont conservés. Combiner des modèles ne masque jamais leurs limites.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Liaisons à unités explicites | `pipelines.py`. Une liaison `{from, to}` copie une sortie déclarée d'une étape antérieure (ou un champ du résultat, avec son unité obligatoire : `step.result:chemin\|unité`) vers une entrée d'une étape suivante. La conversion passe par `units.convert`. Le test *mmol/L → mol/L* vérifie un facteur 1e-3 exact. Toute cible sans unité déclarée est refusée (pas de transfert non vérifié). |
| Expérience avec au moins 2 moteurs vérifiés | Exemple « Température → Arrhenius → cinétique → absorbance ». Il est comparé à la composition analytique B(t) = A₀(1 − e^(−k(T)t)), avec k = A·exp(−Ea/RT) et A = ε·l·c. L'écart relatif est inférieur à 1e-9 (RK4, pas de 1 s). |
| Variables incompatibles détectées | Les cas suivants sont refusés avec un code stable : dimensions différentes (`incompatible_variables` : 1/s vers mol/L) ; **constante d'un ordre 1 envoyée vers une réaction d'ordre 2** (unité attendue (mol/L)⁻¹/s, dérivée de l'ordre de la réaction) ; étape inconnue ou postérieure ; sortie inexistante ; indice invalide ; cible sans unité ; unité de source absente (`invalid_binding`). Les erreurs de contrat d'une étape sont propagées avec leur code (`out_of_range`…). |
| Écart d'échelle de temps détecté | Un adaptateur stationnaire publie son temps caractéristique (τ = R_th·C_th pour l'échauffement). Si τ dépasse 10 % de la durée **indiquée** d'une étape dynamique qui en dépend (par les liaisons, même indirectement), un avertissement `timescale_mismatch` est émis. Le test : τ = 20 s ne déclenche rien pour une durée de 600 s, mais déclenche l'avertissement pour 100 s. Une absorbance supérieure à 2 est aussi signalée (`absorbance_out_of_linear_range`). |
| Résultats intermédiaires et provenance | Pour chaque étape, la trace conserve : entrées normalisées (valeurs liées incluses), conversions (valeur, unité source, valeur convertie, unité cible), sorties avec unités, hypothèses, avertissements, provenance (moteur, version, date) et maturité. La spécification d'entrée n'est pas modifiée. |
| Maturité = étape la plus faible | La chaîne « Circuit CC → échauffement → Arrhenius → cinétique » est **calculable**, l'étape limitante étant `heating` : l'adaptateur d'échauffement n'est pas encore vérifié contre une référence indépendante (prévu en v7.1). L'autre chaîne est vérifiée. Le niveau « vérifié » de l'adaptateur Beer–Lambert cite un test existant, ce qui est contrôlé. |
| Sauvegarde et rejeu | `experiment_service.run_pipeline` produit un dossier schéma 2 (`model_id = multi_model_pipeline`), dont l'intégrité est vérifiée au niveau `full`. Le rejeu compare chaque sortie de chaque étape, les sorties rapportées et la maturité (≥ 10 valeurs, identiques à 1e-9 près). |
| API et interface | `GET /api/pipelines/examples` (exemples et adaptateurs), `POST /api/pipelines/run`. Panneau « Expériences multi-modèles » : choix d'un exemple, spécification JSON modifiable, tableau des étapes (modèle, maturité, conversions, sorties), avertissements, résultats rapportés et refus affiché avec son code. |

## Tests
- `tests/test_v58_pipelines.py` : 23 tests (références analytiques, conversions, 12 refus, échelles de temps, provenance, maturité, sauvegarde, rejeu, API).
- `tests/browser/test_v58_pipeline_ui.py` : 2 tests en navigateur réel.
- L'audit axe-core ne relève aucune violation.

## Limites
- **Pas de propagation d'incertitude dans la chaîne** dans cette version. Les analyses v5.5 restent disponibles modèle par modèle.
- Les étapes s'enchaînent dans un seul sens et chacune s'exécute une seule fois. Il n'y a pas de couplage dynamique (par exemple une température qui varie pendant la cinétique) : la valeur transmise est une valeur unique, d'où l'avertissement d'échelle de temps.
- Deux adaptateurs seulement (échauffement stationnaire, Beer–Lambert). Les autres liens passent par les modèles à contrat existants.
- Résultats simulés : ce ne sont pas des données expérimentales.
