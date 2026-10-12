# Notes de version — Virtual Lab Platform v5.4

**Objectif (feuille de route) :** étendre l'électricité seulement après validation du circuit CC : transitoires RC/RL, puis RLC. Comparer chaque modèle à des cas analytiques ou à des solveurs de référence, ajouter des graphiques avec des unités cohérentes, et ne pas prétendre simuler des composants non linéaires.

## Critères d'acceptation et résultat
| Critère | Résultat |
|---|---|
| Transitoire RC/RL sur la paillasse | `workbench_transient.py` : tout circuit câblé avec **un** condensateur **ou** une bobine, des résistances et une source CC. Le réseau résistif est réduit **exactement** à son équivalent de Thévenin par le solveur CC validé en v4.4 : R_th par une sonde de 1 V (source court-circuitée), V_th par une résistance de test. Les valeurs sont converties par le module d'unités (par exemple « 1 µF »). |
| Refus explicites | Deux éléments réactifs ou plus (circuit d'ordre supérieur), élément directement sur la source idéale, élément hors de tout chemin fermé, valeur nulle, négative ou non numérique. Chaque refus a un code et un message traduit. |
| RLC série | `simulate_series_rlc_step` : réponse indicielle analytique dans les 3 régimes (pseudo-périodique, critique, apériodique), avec état initial (tension du condensateur, courant). |
| Comparaison à des références indépendantes | RC (diviseur), RL et **pont de Wheatstone avec un condensateur au milieu**, comparés aux formules de Thévenin établies à la main (écart relatif < 1e-12). RLC dans les 3 régimes comparé à une **intégration numérique indépendante** de l'équation différentielle (Dormand–Prince, v5.2) : écart < 1e-7 V. |
| Bilans d'énergie | Énergie fournie = dissipée + variation de l'énergie stockée : à 1e-3 près pour le transitoire RC, à 2e-3 près pour le RLC (intégration trapézoïdale des puissances échantillonnées). |
| Graphiques et unités | Bouton « Simuler le transitoire RC/RL » dans l'interface : τ, équivalent de Thévenin, valeur finale, courbe tension (V) et courant (A) en fonction du temps (s), bilan d'énergie. Le résultat est enregistré comme dossier, vérifiable et rejouable. |
| API et contrats | `POST /api/electrical/workbench-transient-run` (avec enregistrement), `POST /api/electrical/rlc-step`, et contrats `workbench_rc_rl_transient` et `series_rlc_step_response`. |

## Défauts trouvés et corrigés pendant cette version
- **RLC apériodique** : la fenêtre de temps par défaut (10/α) coupait la réponse bien avant le régime permanent (0,23 V au lieu de 5 V). Le mode lent décroît en α − √(α² − ω₀²). La fenêtre est maintenant fondée sur ce mode lent.
- Contrat : la condition initiale unique `initial_value` (en V ou en A selon l'élément) n'avait pas d'unité cohérente. Elle est remplacée par `initial_voltage_v` (V) et `initial_current_a` (A).

## Tests
`tests/test_v54_transients.py` (16 tests) et `tests/browser/test_v54_transient_ui.py`.

## Limites
- **Un seul élément réactif** sur la paillasse. Les circuits RLC, AC ou à plusieurs condensateurs câblés ne sont pas calculés depuis la paillasse : seuls les modèles analytiques RLC série et AC série existent.
- Les tensions des autres nœuds ne sont pas tracées au cours du temps (seules celles de l'élément).
- Pas d'interrupteurs, de diodes ni de transistors : aucun composant non linéaire n'est simulé.
- **Aucune comparaison avec un logiciel de référence externe** (ngspice), faute d'outil disponible.
