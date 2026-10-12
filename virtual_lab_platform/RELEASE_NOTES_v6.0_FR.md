# Notes de version — Virtual Lab Platform v6.0

**Objectif (feuille de route) :**
- un schéma commun pour toute valeur : propriété, valeur, unité, conditions, source, date, licence, incertitude et domaine d'applicabilité ;
- des données importées, calculées, simulées et expérimentales tenues séparées ;
- recherche, filtres, validation et export.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Schéma commun | `data_catalog.py` (schéma 1.0). **Jeu de données** : id, version, titre, nature, sources, licence, conditions, colonnes (nom, grandeur, unité vérifiée par `units.py`), lignes typées, incertitude, applicabilité, analyses publiées. **Propriété** : valeur, unité, incertitude, exactitude, valeur approchée ou non, conditions, sources, date. Toute entrée non conforme est refusée avec un code stable (9 cas testés). |
| Natures séparées | Cinq natures : `reference`, `experimental`, `imported`, `computed`, `simulated`. Une donnée « référence » ou « expérimentale » doit citer une source connue. Une donnée **simulée doit référencer l'empreinte du dossier** qui l'a produite. Une donnée **importée doit garder l'empreinte de son fichier d'origine**. Une entrée locale ne peut pas se déclarer « expérimentale » (`kind_not_allowed`). Les filtres sont stricts : une simulation n'apparaît jamais parmi les mesures. |
| Données sourcées livrées | **Puromycine** (Treloar 1974, reproduit par Bates & Watts 1988 et le paquet R *datasets*) : 23 mesures. **DBO** (Marske 1967, mêmes reproductions) : 6 mesures. Les 9 constantes physiques (SI 2019 ou CODATA 2018), avec leur incertitude relative, apparaissent comme entrées « référence ». Les analyses publiées (estimations et erreurs types) sont conservées : elles serviront à valider l'ajustement en v6.3. |
| Versionnage | `data_catalog/catalog_lock.json` enregistre l'empreinte du contenu de chaque jeu à sa version. **Une modification du contenu sans changement de version est détectée** (test : une valeur de DBO changée en silence). |
| Recherche, filtres, export | `GET /api/data/catalog?q=&kind=&type=&domain=`, `GET /api/data/catalog/{id}`, `GET /api/data/catalog/{id}.csv` (en-tête avec nature, sources et empreinte ; unités dans les noms de colonnes), `POST /api/data/catalog/validate`. Panneau « Catalogue de données » dans l'interface : recherche, filtre par nature, export CSV. |
| Entrées locales | Les jeux importés, calculés ou simulés sont enregistrés dans la base SQLite locale, avec leur empreinte. Leur intégrité est recontrôlée à chaque lecture. `simulated_from_dossier` convertit les lignes d'un dossier sauvegardé en jeu « simulé » lié à ce dossier. |

## Unités
`units.py` accepte désormais `count`/`counts` (sans dimension) et `ppm`/`ppb` (rapports de grandeurs de même nature ; la source précise lesquelles).

## Tests
- `tests/test_v60_data_catalog.py` : 16 tests.
- `tests/browser/test_v60_catalog_ui.py` : 1 test en navigateur réel.
- Contraste des en-têtes de tableaux et des étiquettes des panneaux clairs corrigé (axe-core : 0 violation).

## Limites
- Le contenu livré est volontairement réduit : 2 jeux expérimentaux et 9 constantes. Je n'ai saisi que des données dont je pouvais citer la source et que l'on peut recouper avec plusieurs reproductions publiées. Aucune autre table de propriétés n'a été tapée de mémoire.
- Les conditions de mesure (température, tampon) ne figurent pas dans les tables reproduites et sont signalées comme absentes.
- L'import de fichiers vers le catalogue, avec contrôle qualité, est prévu en v6.2.
