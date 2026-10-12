# Notes de version — Virtual Lab Platform v5.7

**Objectif (feuille de route) :** attribuer un niveau de maturité à chaque modèle (maquette conceptuelle, modèle calculable, modèle vérifié, modèle validé sur données) ; exposer pour chacun ses équations, hypothèses, limites, jeux de référence et état de validation ; retirer les affirmations non justifiées par le code.

## Critères d'acceptation et résultat
| Critère | Résultat |
|---|---|
| 4 niveaux définis | `maturity.py` : définitions explicites. « Vérifié » exige **au moins une référence indépendante** : solution analytique évaluée à part, solveur indépendant, benchmark publié, quantité conservée ou propriété statistique. « Validé sur données » exige un **jeu de données sourcé**. |
| Niveaux vérifiés par la machine | `check_claims()` refuse tout « vérifié » qui ne cite pas un test **existant** (contrôlé par analyse du code des tests) et tout « validé sur données » sans source. **La validation générée échoue si un test cité comme preuve n'a pas réussi** (ligne « Preuves de maturité » dans la matrice). |
| Vérification des 10 modèles du catalogue | `tests/test_v57_model_verification.py` (16 tests). Chaque modèle est comparé à une référence qui ne réutilise pas son code : intégration adaptative indépendante (SIR, logistique, premier ordre, Lotka–Volterra, RC/RL), série de Fourier exacte (diffusion thermique, écart observé 0,0095 °C), intégrale première conservée (Lotka–Volterra), intervalle analytique entre potentiels d'action (neurone LIF), arithmétique complexe indépendante (RLC en régime sinusoïdal), propriétés exactes (Michaelis–Menten, Arrhenius). |
| Résultat | **21 modèles vérifiés, 1 calculable** (concepteur d'expériences), **33 maquettes conceptuelles** (entrées du catalogue sans solveur) et **0 validé sur données** : aucune comparaison avec des données réelles n'existe encore. |
| Exposition | Chaque contrat porte `maturity` (niveau, preuves avec type, test, description et tolérance). Routes `GET /api/maturity` (définitions, comptes, détail) et `/api/models` (avec la maturité). **Badge de maturité** sur chaque modèle du catalogue de l'interface, avec les preuves en info-bulle. Les équations, hypothèses et domaines de validité sont obligatoires pour tout modèle vérifié (test). |
| Affirmations corrigées | `/api/version` annonçait « 30 modèles L0 » alors que le code en contient **33**. C'est corrigé, et un test recalcule désormais ces chiffres depuis le code. Les contrats `workbench_dc_circuit` et `series_rlc_frequency_sweep` n'exposaient pas leurs équations : c'est fait. L'audit des textes de l'interface et des bibliothèques n'a pas trouvé d'autre affirmation de validation injustifiée. |

## Résultats chiffrés (y compris défavorables)
- Le modèle SIR (Euler explicite) a, au pas par défaut de 0,1 jour, une erreur de **0,31 %** sur le pic épidémique (0,03 % à 0,01 jour). Ce chiffre figure dans la preuve affichée.
- La diffusion thermique (schéma explicite FTCS, 41 nœuds) s'écarte de la solution exacte d'au plus 0,0095 °C.

## Tests
`tests/test_v57_model_verification.py` (16), `tests/test_v57_maturity.py` (9) et un test navigateur (badges du catalogue).

## Limites
- **« Vérifié » signifie que le calcul est correct pour les équations du modèle**, et non que le modèle décrit fidèlement la réalité. Aucun modèle n'est validé sur des données expérimentales : c'est l'objet du jalon C (données) et de la v7.3 (données publiques).
- Les 33 entrées « maquette conceptuelle » ne calculent rien. Elles restent dans le catalogue pour décrire les domaines visés.
