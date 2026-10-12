# Virtual Lab Platform v2.1

Laboratoire de simulation scientifique local, avec paillasse interactive, bibliothèque multidisciplinaire en développement, outils de recherche et trois nouveaux modèles électriques avancés.

## Lancer sur macOS
1. Décompresser l'archive.
2. Ouvrir Terminal dans le dossier du projet.
3. Lancer `sh launch_macos_linux.sh`.
4. Ouvrir `http://127.0.0.1:8765`.
5. Laisser le Terminal ouvert. Arrêt : `Ctrl+C`.

Python 3.10+ requis. L'application est locale et ne nécessite pas de connexion Internet pour ses fonctions intégrées.

## Nouveaux modèles électriques
- **RC/RL transitoire** : source échelon idéale, résistance et capacité (RC) ou inductance (RL) constantes, conditions initiales explicites.
- **RLC série CA** : régime sinusoïdal établi, valeurs efficaces, impédance et puissances.
- **Balayage fréquentiel** : échantillonnage logarithmique pour inspecter la réponse du circuit.

Les résultats et les hypothèses sont affichés dans l'interface et peuvent être exportés en JSON.

## Limites
Le solveur de réseau CC traite les résistances idéales par analyse nodale. Les nouveaux modèles transitoires sont analytiques et limités aux circuits RC/RL du premier ordre ; l'analyse CA est limitée au RLC série linéaire. Ce n'est pas un remplacement de SPICE, et aucune validation indépendante de matériel n'est revendiquée. Pour tout montage réel, vérifier les composants, les puissances, les tensions admissibles et les résultats avec des outils d'ingénierie adaptés.

## Tests
`python -m pytest -q` depuis le dossier du projet. La suite actuelle contient 97 tests automatisés.

Consulter `RELEASE_NOTES_v2.1_FR.md` pour le détail des changements.
