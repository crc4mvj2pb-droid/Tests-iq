# Notes de version — Virtual Lab Platform v7.3

**Objectif (feuille de route) :**
- des modèles simples de croissance, de réactions enzymatiques ou de populations ;
- contrôle de la conservation, des unités et des paramètres, et **validation sur des données publiques**.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Protocole fixé à l'avance | `data_validation.py`, protocole `michaelis_menten_puromycin_treated`, consigné **avant** d'en regarder le résultat. Il fixe : la question, le jeu publié (Puromycine, cellules traitées), le découpage (ajustement sur la première mesure de chaque concentration, validation sur le second réplicat), la statistique (RMSE de validation divisée par l'écart-type des réplicats s_rep, avec s_rep² = Σ d_i²/2n) et le **seuil de 2**. Le seuil de 2·s_rep avait été choisi lors de la planification, avant tout calcul. |
| Résultat | **Validé** : rapport de 0,69 (RMSE de validation 7,40 pour s_rep = 10,78 counts/min/min, ce dernier recalculé à la main dans un test). |
| Le critère discrimine | **Témoin négatif** : les paramètres ajustés sur les cellules traitées doivent échouer sur les cellules non traitées. C'est bien le cas, avec un rapport de 2,79 > 2. Le protocole exige ce rejet pour conclure « validé ». Si les données sont altérées (un écart grossier à la plus forte concentration), le verdict devient « non validé » (test). |
| Premier modèle « validé sur données » | `enzyme_kinetics` passe au niveau `validated_on_data`. La preuve de type « data » cite le jeu sourcé, et `check_claims()` exige cette source. La portée est écrite : **valable pour ce jeu et ses conditions seulement**. Le domaine « Biologie quantitative » compte 1 modèle validé sur données. |
| Exposition | `GET /api/validations`. Le badge « Validé sur données » apparaît dans le catalogue. |

## Tests
- `tests/test_v73_data_validation.py` : 5 tests.
- Les tests v5.7 qui comptaient 0 modèle validé sur données et 10 modèles vérifiés dans le catalogue attendent désormais 1 et 9. Ce changement est dû à la nouvelle preuve et il est documenté.

## Limites
- La validation porte sur **un seul jeu de 12 mesures** issu d'une thèse de 1974. Elle montre que la forme de Michaelis–Menten décrit ces données au niveau du bruit de réplication. Elle ne prouve rien pour d'autres enzymes ou d'autres conditions.
- Les autres modèles de biologie (croissance logistique, Lotka–Volterra) restent « vérifiés » : aucune donnée publique sourcée n'a été ajoutée pour eux.
