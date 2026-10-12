# Notes de version — Virtual Lab Platform v6.2

**Objectif (feuille de route) :**
- import CSV et JSON avec aperçu, détection des unités et validation de schéma ;
- rapport des valeurs manquantes, doublons, valeurs aberrantes et transformations appliquées ;
- fichier d'origine conservé inchangé.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| CSV et JSON | `data_import.py` lit le CSV (séparateur `,` `;` ou tabulation détecté ; marque d'ordre des octets retirée à la lecture seulement) et le JSON (`{columns, rows}` ou liste d'objets). Les fichiers mal formés sont refusés avec un code : fichier vide, lignes de longueur inégale, colonnes en double, aucune ligne, JSON invalide. |
| Aperçu et unités | Les unités se lisent dans les en-têtes, au format `nom (unité)` ou `nom [unité]`, et sont vérifiées par `units.py`. Une unité non reconnue (« fortnights ») est signalée et **bloque l'import** tant que l'en-tête n'est pas corrigé. Une colonne numérique sans unité est signalée. L'aperçu affiche les 10 premières lignes, le type, le minimum et le maximum de chaque colonne. |
| Validation de schéma | `check_schema` compare au schéma attendu : colonne absente, type erroné, unité absente ou **incompatible** (s et min sont compatibles, s et m ne le sont pas). |
| Rapport de qualité | Il signale les valeurs manquantes (avec les numéros de ligne), les **doublons** (« ligne 4 = ligne 3 ») et les **valeurs aberrantes** selon le score z modifié \|0,6745·(x − médiane)/MAD\| > 3,5 (Iglewicz & Hoaglin, 1993). La règle a été vérifiée par un calcul à la main. **Rien n'est supprimé, corrigé ni imputé** : les lignes en cause restent telles quelles et la décision revient à l'utilisateur. |
| Transformations listées | Chaque transformation est listée dans le rapport et dans l'entrée du catalogue (`provenance.transformations`) : retrait de la marque d'ordre des octets, séparateur détecté, unités lues dans les en-têtes, texte converti en nombres, objets JSON convertis en lignes. |
| Fichier d'origine inchangé | Le fichier est stocké **octet pour octet** dans la bibliothèque des imports. Le test compare les octets et l'empreinte SHA-256. L'entrée du catalogue, de nature `imported`, garde l'empreinte, le nom du fichier, l'origine déclarée par l'utilisateur et le rapport de qualité. |
| API et interface | `POST /api/data/preview` (rapport sans les données complètes, plus le contrôle de schéma facultatif) et `POST /api/data/import`. Dans le catalogue, une section « Importer un fichier » : aperçu et contrôle qualité d'abord, import ensuite, puis l'entrée apparaît filtrée sur « importée ». |

## Tests
- `tests/test_v62_data_import.py` : 14 tests.
- `tests/browser/test_v62_import_ui.py` : 1 test en navigateur réel.

## Limites
- Seul le point est accepté comme séparateur décimal. Une valeur « 1,5 » dans un CSV à point-virgule est lue comme du texte et signalée, jamais convertie en silence.
- La règle des valeurs aberrantes est univariée et suppose une distribution à peu près symétrique. Une valeur signalée n'est pas forcément une erreur.
- L'origine déclarée par l'utilisateur n'est pas vérifiée par la plateforme. Une donnée importée reste « importée » et n'est jamais présentée comme une mesure publiée.
