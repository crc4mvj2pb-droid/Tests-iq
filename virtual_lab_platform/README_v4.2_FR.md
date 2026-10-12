# Virtual Lab Platform v4.2

La v4.2 vérifie le parcours électrique dans un vrai navigateur et corrige les défauts trouvés par l'audit sur ce parcours, dont le lancement d'expérience du concepteur, qui ne fonctionnait pas.

## Lancer
`python app.py`, puis ouvrir http://127.0.0.1:8765 (voir `DEMARRAGE_RAPIDE_v4.2_FR.md`).

## Vérifier soi-même
```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/run_validation.py      # tests + matrice générée
```
Sans Playwright, les tests navigateur sont signalés comme **ignorés**, jamais comme réussis.

## Documents
- `RELEASE_NOTES_v4.2_FR.md` : changements et tests modifiés.
- `VALIDATION_MATRIX_v4.2.md` et `TEST_RESULTS_v4.2.txt` : résultats générés par la commande ci-dessus.
