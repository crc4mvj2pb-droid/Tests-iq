# Notes de version — Virtual Lab Platform v7.1

**Objectif (feuille de route) :**
- commencer par des bilans énergétiques simples, des capacités thermiques et des systèmes à constantes de temps ;
- valider sur des solutions analytiques et des cas documentés.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Système à une constante de temps | Contrat `lumped_thermal_transient` (`thermal.py`) : C·dT/dt = P − (T − T_amb)/R_th, avec solution exacte, température stationnaire et constante de temps. Comparé à une **intégration RK4 indépendante** pour trois cas (chauffage, refroidissement, puissance négative) : écart < 1e-9 relatif. **Bilan d'énergie** fourni = perdu + stocké : écart < 1e-5. |
| Domaine de validité contrôlé | Le nombre de Biot Bi = h·L_c/k est calculé si h, L_c et k sont donnés. Pour Bi ≥ 0,1, l'avertissement `lumped_assumption_invalid` est émis. Si seule une partie des grandeurs est donnée, la demande est refusée (`incomplete_biot_inputs`). |
| Conduction stationnaire | Contrat `plane_wall_conduction` : couches en série avec convection facultative ; flux, coefficient U et températures d'interface. Comparé à un **solveur indépendant par différences finies** (3 couches, algorithme de Thomas) : écart < 1e-9. Comparé aussi à un calcul à la main (1 400 W pour 1,4 W/(m·K), 10 m², 20 K, 0,2 m). |
| Banc d'essai | Deux cas indépendants ajoutés : refroidissement newtonien (température après τ·ln 3) et température d'interface d'un mur à deux couches (diviseur de résistances). Le banc compte 37 cas. |
| Maillon faible corrigé | L'adaptateur d'échauffement des expériences multi-modèles était « calculable » depuis la v5.8. Il est désormais **vérifié** comme limite de long terme du transitoire, et la chaîne « Circuit CC → échauffement → Arrhenius → cinétique » devient entièrement vérifiée. Le test v5.8 de la règle du maillon faible impose maintenant explicitement un niveau « calculable » pour continuer à tester cette règle (modification documentée). Le test navigateur v5.8 attend désormais « vérifié » pour cette chaîne ; une première validation de la v7.1 a échoué sur ce point avant cette adaptation. |
| Domaine | Le domaine « Thermique et transferts » regroupe 3 modèles, plus un graphique de température. |

## Tests
`tests/test_v71_thermal.py` : 13 tests.

## Limites
- Aucun « cas documenté » de manuel n'a été recopié : je n'avais pas accès aux exemples chiffrés des ouvrages. Les références restent analytiques ou numériques indépendantes.
- Pas de rayonnement, pas de résistance de contact, pas de conduction 2D ou 3D.
