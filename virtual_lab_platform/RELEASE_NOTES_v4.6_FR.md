# Notes de version — Virtual Lab Platform v4.6

**Objectif de la version :** réussir un parcours chimique complet : saisie d'une réaction, calcul, résultat, enregistrement, historique, vérification et rejeu.

## Parcours complet
- Nouveaux endpoints `POST /api/chemistry/stoichiometry-run` et `POST /api/chemistry/kinetics-run`. Ils calculent puis enregistrent un dossier schéma 2 (v4.5), qui est vérifiable au niveau `full`. Les endpoints sans enregistrement restent disponibles.
- Les panneaux « Réaction » et « Cinétique » de l'interface utilisent ces endpoints. Ils affichent le numéro de dossier et l'empreinte, puis rafraîchissent l'historique.
- **Rejeu** des deux modèles depuis l'historique, avec comparaison valeur par valeur : avancement, réactif limitant, quantités, et concentrations à chaque instant échantillonné.

## Validation scientifique
- **Estimation de l'erreur d'intégration RK4** par doublement du pas (dt contre dt/2, facteur de Richardson 16/15), publiée dans `summary.estimated_final_error`. **Un avertissement apparaît quand l'erreur dépasse la précision affichée** (6 chiffres significatifs).
- Le cas relevé par l'audit v4.1 (k·dt = 1,5 : erreur de −18 % sans avertissement) est maintenant signalé.
- Testé contre la solution analytique du premier ordre pour 5 couples (k, dt) : l'estimation reste dans un facteur 2 de l'erreur réelle.
- Identifiants de réaction en double : refusés. Avant, `final_rates` en perdait un.
- **Réaction non équilibrée** (formules fournies) : refusée par défaut. Elle n'est simulée qu'avec `allow_unbalanced: true`, et elle est alors signalée (`unbalanced_reaction`).
- Formules absentes : avertissement `atom_balance_not_checked`.
- Stœchiométrie : **les symboles d'éléments sont vérifiés** contre les 118 éléments. `Xy` était accepté avant.
- Versions des moteurs : `mass_action_rk4` 2.0 et `stoichiometric_batch_balance` 1.1.

## Test ancien modifié (aucun supprimé)
- `test_chemical_kinetics.py::test_flags_unbalanced_atom_stoichiometry` attendait qu'une réaction non équilibrée soit simulée. Il vérifie maintenant le refus par défaut, puis la simulation signalée avec `allow_unbalanced`. Ce changement de comportement est voulu.

## Limites
- RK4 à pas fixe. L'estimation d'erreur est asymptotique : ce n'est pas une borne garantie. Elle n'est pas calculée au-delà d'un budget de calcul, et un avertissement le dit.
- Il n'y a toujours pas de pas adaptatif ni de solveur pour les systèmes raides. C'est prévu en v5.2.
- Les constantes de vitesse sont fournies par l'utilisateur. Le résultat est un calcul, pas une mesure.
- La stœchiométrie vérifie le bilan atomique, pas la plausibilité chimique ni la sécurité d'une réaction.
- `test_v35_kinetics_bridge.py` et `test_v36_stoichiometry.py` cherchaient les appels `fetch('/api/chemistry/kinetics'` et `fetch('/api/chemistry/stoichiometry'`. Les panneaux appellent maintenant les endpoints `-run`, et ces tests vérifient ces nouveaux appels. Le comportement est testé dans le navigateur (`tests/browser/test_v46_chemistry_path.py`).

## Note de traçabilité
Le premier commit v4.6 a été publié alors que la matrice générée signalait 2 échecs : ce sont les deux tests ci-dessus. Ma chaîne de commandes ne s'arrêtait pas sur l'échec. Un commit correctif a suivi, avec la matrice régénérée sans échec.
