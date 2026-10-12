# Virtual Lab Platform v4.0

Virtual Lab Platform est un prototype local de laboratoire scientifique virtuel multidisciplinaire. La v4.0 met l'accent sur un parcours d'expérience traçable pour le solveur électrique de la paillasse.

## Nouveauté centrale : cycle d'exécution traçable

L'action « Résoudre le circuit CC câblé » utilise désormais `/api/electrical/workbench-run`. Le serveur :

1. valide et résout le réseau à partir des composants et des connexions par bornes ;
2. renvoie les tensions de nœud, courants, chutes de tension, puissances et contrôles numériques ;
3. construit une configuration canonique composants + câbles et calcule son empreinte SHA-256 ;
4. enregistre un dossier dans l'historique SQLite ;
5. retourne l'identifiant du dossier et le statut explicite `simulated_calculation` ;
6. déclenche l'actualisation de l'historique dans l'interface.

L'ancien endpoint `/api/electrical/workbench-solve` reste disponible pour compatibilité sans enregistrement automatique.

## Architecture et données
- Serveur : Python `http.server`, API locale.
- Interface : HTML/CSS/JavaScript dans `static/index.html`.
- Historique : SQLite, fichier `virtual_lab_history.sqlite3` créé au premier enregistrement.
- Export de l'espace de travail et export des résultats : JSON.
- Modèles scientifiques : moteurs spécialisés et contrats de validation propres à chaque domaine.

## Démarrage
Consultez [DEMARRAGE_RAPIDE_v4.0_FR.md](DEMARRAGE_RAPIDE_v4.0_FR.md).

## Tests
Consultez [TEST_RESULTS_v4.0.txt](TEST_RESULTS_v4.0.txt). Les tests automatisés et l'intégration API sont exécutés ; les clics complets dans Chromium restent non vérifiés dans cet environnement car le navigateur bloque la navigation vers les fichiers locaux et localhost.

## Limites à ne pas masquer
- La sauvegarde d'une exécution est un dossier logiciel, pas une validation scientifique indépendante.
- L'empreinte permet de détecter qu'une configuration diffère ; elle ne prouve pas la justesse scientifique.
- Le solveur électrique de paillasse est un solveur résistif CC idéal, pas un remplacement de SPICE.
- Certains workflows multidisciplinaires du catalogue sont des modèles L0 de planification et n'effectuent pas de calcul scientifique.
- Aucune mesure physique réelle n'est produite.
