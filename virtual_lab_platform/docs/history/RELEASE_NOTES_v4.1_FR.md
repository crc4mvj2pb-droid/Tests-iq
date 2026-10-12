# Notes de version — Virtual Lab Platform v4.1

## Reproductibilité et intégrité des expériences
- Ajout d'une fonction commune de sérialisation canonique et de calcul SHA-256 de la configuration.
- Ajout de `GET /api/history/{id}/verify` pour signaler une empreinte absente, concordante ou divergente.
- Ajout de `POST /api/history/{id}/replay` pour relancer un circuit CC enregistré seulement si le modèle est pris en charge et si l'empreinte de configuration correspond.
- Création d'un nouveau dossier à chaque rejeu, avec lien `replay_of` vers le dossier source.
- Ajout des actions « Verify integrity » et « Replay circuit » dans l'historique sauvegardé.
- Version de l'API et de l'interface mise à 4.1.

## Validation
- 170 tests automatisés réussis.
- Compilation Python réussie.
- Syntaxe des trois blocs JavaScript inline validée par Node.js.
- Tests d'intégration API : calcul de circuit 9 V / 1 kΩ, sauvegarde, vérification de l'empreinte, rejeu, création d'un nouveau dossier et égalité des résultats numériques.
- Les interactions complètes en navigateur réel restent à vérifier séparément.
