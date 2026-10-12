# Virtual Lab Platform v2.5 — catalogue enrichi et assemblage visuel

## Nouveautés
- Bibliothèque de démarrage étendue avec composants électriques supplémentaires (dont fils, interrupteur, masse, potentiomètre, instruments), matériel de laboratoire, espèces chimiques et objets conceptuels de biologie.
- Les objets électriques sont classés dans la catégorie « Électricité & électronique ».
- Un composant électrique peut être glissé sur un autre composant électrique de la zone de travail pour créer une liaison visuelle de type câble. Il est également possible de sélectionner un composant puis de choisir une cible dans le panneau de propriétés.
- Les liaisons sont dessinées par-dessus la zone de travail, supprimées lorsque l'un des composants est retiré et incluses dans les exports JSON.
- Un dessin de câble est fourni pour le fil de connexion.
- Le titre de l'application est mis à jour en v2.5.

## Limites importantes
Le catalogue est enrichi mais ne contient pas « toutes les molécules et toutes les machines connues » : l'univers scientifique est trop vaste et doit être intégré progressivement à partir de bases de données sourcées, sous réserve de licences et de qualité des données. Les entrées indiquent explicitement leurs limites.

Les liaisons dessinées sont pour le moment **visuelles** et ne sont pas automatiquement converties en netlist pour le solveur électrique. Le solveur CC existant reste configuré séparément. Les objets de biologie, ADN et molécules ne sont pas tous des modèles exécutables; certains sont des représentations conceptuelles. Aucune découverte ou validation expérimentale n'est revendiquée.

## Démarrage sur macOS
1. Décompresser l'archive dans un nouveau dossier.
2. Ouvrir Terminal dans ce dossier.
3. Exécuter `sh launch_macos_linux.sh`.
4. Ouvrir `http://127.0.0.1:8765` dans Safari.

## Tests réalisés dans l'environnement de développement
- 92 tests Python réussis.
- `compileall` Python réussi.
- Syntaxe du script principal de la page vérifiée avec `node --check`.
- Pas de test manuel de navigateur Safari effectué dans cet environnement.
