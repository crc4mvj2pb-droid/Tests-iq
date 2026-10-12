# Notes de version — Virtual Lab Platform v8.4

**Objectif (feuille de route) :**
- comparer hypothèses et résultats, et afficher incertitudes et sensibilité ;
- séparer le résultat calculé, l'interprétation du modèle et l'explication générée ;
- identifier les données manquantes et les limites qui empêchent de conclure.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Hypothèses contre résultats | `critical_analysis.evaluate_hypotheses` applique des règles explicites, testées dans 7 cas. H1 si S ≥ 0,05 et une sortie croissante sur tout le balayage. H2 si S ≤ −0,05 et une sortie décroissante. H0 si \|S\| < 0,05. Sinon « non concluant » : par exemple une sensibilité locale positive avec une courbe non monotone, ou une sensibilité non calculable. Résultats obtenus : H1 pour la résistance et la constante de temps (S = 1), H1 pour la température et la constante de vitesse (S = 16,1), **H0 pour la puissance et la constante de temps** (S = 0). |
| Incertitudes et sensibilité | L'incertitude numérique est évaluée par la convergence de l'extrapolation de Richardson. L'incertitude paramétrique est évaluée sur demande, par Monte Carlo avec graine : pour τ = R·C avec R à ±5 %, l'écart-type obtenu correspond à C·σ_R (test). Faute d'entrée, il est écrit qu'elle n'est pas évaluée. |
| Trois natures séparées | Les **résultats calculés** donnent la valeur, l'unité et la tâche du graphe dont ils viennent. L'**interprétation dans le modèle** applique les règles ci-dessus. L'**explication générée** est préfixée « [Texte généré par règles, à vérifier] ». |
| Ce qui empêche de conclure | La liste est automatique : modèle non validé sur données mesurées, variables contrôlées à des valeurs par défaut illustratives, absence d'incertitude d'entrée. La portée est « modèle seulement », sauf pour un modèle validé sur données, alors limité aux conditions du jeu. Aucune analyse n'est faite sur un plan partiel, arrêté ou annulé. |
| Exposition | `POST /api/research/analyze`. Bouton « Analyse critique » dans le panneau de l'assistant. |

## Tests
- `tests/test_v84_critical_analysis.py` : 12 tests.
- `tests/browser/test_v84_ui.py` : 1 test en navigateur réel.

## Limites
- La sensibilité est locale, autour de la valeur de référence. La monotonie n'est vérifiée qu'aux points balayés.
