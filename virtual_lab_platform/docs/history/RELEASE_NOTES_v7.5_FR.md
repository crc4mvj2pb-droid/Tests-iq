# Notes de version — Virtual Lab Platform v7.5

**Objectif (feuille de route) :**
- éventuellement, des modèles de croissance tumorale ou de mécanismes associés à des maladies, uniquement si les équations, les données et les limites sont justifiées ;
- présenter les résultats comme exploratoires, jamais comme des conseils médicaux ni des prédictions cliniques validées.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Équations justifiées et sourcées | `biomed.py`. **Croissance de Gompertz** (Gompertz 1825 ; Laird 1964 pour les tumeurs) : solution exacte et point d'inflexion à V = K/e. **Agrégation en deux étapes de Finke–Watzky** (Watzky & Finke 1997 ; Morris et al. 2008 pour les protéines) : solution exacte, temps de demi-conversion, calcul protégé contre le dépassement numérique aux temps longs. |
| Vérification | Pour chaque modèle, comparaison à une **intégration RK4 indépendante** des équations différentielles (écart < 1e-9). Conservation [A] + [B] = A0 respectée à 1e-12. Le temps de demi-conversion redonne exactement A0/2. Deux cas indépendants ajoutés au banc : taille K/e à l'inflexion, et régime initial de nucléation [B] ≈ k1·A0·t. Le banc compte 43 cas. |
| Caractère exploratoire | Chaque résultat porte l'avertissement : « Exploratory model: not fitted to clinical data; not for diagnosis, prognosis, treatment decisions or clinical prediction ». Il figure aussi dans les hypothèses du contrat et dans le domaine « Biomédical exploratoire », qui exclut toute prédiction clinique. |
| Données | **Aucune donnée clinique** : ces modèles restent au niveau « vérifié » (exactitude mathématique) et ne prétendent à aucune validation sur patients. |

## Tests
`tests/test_v75_biomed.py` : 6 tests.

## Limites
- Les paramètres sont illustratifs et les unités arbitraires (« a.u. ») là où aucune grandeur physique n'est définie.
- Ces modèles ne représentent ni traitement, ni immunité, ni hétérogénéité spatiale.
