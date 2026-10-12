# Notes de version — Virtual Lab Platform v4.5

**Objectif de la version :** exporter, importer, restaurer et migrer les projets sans perte de données, et rendre la vérification et le rejeu honnêtes. Cette version corrige les problèmes n° 2 à 5 de l'audit v4.1.

## Format de dossier unique (schéma 2)
- `dossier.py` + `experiment_service.py` : tous les endpoints qui enregistrent (`workbench-run`, rejeu, `protocol/run`, `lab/run`, `experiments`) produisent le même format. Il contient :
  - `dossier_schema_version`, `app_version` et `engine {id, version}` ;
  - `model_id`, `configuration`, `configuration_hash` et `data_status` ;
  - `created_at_utc` ;
  - **`dossier_hash`** : l'empreinte du dossier complet, résultats compris.

  Les champs des résultats restent au premier niveau, donc l'interface et les intégrations existantes fonctionnent sans changement.
- Les expériences de modèles ne sont plus enregistrées sous « unknown ». Les protocoles enregistrent leur configuration.
- Chaque moteur a un numéro de version : `electrical_circuits` 2.0, `workbench_circuit` 2.0, `protocol_engine` 1.0, `lab_designer` 1.0, `engine` 1.0.

## Vérification à trois niveaux
- `full` : la configuration **et** le dossier complet correspondent à leurs empreintes. **Un résultat modifié est maintenant détecté.**
- `configuration_only` : dossier antérieur à v4.5, sans empreinte complète. C'est dit clairement : les résultats ne sont pas couverts.
- `unverifiable` : aucune empreinte (par exemple un protocole v4.1).
- Les colonnes d'index SQLite sont comparées au dossier. Une divergence est signalée.

## Rejeu avec comparaison
- Le rejeu compare, valeur par valeur, les tensions, les courants et le courant de source à ceux du dossier d'origine. La tolérance est fondée sur les incertitudes publiées en v4.4, et sur 1e-9 relatif pour les dossiers anciens qui n'en publient pas.
- Le résultat indique la version du moteur d'origine et celle du rejeu (`engine_changed`). L'interface affiche « résultats identiques… » ou le nombre d'écarts.
- Registre `REPLAYERS` : le rejeu s'étend à d'autres modèles (la chimie en v4.6).
- **Le circuit enregistré par le vrai code v4.1 se rejoue à l'identique avec le moteur v4.4.** Le changement de moteur est signalé.

## Migration SQLite
- Schéma de base 2 : colonnes `dossier_hash`, `dossier_schema_version` et `app_version`, plus la table `schema_meta`.
- **Une copie de sauvegarde automatique est faite avant la migration** (`virtual_lab_history.sqlite3.backup-schema-1-<date>`). La migration est idempotente. **Le JSON des dossiers n'est jamais réécrit.**
- Les lignes anciennes sont réparées dans l'index : `model_id` « unknown » → l'identifiant réel, titre et empreinte retrouvés.
- La migration est testée sur une base **produite par le code v4.1 d'origine** (`tests/fixtures/v41_history.sqlite3`).

## Export et import
- `GET /api/history/{id}/export`, `GET /api/history/export`, `POST /api/history/import` (jusqu'à 20 Mo, 500 dossiers).
- L'import vérifie chaque dossier et applique **tout ou rien** : un seul dossier altéré fait refuser tout le fichier, qui est rejeté et détaillé. Les dossiers déjà présents (même `dossier_hash`) sont ignorés. Chaque dossier importé garde sa provenance (`imported_from`).
- Interface : bouton « Export » par dossier, « Exporter tout l'historique », « Importer des dossiers… ».
- **Import d'une paillasse** depuis un fichier, avec la même validation et le même compte rendu de nettoyage qu'en v4.3.

## Défauts trouvés par les tests navigateur et corrigés
- **Empreinte cassée après passage dans le navigateur** : JavaScript écrit `9.0` sous la forme `9`. Une empreinte calculée en Python ne correspondait plus après export/import par l'interface. La forme canonique normalise maintenant les nombres. Les empreintes antérieures restent vérifiables, car les deux formes sont acceptées.
- Deux calculs identiques produisaient deux dossiers identiques, et le second était pris pour un doublon à l'import. `created_at_utc` les distingue maintenant.

## Test ancien modifié (aucun supprimé)
- `test_v40_experiment_lifecycle.py::test_endpoint_creates_reproducible_configuration_hash_and_saves_history` cherchait des lignes de code dans `app.py`. Il vérifie maintenant les mêmes garanties par un vrai appel HTTP : configuration, empreinte, statuts et enregistrement.

## Limites
- Le rejeu reste limité aux modèles du registre : circuit CC pour l'instant, chimie en v4.6. Les expériences du concepteur et les protocoles sont vérifiables mais pas rejouables.
- L'empreinte détecte les modifications accidentelles ou naïves. Ce n'est pas une signature : quelqu'un qui recalcule l'empreinte peut falsifier un dossier.
- Les protocoles v4.1, qui n'ont aucune empreinte, ne peuvent pas être importés (« unverifiable »).
