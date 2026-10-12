# Démarrage rapide — Virtual Lab Platform v1.8

## 1. Lancer le logiciel sur Mac

1. Décompresse `virtual_lab_platform_v1_8.zip`.
2. Ouvre **Terminal** (Applications → Utilitaires → Terminal).
3. Tape `cd `, ajoute un espace, glisse le dossier `virtual_lab_platform` dans Terminal puis appuie sur Entrée.
4. Lance le serveur local :

   ```bash
   sh launch_macos_linux.sh
   ```

5. Ouvre Safari ou Chrome à l'adresse http://127.0.0.1:8765.
6. Pour arrêter le logiciel, reviens au Terminal et appuie sur `Ctrl+C`.

Python 3.10 ou plus récent est requis. Aucune bibliothèque Python externe n'est nécessaire.

## 2. Construire une expérience dans le laboratoire

1. Va à **Virtual laboratory · build an experiment**.
2. Choisis un workflow et donne un nom à l'expérience.
3. Coche les échantillons/composants et les équipements nécessaires.
4. Les éléments sélectionnés apparaissent sur le **Visual experiment bench**. Tu peux déplacer les cartes par glisser-déposer ou retirer un élément avec `Remove`.
5. Écris les étapes du protocole, une par ligne.
6. Clique sur **Validate setup** pour repérer certains éléments manquants ou paramètres incompatibles.
7. Clique sur **Run virtual experiment** pour exécuter le calcul disponible ou enregistrer un workflow qui n'a pas encore de moteur scientifique.
8. Exporte le dossier expérimental en JSON pour conserver la configuration et les résultats.

Le banc visuel organise les éléments mais n'est pas une simulation 3D physique. Les machines ne sont pas encore des jumeaux numériques validés.

## 3. Analyser un jeu de données CSV

1. Dans **Scientific data library · import**, sélectionne un fichier CSV.
2. Clique sur **Analyze selected CSV** avant de l'importer.
3. Consulte les valeurs manquantes, doublons, types de colonnes, statistiques numériques, quartiles, aperçu et corrélations exploratoires.
4. Clique sur **Export analysis JSON** pour conserver l'analyse.
5. Tu peux ensuite importer le CSV dans la bibliothèque locale pour le référencer.

Les corrélations ne démontrent pas une causalité. L'analyse descriptive ne valide pas la qualité scientifique ou la provenance des données.

## 4. Exécuter un modèle SBML et tester un paramètre

1. Le modèle synthétique A→B fourni est disponible par défaut dans la liste SBML.
2. Lance **Run SBML simulation** pour exécuter le modèle compatible avec le sous-ensemble SBML pris en charge.
3. Dans **Explore a model parameter**, utilise `k` comme identifiant de paramètre pour le modèle de démonstration.
4. Modifie les valeurs, par exemple `0.05,0.1,0.2,0.4,0.8`, puis clique sur **Run parameter sweep**.
5. Compare les quantités finales et exporte le dossier JSON.

Ce modèle est un exemple technique synthétique, pas une découverte scientifique. Le moteur ne prend en charge qu'un sous-ensemble de SBML et rejette les fonctions non supportées.

## 5. Ce que cette version fait et ne fait pas

**Déjà disponible :**
- catalogue d'échantillons, composants, machines et workflows;
- contrôle de certaines exigences matérielles et capacités;
- calcul de dilution et courbe enzymatique illustrative;
- modèles SIR, diffusion thermique 1D et cinétique enzymatique, maintenant connectés aux workflows du laboratoire;
- import local de modèles SBML et jeux CSV avec empreinte SHA-256;
- exécution SBML partielle, balayage d'un paramètre global;
- analyse descriptive des CSV, comparaison de données de référence, sensibilité, incertitude et historique;
- graphiques de résultats, export JSON et historique SQLite des expériences du laboratoire; bibliothèque de connaissances scientifiques.

**Pas encore disponible :**
- scène de laboratoire 3D et physique des équipements;
- moteur scientifique validé pour chaque discipline;
- modèles cliniques validés du cancer, d'Alzheimer ou d'autres maladies;
- moteur complet de chimie, d'optique, de PCR, de matériaux ou de formulation cosmétique;
- import automatique de bases scientifiques en ligne;
- orchestration par IA.

Un test logiciel réussi confirme le comportement du code testé, pas la validité scientifique d'un modèle. Ne l'utilise pas pour des décisions médicales, cliniques, de sécurité ou réglementaires.

## Nouveautés v1.3

- Le workflow de chauffage utilise le moteur numérique de diffusion thermique 1D.
- Le workflow SIR utilise le moteur de dynamique de population existant.
- Les sorties numériques sont visualisées par graphiques et tableaux génériques.
- Les exécutions du laboratoire sont enregistrées dans l’historique SQLite local avec empreinte de configuration.


## 6. Éditeur de protocole structuré (v1.4)

Dans **Virtual laboratory · build an experiment** :
1. Chaque étape dispose d'une action, d'un équipement sélectionné, d'une durée prévue et d'un type de mesure éventuel.
2. Utilise **Add step** pour ajouter des étapes. Le schéma visuel montre les dépendances séquentielles.
3. Dans **Material transfers between steps**, choisis un composant sélectionné, l'étape de départ et d'arrivée, une quantité et une unité. L'unité doit correspondre au catalogue.
4. Associe un type de mesure à l'étape et sélectionne un instrument compatible, par exemple le thermomètre pour une mesure de température.
5. Clique sur **Validate protocol graph** pour vérifier les références, cycles, unités, instruments et dépendances.
6. **Run virtual experiment** exécute le calcul numérique disponible et enregistre en plus une trace du protocole. **Record protocol run** enregistre uniquement la trace du protocole.
7. Exporte le dossier JSON. Les mesures non calculées restent nulles; le logiciel ne fabrique pas de valeurs.

Les durées sont des estimations saisies par l'utilisateur. La trace est une représentation reproductible du protocole, pas l'actionnement physique d'une machine. Les caractéristiques du catalogue ne remplacent ni les manuels constructeur, ni les procédures de sécurité, ni une validation métrologique.


## Interface v1.8

La nouvelle paillasse interactive est la page d’accueil. Choisis une catégorie dans la bibliothèque, clique sur « Ajouter » (ou glisse l’objet sur la paillasse), sélectionne-le pour modifier ses paramètres et utilise « Analyser l’expérience ». Pour tester le bilan de dilution, ajoute « Solution mère » et « Eau (solvant) », puis modifie leurs volumes et la concentration de la solution mère. Les autres objets sont principalement descriptifs à ce stade; les outils de recherche avancés restent accessibles en bas de la paillasse. Le sélecteur de langue couvre la nouvelle interface, pas encore tous les écrans historiques.
