# Notes de version — Virtual Lab Platform v7.4

**Objectif (feuille de route) :**
- commencer par des modèles mathématiques classiques et bien délimités ;
- ne pas présenter ces modèles comme des jumeaux complets du cerveau humain.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Modèles classiques | `neuro.py`. **Hodgkin–Huxley (1952)** : membrane de l'axone géant de calmar en potentiel imposé spatialement, convention moderne (repos à −65 mV), RK4 avec pas ≤ 0,05 ms ; la singularité apparente de α_n et α_m est traitée par sa limite. **FitzHugh–Nagumo (1961)** : réduction à deux variables sans dimension, avec équilibre et courants de Hopf analytiques. |
| Vérification indépendante | Une **réimplémentation séparée** des équations de Hodgkin–Huxley, à pas 4 fois plus fin, donne les mêmes instants de potentiels d'action à 0,02 ms près. Le **potentiel de repos** simulé coïncide à 1e-3 mV avec la racine de I_ion(V) = 0 calculée à part (−65,0 mV). Comportement connu de **classe II** (Hodgkin 1948) : silence à 2 µA/cm², décharge répétitive à plus de 40 Hz dès 6,5 µA/cm², fréquence croissante ensuite. FitzHugh–Nagumo : l'équilibre est une racine exacte, et la **perte de stabilité se produit au courant de Hopf analytique** (trace du jacobien nulle) : une petite perturbation s'amortit à I_H − 0,02 et croît à I_H + 0,02. |
| Résultat négatif documenté | Juste sous le courant de Hopf, une oscillation peut **persister** depuis une condition initiale éloignée (bistabilité). Le test de stabilité part donc de l'équilibre perturbé, ce qui est la définition de la stabilité linéaire, et ce comportement est signalé ici plutôt que masqué. |
| Pas de « jumeau du cerveau » | Chaque résultat de Hodgkin–Huxley rappelle : « Not a model of mammalian or human neurons, networks or brain function ». Le domaine « Neurosciences computationnelles » l'exclut explicitement. |
| Banc d'essai | Deux cas ajoutés : courant de Hopf supérieur (exact), et aucun potentiel d'action au repos. Le banc compte 41 cas. |

## Tests
`tests/test_v74_neuro.py` : 8 tests.

## Limites
- Paramètres de l'axone de calmar à 6,3 °C ; pas de propagation, de synapses ni de réseau.
- FitzHugh–Nagumo est qualitatif : ses unités sont arbitraires.
