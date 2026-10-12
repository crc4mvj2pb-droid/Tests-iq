# Notes de version — Virtual Lab Platform v9.1

**Objectif (feuille de route, jalon F) :** sécurité des entrées, limites de ressources, isolation des imports, protection des données.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Entrées JSON | `security.parse_json` refuse les littéraux `NaN` et `Infinity`, que `json.loads` acceptait **par défaut jusqu'ici** (défaut réel corrigé, `invalid_json`), ainsi qu'une imbrication de plus de 64 niveaux (`json_too_deep`). Les limites de taille existantes (1 Mo, 20 Mo pour l'import d'historique) sont désormais réglables par la configuration validée de la v9.0. |
| Isolation des imports | **Défaut réel corrigé** : le refus des déclarations DOCTYPE et ENTITY dans les fichiers SBML ne regardait que les 20 000 premiers caractères. Un long commentaire placé avant un DOCTYPE contournait le contrôle. Le texte entier est maintenant examiné ; une « bombe d'entités » précédée de 30 000 caractères de commentaire est refusée, sans aucun fichier stocké (test). Les fichiers importés ne sont jamais exécutés, et leurs noms sont nettoyés. |
| En-têtes de sécurité | Sur toutes les réponses : `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cross-Origin-Opener-Policy`. Les pages HTML portent en plus une **Content-Security-Policy** limitée aux ressources du serveur lui-même : ni cadre, ni objet, ni `eval`. |
| L'interface fonctionne sous cette politique | Test navigateur **sans contournement** : chargement, assistant et catalogue avec 0 violation de la politique et 0 erreur console. L'interface n'utilise ni `eval` ni `new Function`. Les autres tests navigateur contournent la politique uniquement pour l'outil de test, dont `wait_for_function` utilise `eval`. |
| Limite de débit | Seau à jetons par serveur et par client (600 requêtes par minute par défaut, réglable). Au-delà, réponse 429 avec `Retry-After` (test). Il empêche un script emballé de monopoliser la machine. |
| Protection des données | Inchangée et rappelée : écoute sur 127.0.0.1 seulement, requêtes d'autres sites refusées (v4.8), aucune donnée envoyée à l'extérieur, données personnelles absentes des réponses d'administration et de l'environnement des paquets. |

## Tests
- `tests/test_v91_security.py` : 7 tests.
- `tests/browser/test_v91_csp.py` : 1 test en navigateur réel sous la politique réelle.

## Limites
- La politique autorise les scripts et styles intégrés à la page (`'unsafe-inline'`), car l'interface tient en un seul fichier. Sans source externe ni `eval`, le risque reste limité à un serveur local.
- Il n'y a pas d'authentification : l'application est mono-utilisateur et locale. Ne pas l'exposer sur un réseau.
