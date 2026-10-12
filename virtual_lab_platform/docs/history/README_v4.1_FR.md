# Virtual Lab Platform v4.1

La v4.1 renforce la reproductibilité du cycle d'expérience électrique introduit en v4.0.

## Nouveautés
- Endpoint `GET /api/history/{id}/verify` pour vérifier que la configuration sauvegardée correspond à son empreinte SHA-256.
- Endpoint `POST /api/history/{id}/replay` pour relancer un circuit CC sauvegardé, après vérification de l'empreinte.
- Le rejeu crée un nouveau dossier d'expérience et inclut `replay_of` avec l'identifiant de l'expérience d'origine.
- Contrôles « Verify integrity » et « Replay circuit » dans l'historique de l'interface.
- Sérialisation canonique de la configuration centralisée dans `experiment_lifecycle.py`, avec rejet des valeurs JSON non finies.

## Lancer
Voir [DEMARRAGE_RAPIDE_v4.1_FR.md](DEMARRAGE_RAPIDE_v4.1_FR.md). Exécution locale : `python app.py`, puis `http://127.0.0.1:8765`.

## Tests
Voir [TEST_RESULTS_v4.1.txt](TEST_RESULTS_v4.1.txt). La suite automatisée couvre l'API de rejeu, l'historique SQLite, la stabilité de l'empreinte, la détection d'une configuration modifiée et les contrôles visibles dans l'interface.

## Limites
- La vérification porte sur l'empreinte de la configuration enregistrée, pas sur un hachage cryptographique de tout le dossier.
- Le rejeu est actuellement limité aux circuits CC résistifs de la paillasse.
- Les résultats sont des calculs simulés, pas des mesures expérimentales.
- Le solveur ne remplace pas SPICE ni une validation électrique indépendante.
- Les parcours interactifs complets dans Chromium n'ont pas pu être vérifiés dans cet environnement ; les tests portent sur l'API, les fonctions et les éléments de l'interface.
