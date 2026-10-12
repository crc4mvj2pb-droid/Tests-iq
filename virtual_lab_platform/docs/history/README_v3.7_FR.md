# Virtual Lab Platform v3.7

## Démarrer
- **Windows** : double-cliquer sur `launch_windows.bat` ou exécuter `python app.py` dans ce dossier.
- **macOS/Linux** : exécuter `python3 app.py`.
- Ouvrir ensuite http://127.0.0.1:8765.
- Le serveur est local : ne pas l'exposer directement à Internet.

## Nouveauté v3.7 — instruments virtuels et incertitudes
La section **Instruments virtuels et incertitudes** permet de sélectionner un instrument du catalogue (thermomètre, balance, pH-mètre, spectrophotomètre ou pipette) et de définir :
- la valeur théorique fournie par l’utilisateur ;
- un biais instrumental illustratif ;
- une correction d’offset et un facteur de correction de gain ;
- une incertitude-type d’étalonnage ;
- une résolution d’affichage ;
- une graine aléatoire pour reproduire exactement la même simulation.

L’API `POST /api/instruments/measure` renvoie la lecture brute simulée, la lecture corrigée, la valeur indiquée, un budget d’incertitude, l’incertitude élargie avec `k=2`, l’intervalle correspondant et l’écart par rapport à la théorie. Les unités sont liées au catalogue de l’instrument, et les appareils sans modèle de mesure sont refusés.

### Interprétation scientifique
- Le statut est `simulated_measurement` et `experimental_data` vaut `false` : **ce ne sont pas des données expérimentales**.
- Les incertitudes du catalogue sont des valeurs pédagogiques illustratives, pas des spécifications certifiées par les fabricants.
- Le budget combine quadratiquement les composantes indépendantes (incertitude instrumentale, étalonnage et résolution modélisée par une distribution rectangulaire).
- `k=2` est une approximation d’intervalle élargi, pas une garantie universelle de couverture.
- Le modèle ne simule pas la dérive, l’hystérésis, le temps de réponse, l’environnement ni la traçabilité métrologique. La valeur théorique est fournie par l’utilisateur et n’est pas validée indépendamment.

## Validation
Les tests du projet s’exécutent avec `python -m pytest -q`. Le rapport livré avec cette version est `TEST_RESULTS_v3.7.txt`.
