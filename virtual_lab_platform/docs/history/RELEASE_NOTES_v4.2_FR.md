# Notes de version — Virtual Lab Platform v4.2

**Objectif de la version :** le parcours électrique de référence et ses erreurs courantes sont vérifiés par de vrais tests navigateur automatisés, et les défauts bloquants ou majeurs rencontrés sur ce parcours sont corrigés. Base : audit indépendant de la v4.1 (`../audit_v4.1/AUDIT_v4.1_CLAUDE_FR.md`).

## Corrections
- **Bloquant corrigé :** `POST /api/lab/run` renvoyait toujours une erreur 500 (`UnboundLocalError` sur `configuration`). L'expérience est maintenant calculée, enregistrée et vérifiable. La configuration enregistrée inclut `workflow_id`.
- Un double-clic sur « Résoudre le circuit CC câblé » ne crée plus qu'un seul dossier : le bouton est désactivé (`aria-busy`) pendant la requête.
- La confirmation « ✓ Replayed as dossier #… » reste visible après le rafraîchissement de l'historique.
- Un corps JSON qui n'est pas un objet (`[1,2]`, `"x"`, `42`, `null`) renvoie 400 et non plus 500. Un corps absent renvoie 400 et non plus 413. Le rejeu accepte un corps vide.
- Les erreurs internes (500) sont maintenant écrites avec leur trace dans le terminal. Les détails ne sont toujours pas exposés par l'API.
- Les erreurs du circuit ont un code stable (`error_code`, `error_params`). L'interface les affiche en français ou en anglais, avec le nom du composant et non plus son identifiant interne. Une valeur booléenne ou vide n'est plus acceptée comme résistance ou comme tension.
- Une erreur réseau ou une réponse non JSON produit un message compréhensible (« Le serveur local est injoignable… »).
- Un numéro de version unique (`version.py`), utilisé par `/api/health`, `/api/version`, le titre de la page (qui affichait « v3.6 ») et le pied de page.
- Chemin de la base et port configurables (`VIRTUAL_LAB_DB`, `VIRTUAL_LAB_PORT`). Les valeurs par défaut sont inchangées.

## Tests
- Nouveaux tests navigateur Playwright/Chromium (`tests/browser/`). Ils cliquent le parcours complet : ajout, saisie, câblage, calcul, SQLite, vérification, rejeu, sauvegarde, rechargement, suppression. Ils couvrent aussi le double-clic, 5 erreurs de topologie, la coupure réseau et l'absence d'erreur console. En cas d'échec, une capture est écrite dans `test-artifacts/`.
- Preuve que ces tests détectent les défauts : exécutés contre l'interface v4.1 d'origine, **les 8 tests navigateur échouent**.
- Nouveaux tests HTTP (`tests/test_v42_api_robustness.py`) : lancement d'expérience, corps invalides, rejeu sans corps, codes d'erreur, journalisation des 500, version unique.
- `python scripts/run_validation.py` lance toute la suite et **génère** `VALIDATION_MATRIX_v4.2.md` et `TEST_RESULTS_v4.2.txt` à partir des résultats observés.
- `python scripts/build_release.py` produit l'archive avec un manifeste SHA-256, qu'il revérifie.

## Tests anciens modifiés (aucun supprimé)
- Six tests v3.4–v4.0 vérifiaient le texte littéral `"version": "4.1"` dans `app.py`. Ils vérifient maintenant `"version": APP_VERSION`.
- `test_v40_experiment_lifecycle.py` attend maintenant `wbFetchJson('/api/electrical/workbench-run'` (même endpoint, avec la nouvelle gestion d'erreurs). Il vérifie que `sort_keys=True` se trouve dans `experiment_lifecycle.py`, puisque la sérialisation locale inutilisée de `app.py` a été retirée.

## Limites restantes
- Les tests navigateur tournent dans Chromium headless. Ils ne remplacent pas un essai dans Safari sur macOS.
- Le glisser-déposer à la souris n'est pas couvert.
- Problèmes de l'audit traités dans les versions suivantes : dossiers non unifiés (v4.5), chimie non enregistrée (v4.6), contrôle `Origin`/`Host` (v4.8), sous-réseaux flottants (v4.4).
- Les résultats restent des calculs simulés, pas des mesures. Le solveur de paillasse n'est pas SPICE.
