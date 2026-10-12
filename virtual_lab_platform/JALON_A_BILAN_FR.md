# Bilan du grand jalon A — « Un laboratoire vraiment utilisable » (v4.2 → v4.9)

**Condition de passage à v5 (feuille de route) :** les parcours électriques et chimiques essentiels, la sauvegarde/restauration et les tests intégrés doivent être documentés et reproductibles.

| Exigence | Preuve reproductible | Documentation |
|---|---|---|
| Parcours électrique complet depuis l'interface | `tests/browser/test_v42_workbench_e2e.py` : ajouter, saisir, câbler, résoudre, SQLite, vérifier, rejouer, sauvegarder, recharger, supprimer. Ajoutés : double-clic, 5 erreurs de topologie, coupure réseau, clavier seul (`test_v48`) | `docs/history/RELEASE_NOTES_v4.2_FR.md`, `v4.3`, `v4.4` |
| Solveur électrique cohérent | `tests/test_v44_dc_reference.py` : formules analytiques (Wheatstone, R-2R) et solveur exact indépendant ; sur 300 réseaux mal conditionnés, l'erreur reste sous l'incertitude publiée | `RELEASE_NOTES_v4.4_FR.md` |
| Parcours chimique complet | `tests/browser/test_v46_chemistry_path.py` (stœchiométrie, cinétique, rejeu depuis l'historique) ; `tests/test_v46_chemistry.py` (solutions analytiques, estimation d'erreur RK4) | `RELEASE_NOTES_v4.6_FR.md` |
| Sauvegarde, restauration, export, import, migration | `tests/test_v45_dossiers.py` (migration d'une **vraie** base v4.1, export/import sans perte, refus d'un fichier altéré) ; `tests/browser/test_v45_save_restore.py` ; `tests/browser/test_v43_workbench_integrity.py` | `RELEASE_NOTES_v4.5_FR.md`, `v4.3`, `INSTALLATION_FR.md` |
| Instruments reliés aux résultats | `tests/test_v47_linked_instruments.py` (couverture statistique de l'intervalle k = 2) ; test navigateur v4.7 | `RELEASE_NOTES_v4.7_FR.md` |
| Erreurs, accessibilité, sécurité locale | `tests/browser/test_v48_interface_quality.py` ; `tests/test_v48_local_security.py` | `RELEASE_NOTES_v4.8_FR.md` |
| Tests intégrés et reproductibles | `python scripts/run_validation.py` génère `VALIDATION_MATRIX_v4.9.md` et `TEST_RESULTS_v4.9.txt` ; contrôle en environnement propre dans `RC_CHECK_v4.9_FR.md` | `INSTALLATION_FR.md` |

**Évaluation :** la condition est remplie **pour le périmètre testé**, c'est-à-dire Chromium sous Linux et Python 3.10 à 3.14. **Je recommande toutefois un essai par vous-même sur votre Mac (Safari) avant de considérer le jalon comme clos**, car ce système et ce navigateur n'ont pas pu être testés ici.

## Chiffres
- Tests : 170 en v4.1 → **600 en v4.9**, dont 31 dans un vrai navigateur. Aucun test n'a été supprimé. Les tests anciens modifiés sont listés dans les notes de chaque version.
- Problèmes de l'audit v4.1 :
  - corrigés : n° 1 à 18, 20 et 21 (le 20 en partie : `app_test.py` archivé, mais les vieux tests « chaîne présente » existent toujours, complétés par des tests de comportement) ;
  - n° 22 (cosmétique) traité en partie : documentation rangée, version unique ;
  - n° 19 (instruments) traité en v4.7.
- Défauts nouveaux trouvés **par les tests navigateur** et corrigés :
  - double soumission (paillasse, concepteur) ;
  - message de rejeu invisible ;
  - empreinte cassée après passage par JavaScript (`9.0` → `9`) ;
  - libellés presque invisibles (contraste 1,56).

## Ce qui reste hors du jalon A (prévu en v5 et après)
- Solveurs à pas adaptatif ou pour systèmes raides (v5.2). Contrôle dimensionnel systématique des unités (v5.1).
- RC/RL/RLC depuis la paillasse (v5.4). Le solveur de paillasse reste un solveur CC résistif, pas SPICE.
- Comparaison avec ngspice : non faite, faute d'outil disponible ici.
- Les modules plus anciens (13 modèles de `models.py`, SBML, outils de recherche) n'ont pas été revalidés de façon indépendante pendant le jalon A. Leurs propres tests passent.
- Tous les résultats sont des calculs ou des mesures simulées, pas des données expérimentales.
