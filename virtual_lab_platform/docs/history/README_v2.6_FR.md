# Virtual Lab Platform v2.6

Laboratoire scientifique virtuel local : modèles numériques explicites, bibliothèques par discipline, paillasse interactive et dossier d’expérience exportable.

## Démarrage rapide sur Mac
1. Décompresser le ZIP.
2. Ouvrir le dossier décompressé dans Finder.
3. Ouvrir Terminal dans ce dossier et lancer `sh launch_macos_linux.sh`.
4. Ouvrir `http://127.0.0.1:8765` dans Safari.

Python 3.10 ou plus récent est requis. Aucun service cloud n’est nécessaire pour démarrer l’application.

## Interaction machine–échantillon
1. Choisir un équipement dans « Machines » et cliquer sur « Ajouter ».
2. Choisir une molécule, substance ou structure dans la bibliothèque.
3. Faire glisser l’objet sur la machine dans la zone de travail. Le badge indique qu’un contenu lui est associé.
4. Sélectionner la machine et utiliser « Exécuter la machine » dans le panneau Propriétés.
5. Pour un spectrophotomètre, renseigner ε, c et l dans les paramètres avancés de l’échantillon. Pour un pH-mètre, fournir le pH connu. Les valeurs non renseignées ne sont pas inventées.
6. Dans un réacteur, ajouter les espèces nécessaires puis choisir un bilan stœchiométrique proposé.

## Intégrité scientifique
Le logiciel distingue les calculs implémentés, les bilans idéaux et les représentations conceptuelles. Il ne prétend pas couvrir toutes les connaissances scientifiques humaines, ni simuler chaque machine ou chaque molécule. Voir `RELEASE_NOTES_v2.6_FR.md` pour les détails et limites.
