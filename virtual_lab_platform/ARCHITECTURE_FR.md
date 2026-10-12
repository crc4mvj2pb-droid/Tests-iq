# Architecture — Virtual Lab Platform

| Couche | Modules | Rôle | Règle vérifiée par test |
|---|---|---|---|
| Interface | `static/index.html`, `app.py` (routes HTTP) | Saisie, affichage, contrôle `Host`/`Origin`, format d'erreur unique | — |
| Orchestration | `experiment_service.py`, `model_registry.py` | Validation par contrat, exécution, dossiers, rejeu, export/import | — |
| Calcul scientifique | `electrical_circuits.py`, `workbench_circuit.py`, `electrical_advanced.py`, `chemical_kinetics.py`, `reaction_stoichiometry.py`, `models.py`, `virtual_instruments.py`, `linked_measurements.py` | Calculs purs, sans réseau ni base de données | Les moteurs n'importent ni `app`, ni `history`, ni `sqlite3`, ni `http`, ni `urllib` (`tests/test_v50_contracts.py`) |
| Persistance | `history.py`, `dossier.py` | SQLite, migrations, format de dossier et empreintes | — |
| Contrats | `contracts.py` | Schéma commun d'un modèle et validation des entrées | Chaque contrat est bien formé et fidèle à son moteur |

## Contrat d'un modèle (v5.0, `contracts.py`)
Un contrat contient :
- `id`, `version` (version du moteur) et `contract_version` ;
- `title`, `domain` et `engine` ;
- `parameters[]` : nom, type (`number`, `integer`, `string`, `boolean`, `enum`, `array`, `object`), **unité obligatoire pour les nombres**, bornes (`minimum`, `exclusive_minimum`, `maximum`), défaut, caractère obligatoire, choix possibles et description ;
- `outputs[]` : nom, chemin dans le résultat et **unité** ;
- `assumptions[]`, `validity[]`, `error_codes[]`, `references[]` et `equations[]`.

L'unité `a.u.` désigne des unités arbitraires ou « unités du modèle ». Elle ne se convertit en aucune unité physique.

## Exécution standard
`GET /api/contracts`, `GET /api/contracts/{id}`, puis `POST /api/models/{id}/run` avec `{"inputs": {...}}`. La réponse a toujours la même forme :
`{model_id, model_version, contract_version, inputs (normalisés), outputs {nom: {value, unit}}, result, warnings, assumptions, limitations, provenance}`.

## Format d'erreur unique
Toute réponse d'erreur contient `{error, error_code, error_params?}`. Le code est précis quand le moteur en fournit un (par exemple `out_of_range`, `unknown_parameter` ou `floating_network`). Sinon, il dépend du statut HTTP (`invalid_request`, `not_found`, `conflict`…).
