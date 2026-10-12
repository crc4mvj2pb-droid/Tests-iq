# Bilan du grand jalon D — « Élargissement disciplinaire par modules validés » (v7.0 → v7.6)

**Porte de sortie (feuille de route) :** chaque module ajouté a un périmètre limité, un banc d'essai et un statut de validation explicite.

| Domaine | Périmètre limité | Banc d'essai indépendant | Statut (dérivé, v7.0) |
|---|---|---|---|
| Circuits électriques linéaires | CC, RC/RL, RLC ; pas de non-linéaire ni de SPICE | 5 cas | vérifié |
| Cinétique et stœchiométrie | Action de masse, Arrhenius, bilans | 12 cas | vérifié |
| Physicochimie (v7.2) | Acide–base dilué à 25 °C, sans activités | 2 cas | vérifié |
| Thermique (v7.1) | 1D, une constante de temps (Bi < 0,1), murs composites | 5 cas | vérifié |
| Biologie quantitative (v7.3) | Michaelis–Menten, logistique, Lotka–Volterra | 3 cas | vérifié ; **1 modèle validé sur données** (Puromycine) |
| Neurosciences (v7.4) | Neurone unique ; aucun jumeau du cerveau | 4 cas | vérifié |
| Biomédical exploratoire (v7.5) | Modèles pédagogiques et exploratoires, aucun usage clinique | 6 cas | vérifié (aucune donnée clinique) |
| Processus environnementaux | Premier ordre, un compartiment | 1 cas | vérifié |

Les nombres de cas sont ceux de `GET /api/domains` (un cas compte pour le modèle qu'il exerce).

Ces règles sont **contrôlées par le code**, pas seulement décrites (`domains.problems()`, `plot_problems()`) :
- chaque contrat appartient à un seul domaine ;
- chaque domaine a des exclusions et au moins un cas de référence ;
- les graphiques déclarés correspondent aux résultats réels.

Le contrôle a révélé deux manques, aussitôt comblés : un domaine sans cas de référence (v7.0) et une collision de noms avec une maquette du catalogue (v7.2).

**Évaluation :** la porte de sortie est franchie.

Réserves :
- un seul modèle est validé sur données réelles ; tous les autres sont vérifiés mathématiquement ;
- les références bibliographiques et les pKa n'ont pas pu être relus dans leurs sources originales ici ;
- l'interface affiche les domaines, mais les nouveaux modèles (thermique, acide–base, neurones, biomédical) ne s'utilisent que par l'API standard (`POST /api/models/{id}/run`), par le panneau d'analyses et par les chaînes multi-modèles. Ils n'ont pas de formulaire dédié.

## Chiffres
- Validation générée : 1 088 tests passés en v7.6 (`VALIDATION_MATRIX_v7.6.md`).
- Banc indépendant : 43 cas.
- Maturité : 29 modèles vérifiés, 1 validé sur données, 1 calculable, 33 maquettes.
