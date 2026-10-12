# Démarrer Virtual Lab Platform v1.6 sur Mac

1. Décompresse `virtual_lab_platform_v1_6.zip`.
2. Ouvre Terminal.
3. Tape `cd ` avec un espace, glisse le dossier extrait `virtual_lab_platform` dans Terminal, puis appuie sur Entrée.
4. Lance `sh launch_macos_linux.sh`.
5. Ouvre http://127.0.0.1:8765 dans Safari ou Chrome.
6. Pour arrêter le serveur : `Ctrl+C` dans Terminal.

Python 3.10 ou supérieur est requis. Le prototype n'a pas de dépendance Python externe.

Pour les instructions complètes sur le banc visuel, l'éditeur de protocole structuré, les transferts de matière, les plans de mesure, les incertitudes instrumentales et les effets d'équipement, l'analyse CSV et les balayages SBML, consulte `DEMARRAGE_RAPIDE_FR.md`.

## Confidentialité et limites
- L'application écoute uniquement sur `127.0.0.1`; elle n'est pas publiée sur Internet.
- Les expériences, fichiers importés et historique restent sur l'ordinateur.
- Les spécifications des équipements sont indicatives et ne sont pas des spécifications constructeur certifiées.
- Les modèles scientifiques sont de portée limitée et ne sont pas automatiquement validés par des essais réels.
- Ne pas utiliser pour des décisions médicales, cliniques, de sécurité, industrielles ou réglementaires.

La version 1.3 relie les workflows de chauffage des matériaux et de dynamique SIR à des solveurs numériques, affiche des graphiques de résultats et sauvegarde les exécutions du laboratoire dans l’historique SQLite local. Consulte `DEMARRAGE_RAPIDE_FR.md` pour le guide détaillé.
