# Notes de version — Virtual Lab Platform v6.4

**Objectif (feuille de route) :**
- un journal d'événements de l'expérience : modèle et version, paramètres, fichiers sources, graines, résultats, erreurs et environnement logiciel ;
- une empreinte calculée sur un manifeste complet et clairement défini, **sans la présenter comme une preuve d'authenticité externe** ;
- l'export d'un paquet reproductible avec manifeste et rapport.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Journal d'événements | Table `experiment_events`. Chaque action du cycle de vie est enregistrée avec son heure : `saved` (modèle, moteur et version, version de l'application, empreintes de configuration et de dossier, graines), `verified` (niveau), `replayed` (identifiant du rejeu, identité des résultats, changement de moteur), `exported`, `imported`, `packaged` (empreinte du manifeste). Route `GET /api/history/{id}/events`. |
| Environnement | `environment.json` contient : versions de Python, de l'application, de SQLite et des moteurs, système, architecture, et « aucun paquet tiers ». **Aucune donnée personnelle** : ni nom d'utilisateur, ni nom de machine, ni chemin (test). Les graines aléatoires de la configuration sont relevées. |
| Paquet reproductible | `GET /api/history/{id}/package` produit un ZIP. Il contient : le dossier, la configuration, le journal, l'environnement, les **données utilisées** (jeu du catalogue en JSON et CSV, **fichier importé d'origine octet pour octet**, dossiers sources d'une lecture d'instrument), un **instantané du code de la plateforme** (bibliothèque standard seulement), `reproduce.py` et `README_REPRODUCE.md`. Ni base de données utilisateur, ni autre fichier importé, ni cache. |
| Manifeste et empreinte | `MANIFEST.json` donne la SHA-256 et la taille de chaque fichier, plus l'empreinte de la liste elle-même. Sa portée est écrite : « intégrité des fichiers listés ; ni signature, ni preuve d'auteur ». `verify_package` détecte un fichier modifié (test : une constante de vitesse changée dans le dossier). |
| **Reproduction par un tiers** | Le test extrait le paquet dans un répertoire vide et lance `python -I reproduce.py` dans un **processus séparé**, sans accès au dépôt (mode isolé, variables PYTHON* retirées). Le script vérifie le manifeste, recharge les données dans une base temporaire, refait le calcul avec le code embarqué et le compare au dossier. Cas réussis : cinétique (> 50 valeurs), **ajustement sur les données publiées de la Puromycine**, **ajustement sur un fichier importé**, **lecture d'instrument avec son dossier source**. Un paquet dont le code embarqué a été modifié est **refusé** (code de sortie 2). |
| Interface | Lien « Paquet reproductible » sur chaque expérience de l'historique (ajouté avec la v6.5). |

## Tests
`tests/test_v64_traceability.py` : 9 tests, dont 5 reproductions en processus séparé.

## Limites
- Le paquet garantit l'intégrité, pas l'authenticité : quelqu'un qui refait un paquet complet peut recalculer un manifeste cohérent. Une signature cryptographique demanderait une gestion de clés, hors du périmètre.
- Un dossier sans rejoueur (protocoles, flux de laboratoire conceptuels) est exporté, mais `reproduce.py` indique « non reproductible automatiquement » au lieu de prétendre le contraire.
- La reproduction attend une version de Python récente (3.10 ou plus). Les écarts d'arrondi entre plateformes restent dans les tolérances de comparaison des moteurs (1e-9 à 1e-12 relatif).
