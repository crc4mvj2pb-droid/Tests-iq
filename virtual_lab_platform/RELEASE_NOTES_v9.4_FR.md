# Notes de version — Virtual Lab Platform v9.4 (version finale)

**Objectif (feuille de route, jalon F) :** documentation, installation, mises à jour, procédure de support ; vérification finale.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Installation vérifiable | `scripts/install_check.py` (bibliothèque standard seulement) démarre le vrai serveur sur un port libre, avec base, sauvegardes et journaux temporaires. Il réussit **12 contrôles** : démarrage, page, 27 contrats, calcul, dossier vérifié, rapport, paquet relancé par un tiers en processus isolé, sauvegarde vérifiée puis restaurée, réponse tracée de l'assistant, diagnostic, 200 requêtes (médiane d'environ 1 ms), **rien d'écrit dans l'installation**. |
| Documentation | Nouveau `README.md` (l'ancien, qui décrivait la v2.7, est archivé dans `docs/history/`). `GUIDE_UTILISATEUR_FR.md` décrit les 11 panneaux et les bonnes pratiques. `GUIDE_ADMINISTRATION_FR.md` couvre installation, configuration, sauvegardes hors de l'ordinateur, mise à jour, récupération, journal, sécurité et **procédure de support**. L'architecture est complétée et le bilan du jalon F est écrit. |
| Mises à jour | La procédure est écrite. Une vraie base v4.1 est migrée automatiquement (test depuis la v4.5). Les tables ajoutées depuis (catalogue, journal, décisions, projets) sont créées à la première utilisation. |
| Contrôle final en dossier propre | Voir `RC_CHECK_v9.4_FR.md`. |

## Tests
`tests/test_v94_install_check.py` : 2 tests.

## Limites
Voir `RAPPORT_FINAL_FR.md`, section « Limites restantes ».
