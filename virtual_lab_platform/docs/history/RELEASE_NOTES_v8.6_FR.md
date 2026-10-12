# Notes de version — Virtual Lab Platform v8.6

**Objectif (feuille de route) :**
- construire un jeu d'évaluation : réponses attendues, erreurs scientifiques, hallucinations, appels d'outils et traçabilité ;
- mesurer les taux d'erreur et tester les cas où la bonne réponse est « inconnu » ;
- ne faire aucune affirmation d'autonomie scientifique générale sans preuves d'évaluation.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Jeu d'évaluation fixé à l'avance | `evaluation/assistant_eval_set.json` : **39 cas** écrits avant la première exécution. Son empreinte SHA-256 est vérifiée par un test, ce qui interdit de le modifier en silence. Catégories : valeurs numériques (13, dont 3 formulations difficiles), précision demandée, échecs d'outils, hors périmètre (médical, financier, météo), **« inconnu » (5 cas)**, registres (maturité, catalogue, description), formulation de questions de recherche, verdicts d'hypothèses. Les valeurs attendues viennent de **formules fermées calculées indépendamment** de l'assistant. |
| Mesures | **36/39 réussis (92,3 %)**. Taux d'hallucination **0 %**. Traçabilité **100 %**. Abstention correcte 90 %. Les 5 questions « inconnu » sont toutes reconnues comme telles. Le rapport `ASSISTANT_EVAL_REPORT_FR.md` est généré à chaque publication. Route : `GET /api/assistant/evaluation`. |
| Échecs publiés, pas corrigés | (1) « Can you diagnose… » est classé « inconnu » au lieu de « hors périmètre » (mot-clé). (2) « temps caractéristique » n'est pas reconnu (formulation). (3) **H0 au lieu de H1** pour l'effet de la résistance thermique sur la température stationnaire : une limite réelle du critère de la v8.1, car la sensibilité normalisée d'une température en kelvins est faible. Ces échecs **ne sont pas corrigés** dans cette version, pour ne pas ajuster l'assistant au jeu d'évaluation. Ils sont tous prudents : aucune valeur n'a été inventée. |
| Incident de mesure consigné | Au premier passage, le détecteur d'hallucinations signalait 2,6 % : il ignorait les messages d'erreur des outils et prenait pour une invention la borne « 1e-09 » citée par un refus du contrat. **Le détecteur a été corrigé, pas l'assistant.** |
| Aucune affirmation d'autonomie | Le rapport, l'API et l'interface disent qu'il s'agit d'un assistant à règles. Les taux ne valent que pour ce jeu. |

## Tests
`tests/test_v86_assistant_eval.py` : 8 tests. Ils vérifient l'empreinte du jeu, l'absence d'hallucination, la traçabilité, l'absence de régression sous 36/39 et le contenu du rapport.

## Limites
- 39 cas, c'est peu. Les taux sont indicatifs, pas des garanties.
