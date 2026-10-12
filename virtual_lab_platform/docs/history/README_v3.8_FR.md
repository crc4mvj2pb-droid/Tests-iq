# Virtual Lab Platform v3.8

Virtual Lab Platform est un prototype local de laboratoire scientifique numérique. Il combine un espace de travail multidisciplinaire, des outils de calcul, des solveurs ciblés et une bibliothèque de connaissances dont le niveau de validation doit rester explicite.

## Changements v3.8

- Indicateur visible de connexion à l'API locale et message d'aide lorsque le serveur n'est pas accessible.
- Instructions explicites pour démarrer via `python app.py` et éviter l'ouverture directe du fichier HTML.
- Action **Restaurer la sauvegarde** avec confirmation avant de remplacer un travail en cours.
- Messages d'erreur visibles en cas d'échec de sauvegarde ou de restauration.
- Validation plus stricte des données restaurées et restauration des connexions de paillasse.
- Tests de non-régression pour l'état de connexion, la sauvegarde, les identifiants HTML et la version.

## Fonctionnalités conservées

- Bibliothèque multidisciplinaire et paillasse interactive, avec catégorie **Électricité & électronique**.
- Solveur de circuits résistifs CC par analyse nodale et connexions entre bornes.
- Cinétique chimique générique A → B → C par intégration RK4.
- Calcul stœchiométrique serveur avec identification du réactif limitant et contrôle de bilan atomique lorsque les formules sont disponibles.
- Instruments virtuels : lecture simulée reproductible, correction d'étalonnage, résolution d'affichage et budget d'incertitude.
- Outils de recherche exploratoire, analyse de données, import local de SBML/CSV, provenance et historique local.

## Lancement

```bash
python app.py
```

Puis ouvrir http://127.0.0.1:8765. L'environnement est conçu pour un usage local; ne l'exposez pas directement à Internet.

## Limites scientifiques

Les tests logiciels vérifient le comportement du code et ne constituent pas une validation expérimentale indépendante. Les instruments sont simulés, leurs incertitudes sont illustratives et les modèles ne couvrent pas toutes les conditions physiques ou chimiques réelles. Les éléments du catalogue peuvent être descriptifs ou conceptuels sans être des simulateurs exécutables.
