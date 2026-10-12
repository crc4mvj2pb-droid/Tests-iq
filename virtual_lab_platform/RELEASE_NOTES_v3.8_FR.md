# Notes de version — v3.8

## Objectif

Fiabiliser l'utilisation de l'interface avant d'ajouter de nouveaux modèles scientifiques.

## Modifications

- Statut de l'API locale visible et vérifié au démarrage.
- Message hors ligne avec commande de lancement et URL correctes.
- Restauration manuelle de la dernière paillasse enregistrée.
- Confirmation avant remplacement de la paillasse actuelle.
- Gestion visible des erreurs de stockage local.
- Validation des données de sauvegarde et conservation des connexions valides.
- Tests de non-régression supplémentaires.

## Limites de validation

Les tests Python et les vérifications syntaxiques sont automatisés. Le navigateur Chromium disponible dans l'environnement de travail a bloqué la navigation automatisée (`ERR_BLOCKED_BY_ADMINISTRATOR`); aucun test de clic réel dans un navigateur n'est donc revendiqué pour cette version.
