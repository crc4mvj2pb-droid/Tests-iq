# Virtual Lab Platform v3.1

## Nouveauté principale
Le panneau de cinétique chimique prend désormais en charge une réaction séquentielle facultative :
- A → B
- puis B → C si l'option correspondante est activée.

Les résultats sont présentés pour toutes les espèces actives : concentrations finales, courbes concentration/temps, tableau échantillonné et export JSON. Les paramètres restent explicitement fournis par l'utilisateur.

## Démarrage
- Windows : lancer `launch_windows.bat` ou exécuter `python app.py`.
- macOS/Linux : depuis ce dossier, exécuter `python3 app.py`.
- Ouvrir ensuite l'adresse locale indiquée par le serveur (par défaut `http://127.0.0.1:8000` si configuré ainsi).

## Limites scientifiques
Le modèle utilise une loi d'action de masse et un intégrateur RK4 à pas fixe. Le modèle est homogène, à volume et température constants. Pour A → B → C, les deux réactions partagent l'énergie d'activation et la température de référence saisies pour la première étape. Ce n'est pas un modèle universel de chimie et les constantes doivent être documentées ou calibrées avant tout usage scientifique réel.

## Vérifications
Les 117 tests de la suite v3.0 passent toujours après les changements d'interface. Voir `TEST_RESULTS_v3.1.txt`. Le test navigateur manuel sur macOS reste à effectuer.
