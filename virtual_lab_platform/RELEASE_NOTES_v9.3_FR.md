# Notes de version — Virtual Lab Platform v9.3

**Objectif (feuille de route, jalon F) :**
- projets ; utilisateurs et rôles **si une collaboration multi-utilisateur devient nécessaire** ;
- partage de dossiers reproductibles.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Projets | `projects.py` : créer, lister, ajouter ou retirer une expérience (sans doublon), supprimer. **Supprimer un projet ne supprime jamais les expériences** (test). Tables `projects` et `project_experiments` dans la base locale, incluses dans les sauvegardes v9.0. |
| Partage | L'export d'un projet est un ZIP qui contient : `project.json`, les dossiers au format d'export standard, le **paquet reproductible de chaque expérience** (v6.4, vérifié valide) et `MANIFEST.json` (SHA-256). Test : une seconde installation vide importe le projet. Un second import relie le dossier déjà présent au lieu de le dupliquer. |
| Intégrité | Un fichier de projet modifié (une constante de vitesse changée) est **refusé, sans rien importer**, ni dossier ni projet (test). Les dossiers sont vérifiés un par un, en tout-ou-rien (v4.5). |
| Utilisateurs et rôles | **Non implémentés, par décision documentée** : l'application est locale et mono-utilisateur (écoute sur 127.0.0.1, sans authentification). La collaboration passe par l'échange de fichiers de projet vérifiables. Un mode multi-utilisateur demanderait authentification, chiffrement et serveur exposé : c'est un autre produit, à concevoir seulement si le besoin est établi. |
| Exposition | `GET` et `POST /api/projects`, `POST /api/projects/{id}/experiments` (ajouter ou retirer), `POST /api/projects/{id}/delete`, `GET /api/projects/{id}/export`, `POST /api/projects/import`. Panneau « Projets et partage ». |

## Tests
- `tests/test_v93_projects.py` : 5 tests.
- `tests/browser/test_v93_ui.py` : 1 test en navigateur réel.

## Limites
- Les fichiers de projet garantissent l'intégrité, pas l'identité de l'expéditeur.
- Taille maximale d'un import : 20 Mo par défaut, réglable.
