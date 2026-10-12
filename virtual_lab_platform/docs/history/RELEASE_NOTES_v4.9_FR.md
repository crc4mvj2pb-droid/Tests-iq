# Notes de version — Virtual Lab Platform v4.9 (version candidate)

**Objectif de la version :** tout retester dans un environnement propre, vérifier l'installation et préparer une archive fiable. Cette version clôt le grand jalon A.

## Contenu
- **Contrôle de version candidate** (`RC_CHECK_v4.9_FR.md`) :
  - archive vérifiée dans un dossier vide ;
  - démarrage par le lanceur sans aucune bibliothèque tierce ;
  - suite exécutée sur **Python 3.10, 3.11, 3.12, 3.13 et 3.14** ;
  - environnement de développement neuf : 600/600.
- **Guide d'installation consolidé** (`INSTALLATION_FR.md`) : utilisation, données, mise à jour depuis une version antérieure, vérification de l'archive, validation.
- `scripts/verify_manifest.py` : vérifie l'archive indépendamment du script de construction.
- **Rangement :** les 103 documents des versions précédentes sont dans `docs/history/`, et la feuille de route et le brief d'audit dans `docs/`. `app_test.py`, une copie obsolète et inutilisée de `app.py`, est archivé dans `docs/history/legacy/` avec une note. Rien n'a été supprimé.
- `README.md` : architecture et vérification mises à jour.
- **Bilan du jalon A** : `JALON_A_BILAN_FR.md`.

## Corrections
- Le lanceur macOS/Linux affiche le port réellement utilisé (`VIRTUAL_LAB_PORT`).
- Sans Playwright, chaque test navigateur est ignoré individuellement avec une raison explicite. La matrice les liste comme « impossible à lancer » au lieu d'un seul test ignoré.

## Limites
- Windows, macOS, Safari et Firefox n'ont pas été testés ici (voir `RC_CHECK_v4.9_FR.md`).
