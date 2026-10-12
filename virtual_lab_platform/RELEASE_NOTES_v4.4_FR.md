# Notes de version — Virtual Lab Platform v4.4

**Objectif de la version :** sécuriser le seul périmètre annoncé comme calculable, le circuit continu résistif. Aucun résultat numérique ne doit être trompeur, et les erreurs de topologie doivent être expliquées.

## Diagnostic de topologie (avant tout calcul)
- **Sous-réseau flottant** (relié ni à la source ni à la masse) : calcul refusé, avec les composants nommés (`floating_network`). Avant, le message était générique (« matrice singulière »).
- **Branches sans courant** : les résistances qui ne sont pas sur une boucle passant par la source sont signalées (`dead_end_branch`). Critère de théorie des graphes : elles n'appartiennent pas au même bloc biconnexe que la source (algorithme de Tarjan). Cela couvre aussi les groupes de résistances suspendus à un seul nœud.
- **Composants ignorés** : les composants électriques non câblés et non calculés sont listés (`ignored_components`) et affichés.
- Déjà en place depuis v4.2–v4.3 et testés : source court-circuitée, résistance shuntée, borne non câblée, nombre de sources ou de masses, composant non pris en charge câblé, valeurs invalides.

## Calcul numérique
- **Seuil de singularité relatif** (1e-13 × la plus grande conductance) au lieu d'un seuil absolu. Deux résistances de 1e15 Ω en série, valeur acceptée par le validateur, étaient refusées à tort comme « singulières ». Elles sont maintenant calculées (4,5 V).
- **Raffinement itératif en précision mixte** : factorisation LU en virgule flottante, système et résidus calculés exactement en rationnels. La solution converge vers la solution exacte arrondie tant que le conditionnement reste très inférieur à 1/ε.
- **Incertitude publiée** : `node_voltage_uncertainty_v` par nœud (estimation a posteriori, au moins K·ε·|V| avec K = 16), et `current_rounding_uncertainty_a` par branche.
- **Contrôles** : loi des nœuds à chaque nœud interne, retour du courant de source par la masse (`source_loop_residual_a`) et bilan de puissance. Chacun est comparé à la borne d'incertitude propagée et non plus à une tolérance fixe.
- **Avertissement de précision** (`numerical_precision`) quand un courant affiché n'est pas fiable à 5 chiffres significatifs. Exemple : 1 mΩ en série avec 1 TΩ, où le courant de la petite branche est la différence de deux nombres presque égaux. Les tensions restent fiables.
- **Conventions de signe explicites** dans le résultat (`conventions`) et dans l'interface.

## Validation indépendante
- Formules analytiques : série, parallèle, diviseur, **pont de Wheatstone** (formule de Thévenin, 3 jeux de valeurs), **échelle R-2R** (1, 3 et 6 étages).
- **Solveur exact en rationnels** écrit séparément dans les tests (`fractions.Fraction`). Il ne partage aucun code avec `electrical_circuits.py`.
- 12 réseaux aléatoires comparés à 1e-9 près.
- **300 réseaux aléatoires mal conditionnés** (résistances de 1 Ω à 1 GΩ) : l'erreur réelle de chaque tension de nœud et de chaque courant **ne dépasse jamais l'incertitude annoncée**.
- Réseau de taille maximale (≈ 200 résistances, 122 nœuds) résolu en moins de 10 s. Observé ici : 0,02 s.
- Tests navigateur : sous-réseau flottant nommé et non enregistré ; composant ignoré et conventions affichés.

## Limites
- **ngspice n'était pas installé dans cet environnement : la comparaison avec un solveur externe n'a pas été faite.** Elle reste optionnelle.
- K = 16 est un facteur de sécurité heuristique. L'estimation d'erreur est a posteriori, ce n'est pas une borne prouvée. Sur les 300 cas testés, elle a toujours majoré l'erreur réelle.
- Un courant exactement nul peut être affiché comme une très petite valeur, de l'ordre de l'incertitude publiée.
- Le solveur reste limité à une source idéale CC, une masse, des fils idéaux et des résistances linéaires. Ce n'est pas SPICE.
