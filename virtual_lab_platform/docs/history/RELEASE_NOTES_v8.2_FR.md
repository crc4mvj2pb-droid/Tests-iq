# Notes de version — Virtual Lab Platform v8.2

**Objectif (feuille de route) :**
- proposer le matériel virtuel, les paramètres, les contrôles et les répétitions ;
- vérifier que chaque étape est compatible avec les moteurs disponibles ;
- signaler les hypothèses et les éléments non simulés.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Paramètres | `protocol_design.design` part d'une question formulée (v8.1). Il propose un balayage de la variable indépendante : logarithmique de ref/2 à 2·ref (rapport constant vérifié), ou linéaire si la référence est nulle ou négative, **toujours borné par le contrat** (test près de la borne de 1 K). |
| Contrôles | Deux essais témoins : un essai à la valeur de référence, et son **double**, qui doit lui être identique (contrôle du déterminisme). |
| Répétitions justifiées | Une seule répétition par point pour un moteur déterministe, avec la raison. Cinq lectures si un instrument simulé ajoute un bruit avec graine. L'instrument doit mesurer une grandeur compatible avec la sortie : sinon, refus avec la liste des instruments compatibles. |
| Compatibilité avec les moteurs | **Chaque essai prévu est validé par le contrat avant toute exécution.** Les valeurs refusées sont listées avec leur raison. Un test valide à nouveau chaque essai contre le contrat. |
| Matériel virtuel | Les instruments du catalogue dont l'unité correspond à la sortie observée sont proposés. Aucun n'est proposé si aucune unité ne correspond (par exemple une constante de temps). |
| Éléments non simulés | Sont toujours listés : les erreurs de mesure réelles, la préparation des échantillons, les réglages et les effets d'opérateur, et les conditions hors des hypothèses du modèle (reprises du contrat). |
| Exposition | `POST /api/research/design`. Bouton « Concevoir le protocole » dans le panneau de l'assistant. |

## Tests
- `tests/test_v82_protocol_design.py` : 6 tests.
- `tests/browser/test_v82_ui.py` : 1 test en navigateur réel.

## Limites
- Ce sont des protocoles **de simulation** : ils planifient des essais sur les modèles, pas une expérience de laboratoire réelle.
