# Démarrage rapide — v3.1

1. Décompressez l'archive.
2. Lancez `launch_windows.bat` sur Windows ou `python3 app.py` sur macOS/Linux.
3. Ouvrez l'adresse locale affichée dans le terminal.
4. Ouvrez le laboratoire et faites défiler jusqu'au « Simulateur de cinétique chimique ».
5. Entrez A₀, B₀, k, la durée, dt et la température.
6. Pour simuler une réaction en deux étapes, cochez « Activer la réaction B → C », puis définissez C₀ et k₂.
7. Cliquez sur « Exécuter la simulation ». Les courbes et le tableau suivent automatiquement les espèces actives.
8. Exportez le résultat en JSON si nécessaire.

Si le calcul échoue avec une concentration négative, réduisez le pas dt. Utilisez des unités cohérentes et ne considérez pas les résultats comme des prédictions expérimentales sans paramètres validés.
