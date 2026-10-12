# Notes de version — Virtual Lab Platform v8.0

**Objectif (feuille de route) :**
- une IA qui appelle les modèles et outils réels par des interfaces contrôlées ;
- les appels, paramètres, sorties, erreurs et sources sont affichés ;
- aucun résultat n'est inventé si un moteur échoue.

## Choix honnête
L'assistant livré est **à règles et déterministe**. Ce n'est pas un modèle de langage, et le code comme l'interface le disent. Aucun modèle de langage n'est disponible ni évaluable dans cet environnement sans réseau ni clé. Un connecteur vers un tel modèle aurait été livré sans évaluation réelle, ce que la feuille de route interdit (v8.6 : « aucune affirmation sans preuves d'évaluation »).

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Appels d'outils réels et contrôlés | `assistant.py`. 6 outils : exécuter un modèle (par son contrat, avec validation et conversion d'unités), décrire un modèle, chercher dans le catalogue, maturité, validations sur données, domaines. La question est analysée par des règles : intentions et extraction des grandeurs avec leurs unités (« R = 2 kΩ » devient `{"value": 2, "unit": "kΩ"}`, la conversion étant laissée au contrat). |
| Tout est tracé | Chaque appel enregistre son identifiant, l'outil, les arguments, l'état, les sorties ou l'erreur, et la durée. **Chaque nombre de la réponse porte l'identifiant de l'appel qui l'a produit** (par exemple `time_constant = 0.006 s [c1]`). `untraced_numbers()` détecte tout nombre absent des sorties d'outils ; un test vérifie qu'une valeur inventée est repérée. |
| Rien d'inventé | Si un outil refuse (par exemple R = −5 Ω), le statut est `tool_failed` et **aucune valeur** n'est donnée. Si une donnée manque (pH sans concentration), le statut est `clarification_needed`, avec la liste des grandeurs manquantes. Une question médicale, financière ou de prévision est classée `out_of_scope`. Une question sans outil correspondant est classée `unknown`. Dans ces quatre cas, aucune valeur. |
| Sources et statut | Les données sourcées utilisées sont citées : pKa du catalogue, signalé comme valeur approchée. La maturité du modèle et la mention « résultat simulé, pas une mesure » accompagnent chaque calcul. Les grandeurs de la question non utilisées sont signalées. |
| Exposition | `POST /api/assistant/ask`, qui renvoie aussi les nombres non traçables. Panneau « Assistant scientifique » : statut, énoncés typés et tableau des appels d'outils. L'ancien « copilote » (v3.x) reste disponible sans changement. |

## Tests
- `tests/test_v80_assistant.py` : 11 tests.
- `tests/browser/test_v80_assistant_ui.py` : 1 test en navigateur réel.

## Limites
- La compréhension repose sur des mots-clés et des motifs. Des formulations inhabituelles donnent « inconnu » plutôt qu'une réponse fausse. Le taux réel sera mesuré par le jeu d'évaluation de la v8.6.
- Une grandeur est affectée au premier paramètre de même dimension. Si un modèle a deux paramètres de même dimension, une ambiguïté est possible ; elle reste visible dans « Entrées utilisées ».
