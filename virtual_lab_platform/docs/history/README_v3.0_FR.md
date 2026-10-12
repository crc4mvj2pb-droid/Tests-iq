# Virtual Lab Platform v3.0 — notes de version

## Nouveauté principale

Le moteur de cinétique chimique introduit en v2.8 est maintenant accessible depuis l’interface graphique. Le panneau « Simulateur de cinétique chimique » permet de régler les concentrations initiales de A et B, la constante cinétique, la durée, le pas d’intégration, la température, l’énergie d’activation et la température de référence.

Après exécution, l’interface affiche les concentrations finales, une courbe SVG des concentrations en fonction du temps, un tableau de valeurs échantillonnées et les hypothèses/limites du modèle. Les résultats peuvent être exportés en JSON. L’API locale `/api/chemistry/kinetics` reste disponible.

## Modèle et limites

Le moteur emploie la loi d’action de masse et une intégration RK4 à pas fixe. Le modèle d’exemple est A → B, premier ordre. Le paramètre `rate_constant` est interprété à `reference_temperature_k`; la dépendance en température suit Arrhenius si une énergie d’activation non nulle est fournie. Les unités doivent être cohérentes. Le modèle ne remplace pas les données cinétiques mesurées, ne calcule pas automatiquement les constantes de vitesse et ne simule ni mécanismes détaillés, ni équilibre, ni transfert de chaleur.

## Démarrage

- Windows : lancer `launch_windows.bat`.
- macOS/Linux : exécuter `./launch_macos_linux.sh` dans le dossier du projet.
- Ouvrir l’adresse locale indiquée par le lanceur.
- Dans l’espace de travail, faire défiler jusqu’au panneau « Simulateur de cinétique chimique ».

## Validation

Les tests automatisés couvrent le moteur cinétique, les modèles existants, l’API et la syntaxe de l’interface. Les résultats exacts sont consignés dans `TEST_RESULTS_v3.0.txt`. Une réussite des tests logiciels ne constitue pas une validation expérimentale indépendante.
