# Démarrage rapide — v4.2

1. Installer Python 3.10 ou plus récent. Aucune bibliothèque n'est nécessaire pour l'application.
2. Mac/Linux : `sh launch_macos_linux.sh`. Windows : double-cliquer sur `launch_windows.bat`. Ou bien : `python app.py`.
3. Ouvrir http://127.0.0.1:8765.
4. Paillasse → onglet électricité → ajouter « Source de tension CC », « Résistance » et « Masse ».
5. Sélectionner chaque composant et saisir sa valeur dans Propriétés (par exemple 9 V et 1000 Ω).
6. Cliquer une borne, puis une autre, pour poser un fil : + → A, B → GND, − → GND.
7. Cliquer « Résoudre le circuit CC câblé » : courant 9 mA, dossier enregistré.
8. Dans « Saved experiments » : « Verify integrity », puis « Replay circuit ».

Options : `VIRTUAL_LAB_PORT=8800 python app.py` pour changer de port ; `VIRTUAL_LAB_DB=/chemin/base.sqlite3` pour utiliser une autre base.
