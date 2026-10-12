# Virtual Lab Platform v3.0 — notes de version

## Fonctionnalité principale : cinétique dans l’interface
- Le moteur de cinétique chimique v2.8 est accessible depuis un nouveau panneau du laboratoire.
- Paramètres modifiables : concentrations initiales A/B, constante de vitesse, durée, pas d’intégration, température, énergie d’activation et température de référence.
- Affichage des concentrations finales, courbes SVG concentration-temps et tableau de valeurs.
- Export JSON des résultats.
- Le panneau appelle le moteur local `/api/chemistry/kinetics` : ce n’est pas un calcul fictif côté navigateur.

## Validation
- 117 tests automatisés réussis.
- Compilation Python et syntaxe JavaScript vérifiées.
- Test HTTP local réussi pour la santé, la version et le calcul cinétique.
- Exemple A → B comparé à la solution analytique du premier ordre.

## Limites connues
Le panneau de v3.0 expose un exemple générique A → B, et ne transforme pas encore automatiquement les objets et machines de la paillasse en réseau cinétique. Les paramètres doivent être fournis avec des unités cohérentes. Aucun modèle ne doit être considéré comme empiriquement validé sans comparaison à des données de référence.
