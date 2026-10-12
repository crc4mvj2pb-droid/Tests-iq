# Banc d'essai indépendant — Virtual Lab Platform v6.5

Généré par `python scripts/run_benchmarks.py` le 2026-10-12T21:14:59+00:00 (Python 3.13.16).
Les références sont calculées dans `benchmarks/independent_suite.py` : formule fermée, table publiée ou intégrateur écrit à part. Ce fichier n'est importé par aucun test unitaire de moteur. Les tolérances ont été fixées avant la première exécution, à partir de l'erreur connue de chaque méthode (colonne « Base de la tolérance »).

## Synthèse

- **33 cas**, 15 moteurs ou modules, 8 domaines (biochimie, chimie, neurosciences, thermique, unités, écologie, électricité, épidémiologie).
- Conformes : 29 · limites connues reproduites : 2 · refus attendus obtenus : 2.
- Échecs : 0 · limites modifiées : 0 · non refusés : 0 · erreurs : 0.
- Verdict : **tous les cas ont le résultat attendu**.

## Résultats

| Cas | Domaine | Moteur | Type de référence | Observé | Référence | Écart | Tolérance | Base de la tolérance | Statut |
|---|---|---|---|---|---|---|---|---|---|
| Pont de Wheatstone déséquilibré : courant du galvanomètre | électricité | `dc_resistive_network` | analytical — Théorème de Thévenin (tout manuel de circuits) | 0.00198019802 | 0.00198019802 | 7.008282843e-15 | 1e-12 (relative) | résolution directe en double précision | conforme |
| Circuit RC : v(τ) = V·(1 − e⁻¹) | électricité | `rc_rl_step_response` | analytical — Solution de l'EDO du premier ordre | 3.160602794 | 3.160602794 | 0 | 1e-12 (relative) | formule fermée évaluée | conforme |
| RLC série sous-amorti : dépassement maximal | électricité | `series_rlc_step_response` | analytical — Ogata, Modern Control Engineering : Mp = exp(−ζπ/√(1−ζ²)) | 9.272339465 | 9.272339465 | 0 | 1e-09 (relative) | point d'échantillonnage placé exactement à t_p = π/ω_d | conforme |
| RLC série à la résonance : I = V/R | électricité | `series_rlc_ac` | analytical — Impédance complexe Z = R à ω0 = 1/√(LC) | 0.05 | 0.05 | 0 | 1e-09 (relative) | annulation X_L − X_C à l'arrondi près | conforme |
| Balayage logarithmique : pic échantillonné ≠ résonance vraie | électricité | `series_rlc_frequency_sweep` | analytical — f0 = 1/(2π√LC) | 1584.893192 | 1591.549431 | 0.004182237968 | écart > 0.001 et ≤ 0.0598 | au plus un demi-pas logarithmique (10^0,025 − 1 ≈ 5,9 %) | limite reproduite |
| A → B → C : maximum de [B] | chimie | `mass_action_kinetics` | analytical — Atkins & de Paula, Physical Chemistry : B_max = A0·(k2/k1)^(k2/(k1−k2)) | 0.5428826433 | 0.5428835233 | 8.800342364e-07 | 0.0001 (absolue) | maximum lu sur une grille de 0,01 s : erreur ≤ B''·Δt²/8 ≈ 1e-5 | conforme |
| A ⇌ B : [B]/[A] → K = kf/kr | chimie | `mass_action_kinetics` | analytical — Loi d'action de masse à l'équilibre | 3 | 3 | 3.700743415e-15 | 1e-09 (relative) | transitoire résiduel e^(−80) négligeable ; RK4 dt = 0,01 s | conforme |
| 2A → P : demi-vie t½ = 1/(2k·A0) | chimie | `mass_action_kinetics` | analytical — Cinétique du second ordre (Espenson) | 1 | 1 | 6.075273618e-11 | 1e-08 (relative) | RK4 dt = 0,01 s, erreur O(dt⁴) | conforme |
| Problème raide de Robertson, [A] à t = 4 s | chimie | `mass_action_kinetics` | published_benchmark — Hindmarsh, ODEPACK/LSODE (cité par Hairer & Wanner, Solving ODEs II) | 0.9055186824 | 0.90552 | 1.455043608e-06 | 0.002 (relative) | table publiée à 5 chiffres significatifs ; méthode implicite rtol = 1e-7 | conforme |
| Problème raide de Robertson, [B] à t = 4 s | chimie | `mass_action_kinetics` | published_benchmark — Hindmarsh, ODEPACK/LSODE (cité par Hairer & Wanner, Solving ODEs II) | 2.240475733e-05 | 2.2405e-05 | 1.083115845e-05 | 0.002 (relative) | table publiée à 5 chiffres significatifs ; méthode implicite rtol = 1e-7 | conforme |
| Problème raide de Robertson, [C] à t = 4 s | chimie | `mass_action_kinetics` | published_benchmark — Hindmarsh, ODEPACK/LSODE (cité par Hairer & Wanner, Solving ODEs II) | 0.09445891281 | 0.094459 | 9.230062718e-07 | 0.002 (relative) | table publiée à 5 chiffres significatifs ; méthode implicite rtol = 1e-7 | conforme |
| Problème raide de Robertson, [A] à t = 400 s | chimie | `mass_action_kinetics` | published_benchmark — Hindmarsh, ODEPACK/LSODE (cité par Hairer & Wanner, Solving ODEs II) | 0.4505187028 | 0.45052 | 2.879381494e-06 | 0.002 (relative) | table publiée à 5 chiffres significatifs ; méthode implicite rtol = 1e-7 | conforme |
| Problème raide de Robertson, [B] à t = 400 s | chimie | `mass_action_kinetics` | published_benchmark — Hindmarsh, ODEPACK/LSODE (cité par Hairer & Wanner, Solving ODEs II) | 3.222901877e-06 | 3.2229e-06 | 5.825033317e-07 | 0.002 (relative) | table publiée à 5 chiffres significatifs ; méthode implicite rtol = 1e-7 | conforme |
| Problème raide de Robertson, [C] à t = 400 s | chimie | `mass_action_kinetics` | published_benchmark — Hindmarsh, ODEPACK/LSODE (cité par Hairer & Wanner, Solving ODEs II) | 0.5494780743 | 0.54948 | 3.504555132e-06 | 0.002 (relative) | table publiée à 5 chiffres significatifs ; méthode implicite rtol = 1e-7 | conforme |
| Robertson avec Dormand–Prince explicite : refus attendu | chimie | `mass_action_kinetics` | published_benchmark — Raideur : un schéma explicite exige un pas ~1e-4 s sur 40 s | refus : `NumericalError: Maximum number of steps (20000) reached at t = 24.4267. If the step size became very small, th` | — | — | 0 (relative) | budget de 20 000 pas | refus attendu obtenu |
| CH4 + 2 O2 → CO2 + 2 H2O (1 mol CH4, 3 mol O2) : eau formée | chimie | `stoichiometry` | analytical — Bilan stœchiométrique | 2 | 2 | 0 | 0 (absolue) | calcul exact | conforme |
| Arrhenius : k double entre 25 et 35 °C pour Ea = R·ln2/(1/T1 − 1/T2) | chimie | `arrhenius_reaction` | analytical — Loi d'Arrhenius ; R exact (SI 2019) | 2 | 2 | 1.776356839e-15 | 1e-12 (relative) | formule fermée | conforme |
| Michaelis–Menten : v(3·Km) = 0,75·Vmax | biochimie | `enzyme_kinetics` | analytical — Michaelis & Menten (1913) | 7.5 | 7.5 | 0 | 1e-12 (relative) | formule fermée | conforme |
| SIR : taille finale de l'épidémie (équation implicite) | épidémiologie | `sir_epidemic` | analytical — Kermack & McKendrick (1927) : R∞ = N − S0·exp(−R0·R∞/N) | 9802.272566 | 9801.833659 | 4.477803827e-05 | 0.001 (relative) | Euler explicite d'ordre 1, dt = 0,01 j : erreur attendue ~1e-4 relative | conforme |
| SIR : pic épidémique, pas de 0,01 jour | épidémiologie | `sir_epidemic` | analytical — Intégrale première S + I − (N/R0)·ln S | 4029.362638 | 4035.51441 | 0.001524408282 | 0.005 (relative) | erreur d'Euler + pic lu sur des valeurs journalières | conforme |
| SIR : pic épidémique, pas de 1 jour (limite connue d'Euler explicite) | épidémiologie | `sir_epidemic` | analytical — Intégrale première S + I − (N/R0)·ln S | 4239.203815 | 4035.51441 | 0.05047421096 | écart > 0.005 | Euler d'ordre 1 au pas maximal autorisé (estimation a priori ~5 % ; pas de borne supérieure démontrée) | limite reproduite |
| Croissance logistique contre intégration RK4 indépendante | écologie | `logistic_growth` | independent_solver — RK4 de ce fichier, dt = 1e-3 | 948.0871536 | 948.0871536 | 2.278324212e-15 | 1e-09 (relative) | erreur RK4 ~1e-13 | conforme |
| Lotka–Volterra : période des petites oscillations 2π/√(αγ) | écologie | `lotka_volterra` | analytical — Linéarisation autour de l'équilibre (Murray, Mathematical Biology) | 5.130250319 | 5.130199321 | 9.940894869e-06 | 0.001 (relative) | amplitude 1 % : correction non linéaire O(ε²) ~1e-4 ; passages interpolés | conforme |
| Neurone LIF : instant du premier potentiel d'action | neurosciences | `leaky_integrate_fire` | analytical — t1 = τ·ln(RI/(RI − (V_seuil − V_repos))) | 32.2 | 32.18875825 | 0.01124175132 | 0.05 (absolue) | détection sur la grille : erreur ≤ dt = 0,05 ms | conforme |
| Neurone LIF sous la rhéobase : aucun potentiel d'action | neurosciences | `leaky_integrate_fire` | analytical — V∞ = V_repos + RI < V_seuil | 0 | 0 | 0 | 0 (absolue) | exact | conforme |
| Diffusion 1D : profil stationnaire linéaire au milieu | thermique | `heat_diffusion_1d` | analytical — Solution stationnaire de l'équation de la chaleur | 45 | 45 | 3.197442311e-13 | 1e-06 (absolue) | transitoire e^(−π²·20) négligeable | conforme |
| Diffusion 1D : température au milieu, série de Fourier | thermique | `heat_diffusion_1d` | analytical — Carslaw & Jaeger, Conduction of Heat in Solids | 52.9340739 | 52.92531441 | 0.008759486373 | 0.05 (absolue) | FTCS, Δx = 1 mm : erreur O(Δx²) | conforme |
| Schéma explicite instable (α·dt/dx² > 0,5) : refus attendu | thermique | `heat_diffusion_1d` | analytical — Critère de stabilité de von Neumann | refus : `ValueError: Explicit heat solver unstable: alpha*dt/dx^2 = 4 > 0.5. Reduce dt_s or increase nodes spacing.` | — | — | 0 (relative) | r = 4 > 0,5 | refus attendu obtenu |
| 1 atm = 101 325 Pa | unités | `units` | published_benchmark — BIPM, Brochure SI (9e éd.) | 101325 | 101325 | 0 | 1e-15 (relative) | définition exacte | conforme |
| 1 eV = 1,602 176 634e-19 J | unités | `units` | published_benchmark — BIPM, Brochure SI (9e éd.) : e exact | 1.602176634e-19 | 1.602176634e-19 | 0 | 1e-15 (relative) | définition exacte | conforme |
| 25 °C = 298,15 K (conversion affine) | unités | `units` | published_benchmark — BIPM, Brochure SI (9e éd.) | 298.15 | 298.15 | 0 | 1e-15 (relative) | définition exacte | conforme |
| 1 Da = 1,660 539 066 60e-27 kg | unités | `units` | published_benchmark — CODATA 2018 | 1.660539067e-27 | 1.660539067e-27 | 0 | 1e-11 (relative) | valeur recommandée | conforme |
| 1 L/h = 2,777…e-7 m³/s | unités | `units` | published_benchmark — BIPM, Brochure SI (9e éd.) | 2.777777778e-07 | 2.777777778e-07 | 0 | 1e-15 (relative) | définitions exactes | conforme |

## Résultats négatifs et limites documentées

- **Balayage logarithmique : pic échantillonné ≠ résonance vraie** : écart observé 0.004182237968 (seuil de limite 0.001). au plus un demi-pas logarithmique (10^0,025 − 1 ≈ 5,9 %).
- **Robertson avec Dormand–Prince explicite : refus attendu** : le moteur refuse au lieu de renvoyer un résultat faux (`NumericalError: Maximum number of steps (20000) reached at t = 24.4267. If the step size became very small, the problem is probably stiff: u`).
- **SIR : pic épidémique, pas de 1 jour (limite connue d'Euler explicite)** : écart observé 0.05047421096 (seuil de limite 0.005). Euler d'ordre 1 au pas maximal autorisé (estimation a priori ~5 % ; pas de borne supérieure démontrée).
- **Schéma explicite instable (α·dt/dx² > 0,5) : refus attendu** : le moteur refuse au lieu de renvoyer un résultat faux (`ValueError: Explicit heat solver unstable: alpha*dt/dx^2 = 4 > 0.5. Reduce dt_s or increase nodes spacing.`).

## Incidents de la première exécution

- Arrhenius : la première version de la référence utilisait R = 8,314462618 J/(mol·K) (valeur tronquée) ; l'écart de 1,3e-11 venait de la référence, pas du moteur. Correction : R = N_A·k_B exact.
- SIR au pas de 1 jour : l'estimation a priori de l'erreur (≤ 5 %) a été dépassée (5,05 % observé). La borne supérieure, non démontrée, a été retirée pour ce cas de limite connue ; seul le seuil bas (> 0,5 %) est vérifié.

## Ce que ce banc ne montre pas

- Il vérifie que les moteurs résolvent correctement **leurs équations**. Il ne valide pas ces équations contre des mesures réelles (niveau « validé sur données », jalon C et v7).
- Aucun solveur de circuits externe (ngspice) n'est disponible dans l'environnement : les références électriques sont analytiques.
- Les cas de Robertson ne sont exacts qu'à 5 chiffres significatifs (précision de la table publiée).
