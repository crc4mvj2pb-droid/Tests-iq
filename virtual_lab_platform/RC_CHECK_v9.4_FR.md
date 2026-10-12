# Contrôle final — Virtual Lab Platform v9.4

Contrôles exécutés le 12 octobre 2026 sur l'archive `virtual_lab_platform_v9.4.zip` publiée (489 fichiers), **décompressée dans un dossier vide**. Seuls les résultats réellement observés sont indiqués.

| # | Contrôle | Commande | Résultat observé |
|---|---|---|---|
| A | Intégrité de l'archive | `sha256sum -c MANIFEST.sha256` et `python3.11 -I scripts/verify_manifest.py` | 489/489 fichiers conformes avec les deux méthodes ; aucune base SQLite, sauvegarde ni journal dans l'archive |
| B | Installation, bibliothèque standard seule (`PYTHONNOUSERSITE=1`) | `python scripts/install_check.py` | **12/12 contrôles réussis** sous Python **3.10.20, 3.11.17, 3.12.3, 3.13.16 et 3.14.6**. Aucun fichier écrit dans le dossier d'installation |
| C | Suite de tests sans navigateur | environnements neufs (`uv venv`) avec **pytest seulement** | Python 3.10 et Python 3.14 : **1 131 réussis, 0 échec, 58 ignorés** (tests navigateur, Playwright absent, chacun avec sa raison) |
| D | Validation complète, navigateur compris | `scripts/run_validation.py` lors de la publication (Chromium, Playwright) | **1 189 réussis, 0 échec, 0 ignoré** ; 46/46 tests cités comme preuves de maturité réussis (`VALIDATION_MATRIX_v9.4.md`) ; banc d'essai 43/43 ; évaluation de l'assistant 36/39 avec 0 % d'hallucination ; audit axe-core sans violation |

## Non contrôlé ici
- **Windows** (`launch_windows.bat`) et **macOS** : non disponibles dans cet environnement.
- **Safari et Firefox** : seul Chromium a été utilisé.
- Lecteur d'écran réel.

## Re-vérification
Après l'ajout de ce document, l'archive a été reconstruite et vérifiée de nouveau dans un dossier vide (manifeste et contrôle d'installation). Seule différence avec l'archive contrôlée ci-dessus : ce fichier.
