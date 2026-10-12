# Virtual Lab Platform v1.8 — interface paillasse

## Livré dans cette version

- Nouvelle interface d'accueil claire organisée autour d'une paillasse scientifique.
- Bibliothèque à catégories : équipement, substances, molécules, biologie/ADN, physique et analyse.
- Ajout par clic ou glisser-déposer, sélection, retrait, modification des propriétés disponibles.
- Objets de paillasse conservés localement dans le navigateur et exportables en JSON.
- Sélecteur de langue d'interface : français, anglais, néerlandais et espagnol.
- Calcul de bilan de dilution idéal lorsque l'utilisateur place une solution mère et de l'eau : volumes et concentrations sont modifiables; hypothèses et limites sont affichées.
- Accès conservé à l'ancien environnement de recherche avancé et à ses outils existants.
- Fiche explicite pour l'assistant scientifique : l'IA n'est pas encore connectée et aucune réponse artificielle n'est simulée.

## Limites connues

- Les icônes moléculaires, ADN, protéines et cellules sont des représentations conceptuelles, pas des modèles 3D atomistiques.
- La plupart des objets de la nouvelle bibliothèque sont descriptifs. Seul le bilan de dilution idéal de cette interface est directement calculé dans la paillasse; les autres workflows doivent être lancés dans les outils avancés lorsqu'ils sont compatibles.
- Le bilan de dilution ne modélise ni interactions chimiques, ni non-additivité des volumes, ni incertitudes instrumentales.
- Le changement de langue couvre l'interface de la nouvelle paillasse; tous les écrans historiques des outils avancés ne sont pas encore traduits.
- L'assistant IA scientifique est un emplacement d'interface seulement; aucun modèle d'IA n'est intégré.
- Aucun contrôle d'équipement physique ni validation expérimentale n'est fourni.

## Vérifications

- 87 tests Python existants réussis.
- Compilation Python et vérification de syntaxe JavaScript réussies.
- Lancement HTTP et vérification d'API réalisés localement avant publication.
