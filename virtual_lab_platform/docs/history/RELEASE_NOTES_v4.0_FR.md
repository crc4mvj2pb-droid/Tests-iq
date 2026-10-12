# Notes de version — Virtual Lab Platform v4.0

## Cycle d'expérience traçable pour les circuits
- Ajout de l'endpoint `POST /api/electrical/workbench-run`.
- Enregistrement automatique du calcul de circuit de la paillasse dans l'historique SQLite.
- Dossier comprenant configuration, résultats, hypothèses, limites, statut `simulated_calculation` et empreinte SHA-256.
- Affichage de l'identifiant du dossier et d'un extrait de l'empreinte après le calcul.
- Actualisation automatique de la liste des expériences enregistrées.
- Conservation de `/api/electrical/workbench-solve` pour les intégrations existantes.
- Mise à jour de la version de l'application à 4.0.

## Validation
- 164 tests automatisés réussis.
- Compilation Python réussie.
- Syntaxe des trois blocs JavaScript vérifiée par Node.js.
- Test d'intégration réel de l'API : circuit source 9 V + résistance 1 kΩ + masse, courant calculé 9 mA ; dossier sauvegardé puis relu depuis l'historique.
- Test de navigation interactive complet dans Chromium non disponible dans cet environnement (navigation bloquée par la politique de l'environnement).
