# Installation et vérification — Virtual Lab Platform

## 1. Utiliser l'application (aucune bibliothèque à installer)
1. Installer **Python 3.10 ou plus récent** (python.org). L'application n'utilise que la bibliothèque standard.
2. Décompresser l'archive `virtual_lab_platform_v<version>.zip`.
3. Lancer :
   - macOS / Linux : `sh launch_macos_linux.sh`
   - Windows : double-cliquer sur `launch_windows.bat`
   - ou, dans tous les cas : `python app.py`
4. Ouvrir **http://127.0.0.1:8765** dans un navigateur.

Options :
- `VIRTUAL_LAB_PORT=8800 python app.py` : utiliser un autre port.
- `VIRTUAL_LAB_DB=/chemin/historique.sqlite3 python app.py` : utiliser une autre base d'historique.

Le serveur n'écoute que sur l'ordinateur local et refuse les requêtes venant d'autres sites (v4.8). **Ne pas l'exposer sur Internet.**

## 2. Vos données
- L'historique est stocké dans `virtual_lab_history.sqlite3`, à côté de `app.py`. **Ce fichier n'est jamais inclus dans une archive de version.**
- La paillasse est enregistrée dans le navigateur (bouton « Enregistrer ») et peut être exportée et importée en JSON.
- Mise à jour depuis une version antérieure : copier votre `virtual_lab_history.sqlite3` dans le nouveau dossier. Au premier lancement, la base est migrée et **une copie de sauvegarde est créée automatiquement** (`virtual_lab_history.sqlite3.backup-schema-1-<date>`). Vous pouvez aussi utiliser « Exporter tout l'historique » puis « Importer des dossiers ».

## 3. Vérifier l'archive
Chaque archive contient `MANIFEST.sha256`. Depuis le dossier décompressé :
- macOS / Linux : `shasum -a 256 -c MANIFEST.sha256` (ou `sha256sum -c MANIFEST.sha256`)
- tous systèmes : `python scripts/verify_manifest.py`

## 4. Refaire la validation complète (facultatif, pour les développeurs)
```bash
python -m venv .venv
. .venv/bin/activate            # Windows : .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/run_validation.py        # tous les tests + matrice générée
python scripts/check_syntax.py          # compilation Python + syntaxe JavaScript (si Node.js est présent)
python scripts/accessibility_audit.py   # audit axe-core
```
Sans Playwright, les tests navigateur sont signalés **ignorés** dans la matrice, jamais réussis.
