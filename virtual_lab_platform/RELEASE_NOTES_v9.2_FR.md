# Notes de version — Virtual Lab Platform v9.2

**Objectif (feuille de route, jalon F) :** observabilité, diagnostics et récupération après panne.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Journal des requêtes | `observability.py` produit une ligne JSON par requête : heure UTC, méthode, chemin **sans paramètres**, statut, code d'erreur et durée. **Aucun corps de requête, aucune valeur, aucune adresse client** (test : une valeur envoyée n'apparaît pas dans le journal). Le journal est gardé en mémoire et, au lancement par `app.py`, écrit dans `logs/requests.jsonl`, avec rotation par taille (3 anciens fichiers, test). |
| Diagnostic | `GET /api/diagnostics` et bouton « Diagnostic » de l'interface. Ils donnent : versions (application, Python, SQLite, système), durée de fonctionnement, compteurs de requêtes, 20 dernières erreurs (codes seulement), intégrité, taille et nombre d'expériences de la base, sauvegardes, espace disque libre, tâches en cours, sources de configuration, comptes de maturité. **Aucun chemin personnel** n'est exposé (test). |
| Récupération après panne | Si la base échoue au contrôle d'intégrité au démarrage, le serveur démarre en **mode récupération** : lectures possibles, **écritures refusées (503 `recovery_mode`)**, sauf la vérification, la création et la restauration de sauvegardes. Une restauration réussie le fait sortir de ce mode. Test en **processus séparé** avec une base corrompue : mode récupération actif, écriture refusée, message affiché, et aucune sauvegarde automatique d'une base endommagée. |
| Sauvegarde automatique | Au démarrage, une sauvegarde est faite si la plus récente a plus de 24 h, puis la rétention configurée est appliquée. Un échec de cette sauvegarde n'empêche pas le démarrage. Les sauvegardes restent atomiques (v9.0). |

## Tests
- `tests/test_v92_observability.py` : 6 tests.
- `tests/browser/test_v92_ui.py` : 1 test en navigateur réel.

## Limites
- Les tâches de fond (analyses, plans) vivent en mémoire : un arrêt du serveur les interrompt. Elles se relancent à la main ; les dossiers déjà sauvegardés ne sont pas affectés.
- Pas d'alerte automatique : le diagnostic se consulte.
