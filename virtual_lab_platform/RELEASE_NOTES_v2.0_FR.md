# Virtual Lab Platform v2.0 — notes de version

## Nouveauté majeure : laboratoire de circuits électriques CC

- Nouveau panneau de laboratoire électrique, intégré à l'interface locale, en français et en anglais.
- Préréglages de réseaux de résistances en série et en parallèle, et édition de connexions arbitraires entre nœuds nommés.
- Solveur d'analyse nodale pour réseau résistif linéaire en régime continu avec source idéale.
- Affiche les tensions de nœuds, tension/courant/puissance de chaque résistance, courant fourni par la source, résistance équivalente et bilan de puissance.
- Contrôles numériques : résidu KCL aux nœuds internes et conservation de puissance.
- Export JSON du circuit et de ses résultats.
- Validation des entrées, détection des circuits flottants/singuliers et résistance non positive.

## Limites importantes

Ce moteur n'est pas un remplacement de SPICE. Il ne simule pas encore le régime alternatif, les transitoires, les condensateurs, inductances, diodes, transistors, bruit, tolérances, échauffement ni non-linéarités. Le modèle de la source est idéal et les fils sont sans résistance. Les valeurs sont des prédictions du modèle, pas des mesures de matériel réel. Pour les montages réels, une vérification indépendante et les règles de sécurité électrique restent nécessaires.

## Tests

- 92 tests automatisés réussis (incluant cinq tests du solveur électrique).
- Compilation Python réussie.
- Vérification syntaxique JavaScript réussie.
- Test API local du solveur CC réussi.

Ces tests vérifient l'implémentation logicielle et des cas mathématiques ciblés ; ils ne constituent pas une validation indépendante de toute la plateforme.

## Périmètre de la version

La plateforme reste un prototype de laboratoire numérique multidisciplinaire. La nouvelle simulation électrique couvre les réseaux résistifs CC, pas l'ensemble de l'électrotechnique. Les autres catégories scientifiques doivent continuer à être reliées à des moteurs spécialisés et validées avec des références pertinentes. L'assistant actuel est local et déterministe, pas une IA générative capable de résoudre toute question scientifique.
