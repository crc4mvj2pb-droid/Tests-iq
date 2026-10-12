# Notes de version — Virtual Lab Platform v3.1

- Ajout d'une seconde étape cinétique optionnelle B → C dans l'interface.
- Ajout de la concentration initiale C et de la constante k₂.
- Graphique, indicateurs et tableau générés automatiquement pour A/B ou A/B/C.
- Export JSON conservé pour le résultat complet.
- Réinitialisation de l'exemple rétablit l'état A → B.
- Version API mise à jour vers 3.1.
- Les 117 tests préexistants passent.

Limites connues : l'interface ne permet pas encore de créer un nombre arbitraire de réactions ; seule la chaîne A → B → C est exposée dans ce panneau. Les paramètres d'activation sont partagés entre les deux étapes. Aucune validation expérimentale indépendante n'est revendiquée.
