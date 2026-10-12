# Notes de version — Virtual Lab Platform v2.2

### Réparations d’interface
- Le code de la paillasse est isolé dans son propre bloc script afin qu’une exception d’un ancien écran ne bloque pas l’enregistrement des gestionnaires d’événements de la paillasse.
- Les catégories de la bibliothèque ont maintenant une entrée Électricité & électronique.
- Ajout d’éléments de catalogue pour source de tension, résistance, condensateur, inductance, diode et transistor, avec avertissements honnêtes sur les composants non résolus.
- Le bouton d’accès aux outils avancés cible explicitement le panneau de recherche.

### Validation
- 97 tests Python hérités réussis.
- Compilation Python réussie.
- Les blocs JavaScript passent `node --check`.
- L’archive est empaquetée sans caches Python.
- Pas de validation manuelle dans Safari disponible depuis cet environnement.
