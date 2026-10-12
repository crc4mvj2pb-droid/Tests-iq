# Virtual Lab Platform v4.1 — démarrage rapide

## 1. Prérequis
- Python 3.11+ recommandé.
- Aucun compte ni service cloud nécessaire.
- Le serveur est prévu pour un usage local uniquement.

## 2. Lancer sous Windows
1. Décompressez `virtual_lab_platform_v4_1.zip` dans un dossier.
2. Ouvrez ce dossier dans l'Explorateur de fichiers.
3. Cliquez dans la barre d'adresse, tapez `cmd`, puis Entrée.
4. Lancez `python app.py`.
5. Ouvrez `http://127.0.0.1:8765` dans votre navigateur.

## 3. Créer et résoudre un circuit
1. Dans la paillasse, ajoutez une source CC, une masse et au moins une résistance.
2. Reliez les bornes via les commandes de connexion.
3. Cliquez sur « Résoudre le circuit CC câblé ».
4. Vérifiez tensions, courants, puissances, contrôles KCL et bilan de puissance.
5. Le calcul est sauvegardé automatiquement dans l'historique SQLite local.

## 4. Vérifier et rejouer une expérience
Dans « Saved experiment history » :
- **Open dossier** : consultez et exportez le dossier JSON enregistré.
- **Verify integrity** : recalcule l'empreinte SHA-256 de la configuration enregistrée et la compare à l'empreinte du dossier.
- **Replay circuit** : pour un dossier de circuit CC pris en charge, relance le solveur à partir des composants et câbles sauvegardés. Un nouveau dossier est créé avec le champ `replay_of` pointant vers l'expérience d'origine.

Une empreinte valide signifie que la configuration correspond à l'empreinte enregistrée ; elle ne garantit ni l'intégrité de chaque champ de résultat, ni la validité physique du modèle.

## 5. Limites
Le rejeu v4.1 ne concerne que les circuits de paillasse `electrical_workbench_dc`. Le solveur supporte une source CC idéale, une référence de masse, des fils idéaux et des résistances linéaires. Ce n'est pas SPICE et aucun instrument physique n'est piloté.
