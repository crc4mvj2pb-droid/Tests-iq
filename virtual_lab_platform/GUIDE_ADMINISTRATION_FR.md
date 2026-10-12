# Guide d'administration et de support — Virtual Lab Platform

## Installation
1. Python 3.10 ou plus récent (python.org). Aucune bibliothèque tierce.
2. Décompresser l'archive et vérifier son intégrité : `python scripts/verify_manifest.py` (ou `sha256sum -c MANIFEST.sha256`).
3. Contrôler l'installation : `python scripts/install_check.py` (une douzaine de contrôles, avec des données temporaires ; rien n'est écrit dans l'installation).
4. Lancer : `sh launch_macos_linux.sh`, `launch_windows.bat` ou `python app.py`.

## Configuration
Valeurs par défaut, remplacées par un fichier `virtual_lab_config.json` (à côté de `app.py`, ou chemin donné par `VIRTUAL_LAB_CONFIG`), lui-même remplacé par les variables d'environnement.

| Réglage | Variable | Défaut |
|---|---|---|
| port | `VIRTUAL_LAB_PORT` | 8765 |
| db_path | `VIRTUAL_LAB_DB` | `virtual_lab_history.sqlite3` |
| backup_dir | `VIRTUAL_LAB_BACKUP_DIR` | `backups/` |
| log_dir | `VIRTUAL_LAB_LOG_DIR` | `logs/` |
| backup_keep, log_max_bytes, max_request_bytes, max_import_bytes, requests_per_minute | (fichier) | 10, 2 Mo, 1 Mo, 20 Mo, 600 |

Une valeur invalide **empêche le démarrage**, avec la liste des problèmes. L'adresse d'écoute est toujours 127.0.0.1.

## Sauvegardes
- Une sauvegarde automatique est faite au démarrage si la dernière a plus de 24 h ; les 10 plus récentes sont conservées.
- Manuelle : panneau « Sauvegardes et maintenance », ou `python maintenance.py backup`.
- Vérifier : `python maintenance.py verify <fichier>`. Restaurer : `python maintenance.py restore <fichier>` (l'état actuel est d'abord sauvegardé).
- **Copiez régulièrement le dossier `backups/` hors de l'ordinateur** (disque externe, stockage de votre institution). La plateforme ne le fait pas pour vous.

## Mise à jour
1. Faites une sauvegarde.
2. Décompressez la nouvelle version dans un nouveau dossier.
3. Copiez-y `virtual_lab_history.sqlite3`, le dossier `scientific_library/imported_assets/` et, si vous en avez, `virtual_lab_config.json` et `backups/`.
4. Au premier lancement, la base est migrée automatiquement, avec une copie de sécurité. Les bases des versions 4.1 et suivantes sont prises en charge (test de migration d'une vraie base v4.1).

## Panne et récupération
- Si la base est endommagée, le serveur démarre en **mode récupération** : lecture seule, écritures refusées. Restaurez une sauvegarde depuis le panneau ou en ligne de commande ; le mode cesse après une restauration réussie.
- `python maintenance.py check` contrôle l'intégrité de la base.
- Les tâches de fond en cours sont perdues si le serveur s'arrête ; les dossiers enregistrés ne le sont pas.

## Journal et diagnostic
- `logs/requests.jsonl` : une ligne par requête (sans contenu ni valeur), avec rotation automatique.
- `GET /api/diagnostics` ou le bouton « Diagnostic » : versions, état de la base, sauvegardes, erreurs récentes, espace disque.

## Sécurité
Le serveur écoute sur la boucle locale seulement. Il refuse les requêtes d'autres sites, envoie des en-têtes de sécurité et une politique de sécurité du contenu (CSP), et limite la taille, la profondeur et le débit des requêtes. Les fichiers importés ne sont jamais exécutés. Il n'y a pas d'authentification : **ne pas exposer le serveur sur un réseau**.

## Procédure de support
Pour signaler un problème, joignez :
1. la sortie de `GET /api/diagnostics` (aucune donnée d'expérience) ;
2. les dernières lignes de `logs/requests.jsonl` ;
3. la version (`GET /api/version`), le système et le navigateur ;
4. si possible, le **paquet reproductible** de l'expérience concernée, après avoir vérifié qu'il ne contient pas de données confidentielles.

## Validation complète (développeurs)
`python -m pip install -r requirements-dev.txt`, `python -m playwright install chromium`, puis `python scripts/run_validation.py`, `python scripts/run_benchmarks.py`, `python scripts/run_assistant_eval.py`, `python scripts/check_syntax.py` et `python scripts/accessibility_audit.py`.
