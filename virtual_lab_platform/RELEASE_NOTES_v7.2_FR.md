# Notes de version — Virtual Lab Platform v7.2

**Objectif (feuille de route) :**
- étendre progressivement les équilibres ou la thermodynamique, avec des données sourcées ;
- définir clairement les hypothèses et les domaines de validité.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Modèle limité et exact | `acid_base.py` (contrats `aqueous_acid_base` et `aqueous_titration`) traite les équilibres acide–base en solution diluée à 25 °C. Il couvre les acides mono- et polyprotiques, ainsi que les acides et bases forts. Il résout le **bilan de charges exact** par dichotomie, sans approximation de Henderson–Hasselbalch ; celle-ci n'est fournie qu'à titre de comparaison. |
| Données sourcées | Le catalogue gagne le jeu `pka_aqueous_25c` (nature « référence », source CRC Handbook, 97e édition) : acides acétique, formique et benzoïque, ammonium, phosphorique, carbonique, citrique. Ce jeu est **étiqueté « approché »**. La source indique honnêtement que les valeurs sont celles couramment reproduites et que le manuel lui-même n'a pas été consulté ici. Il est protégé par le verrou de version. |
| Vérification indépendante | Acide faible : comparé à la racine de l'**équation cubique exacte**, obtenue par une méthode de Newton écrite à part, pour 0,1, 1e-3 et 1e-6 mol/L (écart < 1e-9 pH). Acide fort, autoprotolyse comprise : formule quadratique exacte. Les bilans de charges et de matière sont respectés à 1e-12 dans un mélange phosphate, ammonium, acide et base forts. Titrage : volume d'équivalence exact, pH à la demi-équivalence ≈ pKa, pH à l'équivalence conforme à la formule de la base conjuguée, courbe monotone. Situations de manuel retrouvées : acide acétique 0,1 mol/L à pH 2,88 ; NH₄Cl 0,1 mol/L à pH 5,12 ; H₂PO₄⁻ à pH ≈ (pKa1 + pKa2)/2. |
| Domaine de validité explicite | Hypothèses : solution idéale (activités égales aux concentrations), 25 °C, pKw = 14,00 arrondi. Exclusions : coefficients d'activité, précipitation, complexation, CO₂. Nouveau domaine « Physicochimie des solutions » avec son graphique de titrage. |
| Banc d'essai | Deux cas ajoutés (tampon équimolaire, base forte). **Incident consigné** : pour la base forte, mon estimation a priori négligeait l'autoprotolyse de l'eau ; le banc a mesuré un écart de 4,3e-9 en pH, au-delà de la tolérance de 1e-9. La référence inclut désormais l'eau exactement, **tolérance inchangée**. 39 cas en tout. |
| Collision de noms évitée | Le catalogue contenait une maquette conceptuelle `acid_base_equilibrium`. Le modèle calculable s'appelle donc `aqueous_acid_base`, et la description de la maquette renvoie désormais vers lui. |

## Tests
`tests/test_v72_acid_base.py` : 12 tests. Une première validation a échoué : le test navigateur des domaines comptait 7 cartes en dur, alors que la v7.2 ajoute un 8e domaine. Il compte désormais les domaines déclarés dans le code. Le test v6.0 « jeux livrés » accepte désormais aussi la nature « référence », source toujours exigée.

## Limites
- Au-delà d'une force ionique d'environ 0,1 mol/L, l'écart dû aux activités peut atteindre plusieurs centièmes de pH ou plus.
- Les pKa sont des valeurs approchées, à recouper avec l'édition consultée du manuel avant tout usage de recherche.
