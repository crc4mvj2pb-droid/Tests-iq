# Virtual Lab Platform v2.7

Laboratoire scientifique local et multidisciplinaire. Cette version poursuit le prototype v2.6 en rendant le câblage graphique des circuits CC calculable par le moteur électrique.

## Démarrer sur Mac ou Linux

1. Décompresser l'archive.
2. Ouvrir Terminal dans le dossier du projet.
3. Lancer `sh launch_macos_linux.sh`.
4. Ouvrir `http://127.0.0.1:8765` dans Safari ou un autre navigateur.

Python 3.10 ou plus récent est requis. Aucun paquet Python tiers n'est requis pour le démarrage. Le serveur écoute uniquement sur l'interface locale.

## Nouveauté principale : circuit câblé

Le panneau Électricité & électronique permet de placer une source CC, des résistances, des fils et une masse. Chaque composant affiche des bornes : `+`/`−`, `A`/`B` ou `GND`.

Pour relier deux bornes :

1. Ajouter une source CC, une ou plusieurs résistances et une masse.
2. Cliquer sur une borne du premier composant, puis sur la borne du second. On peut aussi sélectionner le composant, choisir sa borne et utiliser le sélecteur de borne cible dans Propriétés.
3. Répéter jusqu'à obtenir un circuit fermé. Le négatif de la source doit être relié à GND.
4. Modifier la tension de la source (V) et les résistances (Ω) dans Propriétés.
5. Cliquer sur **Résoudre le circuit CC câblé**.

Le logiciel convertit les connexions en nœuds électriques puis exécute une analyse nodale. Les résultats incluent les tensions des nœuds, courants, chutes de tension, puissances dissipées, résistance équivalente et contrôles de Kirchhoff/bilan de puissance. La configuration et les câbles sont enregistrés et exportables en JSON.

### Modèle électrique et limites

- Pris en charge par le solveur graphique : une source idéale de tension continue, un nœud de référence, des fils idéaux et des résistances linéaires.
- Le solveur rejette les bornes non connectées, les courts-circuits de source et les composants raccordés dont le modèle n'est pas disponible.
- Condensateurs, inductances, interrupteurs, diodes, transistors, sources alternatives et comportements électromécaniques ne sont pas encore intégrés à ce solveur graphique. Des modèles RC/RL et RLC analytiques séparés existent, mais ne sont pas encore automatiquement construits à partir de ce câblage.
- Ce moteur n'est pas un remplacement de SPICE et ne constitue pas une garantie de sécurité pour du matériel réel.

## Fonctionnalités conservées

- Paillasse multilingue et bibliothèque scientifique catégorisée.
- Dépôt d'échantillons dans les machines et opérations explicitement prises en charge.
- Bilans stœchiométriques pour les réactions listées.
- Modèles de recherche, incertitudes, analyses de données CSV, import SBML partiel et exports de dossiers JSON.
- Historique et outils de traçabilité locaux.

La bibliothèque est extensible, mais ne représente pas la totalité des connaissances humaines. Une entrée de catalogue n'implique pas qu'une simulation scientifique est implémentée.

## Vérifications de cette version

- 112 tests réussis avec `pytest -q`; 101 tests réussis avec `python -m unittest discover -s tests -q`.
- Vérification de syntaxe JavaScript avec `node --check`.
- Le test interactif navigateur est documenté séparément; les tests automatisés ne remplacent pas une validation scientifique indépendante.
