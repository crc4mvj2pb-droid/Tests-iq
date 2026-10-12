# Brief pour Claude — audit indépendant de Virtual Lab Platform v4.1

Tu reçois le code source de Virtual Lab Platform v4.1, une application locale Python + interface HTML/JavaScript de laboratoire scientifique virtuel.

## Ta mission — audit avant modification

Ne réécris pas le projet immédiatement. Commence par auditer indépendamment ce qui existe réellement, car les versions précédentes peuvent contenir des tests automatisés sans validation complète du navigateur.

### 1. Comprendre le projet
- Lis `README.md`, `README_v4.1_FR.md`, `DEMARRAGE_RAPIDE_v4.1_FR.md`, `RELEASE_NOTES_v4.1_FR.md` et `TEST_RESULTS_v4.1.txt`.
- Examine `app.py`, `static/index.html`, `workbench_circuit.py`, `electrical_circuits.py`, `experiment_lifecycle.py`, `history.py`, `virtual_instruments.py`, `reaction_stoichiometry.py`, `chemical_kinetics.py`, `protocol_engine.py` et les tests correspondants.
- Identifie le véritable point d'entrée, les dépendances, les API, le stockage, les fonctionnalités intégrées et les fonctionnalités seulement partielles.

### 2. Vérifier les affirmations
- Lance la suite de tests et note la commande, la version de Python et le résultat exact.
- Lance la compilation Python et vérifie la syntaxe JS.
- Si l'environnement le permet, lance le serveur et teste les endpoints.
- Si tu peux utiliser un navigateur, teste réellement l'interface. Sinon, écris clairement que ce n'est pas testé.
- Reproduis le circuit de référence 9 V / 1 kΩ, puis vérifie sauvegarde, empreinte, rejeu et comparaison des résultats.
- Recherche bugs, risques de perte de données, erreurs de validation, incohérences d'unités, vulnérabilités d'import et affirmations scientifiques exagérées.

### 3. Produire un audit utile
Donne :
1. Résumé exécutif honnête.
2. Carte de l'architecture et du flux interface → API → moteur → base de données → affichage.
3. Tableau des problèmes avec gravité (bloquant/majeur/mineur), fichier/fonction, preuve, conséquence et correctif recommandé.
4. Liste des fonctions opérationnelles, partielles, simulées et non vérifiées.
5. Tests exécutés avec résultat exact, et tests impossibles à exécuter.
6. Les 5 corrections qui apporteraient le plus de fiabilité.
7. Une proposition pour la v4.2, limitée à un objectif testable, avec critères d'acceptation.

### 4. Contraintes
- N'invente pas des tests, des résultats, des captures ou des fonctions.
- Ne dis pas « entièrement fonctionnel » sans tests de bout en bout.
- Ne remplace pas un vrai moteur scientifique par une animation ou des valeurs codées en dur.
- Ne supprime pas de modules ni de tests sans justifier et signaler la régression.
- Ne fais pas une refonte complète juste pour préférer une architecture différente.
- Conserve les versions précédentes et les données.
- Les sorties calculées/simulées ne sont pas des mesures expérimentales réelles.
- Le solveur de paillasse actuel est limité aux circuits CC résistifs décrits dans la documentation ; il ne faut pas prétendre qu'il s'agit de SPICE.
- Ne passe pas directement à l'IA autonome : la priorité est de fiabiliser les moteurs et les parcours.

### 5. Comment travailler ensuite avec ChatGPT
Après l'audit, ne développe pas encore une deuxième branche complète. Compare tes conclusions avec celles de ChatGPT et propose une seule prochaine étape. La meilleure approche est celle qui fournit le plus de preuves, réduit les bugs et préserve le projet — pas celle qui annonce le plus de fonctionnalités.

Le plan général est fourni dans `ROADMAP_VIRTUAL_LAB_PLATFORM_FR.md`.
