# Virtual Lab Platform v4.0 — démarrage rapide

## 1. Prérequis
- Python 3.11+ recommandé.
- Aucun compte ni service cloud nécessaire.
- Le serveur est prévu pour un usage local uniquement.

## 2. Lancer sous Windows
1. Décompressez `virtual_lab_platform_v4_0.zip` dans un dossier.
2. Ouvrez ce dossier dans l'Explorateur de fichiers.
3. Cliquez dans la barre d'adresse, tapez `cmd`, puis Entrée.
4. Lancez `python app.py`.
5. Ouvrez `http://127.0.0.1:8765` dans votre navigateur.

Si `python` n'est pas reconnu, installez Python depuis python.org en cochant l'option d'ajout au PATH.

## 3. Exécuter une expérience de circuit
1. Ouvrez la paillasse virtuelle et la catégorie « Électricité & électronique ».
2. Ajoutez une source CC, une masse et une ou plusieurs résistances.
3. Sélectionnez chaque composant et reliez ses bornes via le panneau de propriétés.
4. Saisissez une question ou un nom dans « Protocole de travail ».
5. Cliquez sur « Résoudre le circuit CC câblé ».
6. Examinez les tensions, courants, puissances, vérifications KCL et bilan de puissance.
7. Vérifiez le numéro de dossier et le début de l'empreinte SHA-256 affichés.
8. Ouvrez « Saved experiment history » et actualisez si nécessaire pour retrouver le dossier, puis exportez le JSON depuis le dossier enregistré.

## 4. Ce que v4.0 conserve
Chaque exécution du solveur de circuit de la paillasse est sauvegardée dans `virtual_lab_history.sqlite3` dans le dossier du projet. Le dossier contient la configuration (composants et câbles), les résultats numériques, les hypothèses, les limites, un état explicite de calcul simulé et une empreinte SHA-256 de la configuration canonique.

Les fichiers de la paillasse enregistrés via le bouton « Enregistrer la paillasse » restent une sauvegarde de l'espace de travail dans le navigateur. Ce mécanisme est distinct de l'historique SQLite des exécutions.

## 5. Limites scientifiques
Le solveur de paillasse traite les réseaux résistifs en régime continu avec source idéale et câbles idéaux. Il ne remplace pas SPICE et ne prend pas en charge les composants non linéaires ni les effets transitoires dans ce solveur. Les résultats sont des calculs simulés, pas des mesures physiques.

## 6. Arrêter
Dans le terminal où `python app.py` tourne, utilisez `Ctrl+C`.

Le serveur écoute uniquement sur `127.0.0.1`. Ne le publiez pas directement sur Internet.
