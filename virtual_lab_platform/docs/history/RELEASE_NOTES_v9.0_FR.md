# Notes de version — Virtual Lab Platform v9.0

**Objectif (feuille de route, jalon F) :**
- historique, sauvegardes, import et export ;
- configuration et migrations de l'installation locale.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Configuration validée | `config.py`. Les valeurs par défaut sont remplacées par un fichier JSON (`virtual_lab_config.json` ou `VIRTUAL_LAB_CONFIG`), lui-même remplacé par les variables d'environnement. La source de chaque valeur est indiquée. Une valeur invalide ou inconnue **empêche le démarrage**, avec la liste des problèmes (test en processus séparé), au lieu d'être corrigée en silence. L'adresse d'écoute reste fixée à 127.0.0.1 (application locale mono-utilisateur). Route `GET /api/admin/config` : les chemins sont réduits à des noms, pour ne pas exposer l'arborescence personnelle. |
| Sauvegardes cohérentes | `maintenance.py`. Un ZIP contient : une copie de la base faite avec **l'API de sauvegarde en ligne de SQLite** (cohérente pendant des écritures concurrentes, test avec un écrivain en parallèle), les fichiers importés, et `backup.json` (version, schéma, nombre d'expériences, SHA-256 de chaque fichier). L'écriture est atomique : un arrêt brutal ne laisse jamais de sauvegarde à moitié écrite sous son nom final. |
| Vérification | `verify_backup` recalcule les empreintes et contrôle l'intégrité de la copie de la base (`PRAGMA integrity_check`). Une base endommagée est détectée (test sur un fichier corrompu), et le serveur prévient au démarrage. |
| Restauration sûre | Elle vérifie d'abord. **Une sauvegarde altérée est refusée et rien n'est modifié** (test). Sinon, l'état actuel est enregistré dans une sauvegarde « pre-restore », puis la base et les fichiers importés sont remplacés, et une migration de schéma est faite si nécessaire. |
| Exposition | `POST /api/admin/backup`, `GET /api/admin/backups`, `POST /api/admin/backup/verify` et `/restore` (seuls les noms de fichiers listés sont acceptés : aucun chemin ne peut être injecté), `GET /api/admin/integrity`. En ligne de commande : `python maintenance.py backup | list | verify <f> | restore <f> | check`. Panneau « Sauvegardes et maintenance » dans l'interface. Rétention : `prune` garde les N plus récentes. |
| Données hors des archives | Les dossiers `backups/` et `logs/` sont exclus des archives de version, comme la base. |

## Tests
- `tests/test_v90_config_backup.py` : 10 tests.
- `tests/browser/test_v90_ui.py` : 1 test en navigateur réel.

## Limites
- Les sauvegardes restent sur le même disque, par défaut dans `backups/`. Une copie hors de l'ordinateur reste à faire par l'utilisateur ; la documentation de la v9.4 le dira.
- L'empreinte garantit l'intégrité, pas l'authenticité.
