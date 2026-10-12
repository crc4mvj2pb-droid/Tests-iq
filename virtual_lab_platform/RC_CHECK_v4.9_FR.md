# Contrôle de version candidate — Virtual Lab Platform v4.9

Contrôles exécutés le 12 octobre 2026 sur l'archive `virtual_lab_platform_v4.9.zip`, **décompressée dans un dossier vide**. Seuls les résultats réellement observés sont indiqués.

| # | Contrôle | Commande / méthode | Résultat observé |
|---|---|---|---|
| A | Intégrité de l'archive | `sha256sum -c MANIFEST.sha256` et `python scripts/verify_manifest.py` (Python 3.11) | 224/224 fichiers vérifiés par les deux méthodes ; aucune base SQLite ni cache dans l'archive |
| B | Démarrage sans aucune bibliothèque tierce | `sh launch_macos_linux.sh` (Python 3.13 système, `PYTHONNOUSERSITE=1`), port 8799 et base temporaire | `/api/health` → `ok`, version 4.9 ; circuit 9 V / 1 kΩ → 0,009 A ; dossier n° 1 vérifié au niveau `full` ; page servie (200) |
| C | Compatibilité Python | environnements neufs (`uv venv`) avec **pytest seulement** | 3.10.20, 3.11.17, 3.12.3, 3.13.16 et 3.14.6 : **569 réussis** sur chaque version. Les 31 tests navigateur sont **ignorés** (Playwright absent) et chacun est signalé avec sa raison dans la matrice (« impossible à lancer ») |
| D | Environnement de développement neuf | `uv venv -p 3.13` + `pip install -r requirements-dev.txt`, puis `scripts/run_validation.py`, `scripts/check_syntax.py` et `scripts/accessibility_audit.py` | **600 réussis, 0 échec, 0 ignoré** ; 79 fichiers Python compilés ; 3 blocs JavaScript valides ; 0 violation axe-core |

## Défauts trouvés pendant ce contrôle et corrigés
- Le lanceur macOS/Linux affichait toujours le port 8765, même quand `VIRTUAL_LAB_PORT` en demandait un autre.
- Sans Playwright, les 31 tests navigateur apparaissaient comme un seul test ignoré, avec une raison vague. Ils sont maintenant ignorés un par un, avec une raison explicite.

## Non contrôlé ici
- **Windows** (`launch_windows.bat`) et **macOS** : aucun de ces systèmes n'était disponible.
- **Safari et Firefox** : seul Chromium (Playwright 1.56, Chromium 141) a été utilisé.
- Lecteur d'écran réel.

## Re-vérification de l'archive finale
Les contrôles A à D ont porté sur une première archive (224 fichiers). Après l'ajout de ces documents et des deux corrections ci-dessus, l'archive finale (228 fichiers) a été décompressée dans un nouveau dossier vide. Résultats :
- `sha256sum -c MANIFEST.sha256` : tous les fichiers sont conformes ;
- environnement de développement neuf : **600 réussis, 0 échec, 0 ignoré** ;
- Python 3.10 sans Playwright : **569 réussis, 31 ignorés**, chacun avec sa raison.

Seule différence avec l'archive publiée : l'ajout de ce paragraphe dans `RC_CHECK_v4.9_FR.md`. Son manifeste a été revérifié.
