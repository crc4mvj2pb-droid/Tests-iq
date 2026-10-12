# Validation de la cinétique chimique — v5.3 (moteur 2.3)

Généré par `python scripts/kinetics_validation.py` le 2026-10-12T17:29:51+00:00 (Python 3.13.16).
Erreur = plus grand écart absolu |calcul − solution exacte| sur tous les instants échantillonnés et toutes les espèces (concentrations initiales de l'ordre de 1).

## first_order

A → B, k = 0.7 s⁻¹ : [A] = A0·e^(−kt)

| Méthode | Pas dt ou tolérance rtol | Erreur max (trajectoire) | Ordre observé | Erreur finale réelle | Erreur finale estimée par le moteur |
|---|---|---|---|---|---|
| rk4 | dt = 0.2 s | 1.32e-06 | — | 3.80e-07 | 3.82e-07 |
| rk4 | dt = 0.1 s | 7.80e-08 | 4.08 | 2.24e-08 | 2.25e-08 |
| rk4 | dt = 0.05 s | 4.74e-09 | 4.04 | 1.36e-09 | 1.36e-09 |
| rk4 | dt = 0.025 s | 2.92e-10 | 4.02 | 8.38e-11 | 8.39e-11 |
| dopri5 | rtol = 0.0001 | 1.80e-10 | — | 5.44e-11 | 1.87e-08 |
| dopri5 | rtol = 1e-06 | 1.80e-10 | — | 5.44e-11 | 1.87e-08 |
| dopri5 | rtol = 1e-08 | 1.63e-10 | — | 5.29e-11 | 1.71e-08 |
| implicit_euler | rtol = 0.0001 | 1.48e-05 | — | 6.12e-06 | 5.46e-06 |
| implicit_euler | rtol = 1e-06 | 1.63e-07 | — | 6.80e-08 | 6.12e-08 |
| implicit_euler | rtol = 1e-08 | 1.64e-09 | — | 6.86e-10 | 6.17e-10 |

## consecutive

A → B → C, k1 = 1.0, k2 = 0.4 s⁻¹ : [B] = A0·k1/(k2−k1)·(e^(−k1t) − e^(−k2t))

| Méthode | Pas dt ou tolérance rtol | Erreur max (trajectoire) | Ordre observé | Erreur finale réelle | Erreur finale estimée par le moteur |
|---|---|---|---|---|---|
| rk4 | dt = 0.2 s | 9.50e-06 | — | 5.11e-08 | 5.12e-08 |
| rk4 | dt = 0.1 s | 5.46e-07 | 4.12 | 3.17e-09 | 3.18e-09 |
| rk4 | dt = 0.05 s | 3.27e-08 | 4.06 | 1.98e-10 | 1.98e-10 |
| rk4 | dt = 0.025 s | 2.00e-09 | 4.03 | 1.23e-11 | 1.23e-11 |
| dopri5 | rtol = 0.0001 | 1.82e-09 | — | 8.72e-12 | 1.31e-07 |
| dopri5 | rtol = 1e-06 | 1.57e-09 | — | 8.55e-12 | 1.15e-07 |
| dopri5 | rtol = 1e-08 | 5.23e-10 | — | 7.35e-12 | 4.68e-08 |
| implicit_euler | rtol = 0.0001 | 1.87e-05 | — | 3.46e-06 | 3.09e-06 |
| implicit_euler | rtol = 1e-06 | 2.02e-07 | — | 3.75e-08 | 3.37e-08 |
| implicit_euler | rtol = 1e-08 | 2.03e-09 | — | 3.77e-10 | 3.40e-10 |

## consecutive_equal_rates

A → B → C with k1 = k2 = 0.5 s⁻¹ (degenerate case) : [B] = A0·k·t·e^(−kt)

| Méthode | Pas dt ou tolérance rtol | Erreur max (trajectoire) | Ordre observé | Erreur finale réelle | Erreur finale estimée par le moteur |
|---|---|---|---|---|---|
| rk4 | dt = 0.2 s | 1.39e-06 | — | 7.19e-08 | 7.23e-08 |
| rk4 | dt = 0.1 s | 8.28e-08 | 4.07 | 4.14e-09 | 4.16e-09 |
| rk4 | dt = 0.05 s | 5.04e-09 | 4.04 | 2.49e-10 | 2.49e-10 |
| rk4 | dt = 0.025 s | 3.11e-10 | 4.02 | 1.52e-11 | 1.52e-11 |
| dopri5 | rtol = 0.0001 | 1.70e-10 | — | 1.43e-11 | 2.02e-08 |
| dopri5 | rtol = 1e-06 | 1.70e-10 | — | 1.43e-11 | 2.02e-08 |
| dopri5 | rtol = 1e-08 | 1.07e-10 | — | 1.29e-11 | 1.32e-08 |
| implicit_euler | rtol = 0.0001 | 1.90e-05 | — | 8.76e-06 | 7.75e-06 |
| implicit_euler | rtol = 1e-06 | 2.19e-07 | — | 1.05e-07 | 9.41e-08 |
| implicit_euler | rtol = 1e-08 | 2.22e-09 | — | 1.06e-09 | 9.52e-10 |

## second_order_dimerisation

2A → P, k = 0.5 : d[A]/dt = −2k[A]² ⇒ [A] = A0/(1 + 2k·A0·t)

| Méthode | Pas dt ou tolérance rtol | Erreur max (trajectoire) | Ordre observé | Erreur finale réelle | Erreur finale estimée par le moteur |
|---|---|---|---|---|---|
| rk4 | dt = 0.2 s | 6.42e-06 | — | 1.68e-07 | 1.67e-07 |
| rk4 | dt = 0.1 s | 4.40e-07 | 3.87 | 1.13e-08 | 1.12e-08 |
| rk4 | dt = 0.05 s | 2.81e-08 | 3.97 | 7.14e-10 | 7.14e-10 |
| rk4 | dt = 0.025 s | 1.76e-09 | 3.99 | 4.48e-11 | 4.48e-11 |
| dopri5 | rtol = 0.0001 | 1.22e-08 | — | 2.80e-10 | 1.35e-07 |
| dopri5 | rtol = 1e-06 | 1.22e-08 | — | 2.80e-10 | 1.35e-07 |
| dopri5 | rtol = 1e-08 | 6.12e-10 | — | 3.33e-11 | 2.12e-08 |
| implicit_euler | rtol = 0.0001 | 2.04e-05 | — | 8.60e-06 | 7.45e-06 |
| implicit_euler | rtol = 1e-06 | 2.35e-07 | — | 1.25e-07 | 1.12e-07 |
| implicit_euler | rtol = 1e-08 | 2.38e-09 | — | 1.29e-09 | 1.16e-09 |

## mixed_second_order

A + B → P, k = 0.3, A0 = 1, B0 = 2 : [A] = A0(B0−A0)/(B0·e^((B0−A0)kt) − A0)

| Méthode | Pas dt ou tolérance rtol | Erreur max (trajectoire) | Ordre observé | Erreur finale réelle | Erreur finale estimée par le moteur |
|---|---|---|---|---|---|
| rk4 | dt = 0.2 s | 5.61e-07 | — | 3.58e-08 | 3.58e-08 |
| rk4 | dt = 0.1 s | 3.45e-08 | 4.02 | 2.18e-09 | 2.19e-09 |
| rk4 | dt = 0.05 s | 2.13e-09 | 4.02 | 1.35e-10 | 1.35e-10 |
| rk4 | dt = 0.025 s | 1.33e-10 | 4.01 | 8.37e-12 | 8.37e-12 |
| dopri5 | rtol = 0.0001 | 1.80e-10 | — | 8.32e-12 | 9.57e-09 |
| dopri5 | rtol = 1e-06 | 1.80e-10 | — | 8.32e-12 | 9.57e-09 |
| dopri5 | rtol = 1e-08 | 1.41e-10 | — | 7.21e-12 | 8.20e-09 |
| implicit_euler | rtol = 0.0001 | 2.03e-05 | — | 6.02e-06 | 5.30e-06 |
| implicit_euler | rtol = 1e-06 | 2.38e-07 | — | 7.59e-08 | 6.82e-08 |
| implicit_euler | rtol = 1e-08 | 2.41e-09 | — | 7.73e-10 | 6.96e-10 |

## reversible

A ⇌ B, kf = 0.8, kr = 0.2 : [A] = A_eq + (A0 − A_eq)·e^(−(kf+kr)t), A_eq = kr/(kf+kr)

| Méthode | Pas dt ou tolérance rtol | Erreur max (trajectoire) | Ordre observé | Erreur finale réelle | Erreur finale estimée par le moteur |
|---|---|---|---|---|---|
| rk4 | dt = 0.2 s | 4.64e-06 | — | 1.87e-07 | 1.88e-07 |
| rk4 | dt = 0.1 s | 2.67e-07 | 4.12 | 1.08e-08 | 1.08e-08 |
| rk4 | dt = 0.05 s | 1.60e-08 | 4.06 | 6.46e-10 | 6.47e-10 |
| rk4 | dt = 0.025 s | 9.78e-10 | 4.03 | 3.95e-11 | 3.96e-11 |
| dopri5 | rtol = 0.0001 | 8.77e-10 | — | 3.85e-11 | 6.41e-08 |
| dopri5 | rtol = 1e-06 | 8.77e-10 | — | 3.85e-11 | 6.41e-08 |
| dopri5 | rtol = 1e-08 | 4.65e-10 | — | 3.43e-11 | 3.84e-08 |
| implicit_euler | rtol = 0.0001 | 1.79e-05 | — | 6.96e-06 | 5.72e-06 |
| implicit_euler | rtol = 1e-06 | 2.01e-07 | — | 1.45e-07 | 1.30e-07 |
| implicit_euler | rtol = 1e-08 | 2.03e-09 | — | 1.54e-09 | 1.39e-09 |

## parallel

A → B (k1 = 0.6), A → C (k2 = 0.2) : [B] = k1/(k1+k2)·A0·(1 − e^(−(k1+k2)t))

| Méthode | Pas dt ou tolérance rtol | Erreur max (trajectoire) | Ordre observé | Erreur finale réelle | Erreur finale estimée par le moteur |
|---|---|---|---|---|---|
| rk4 | dt = 0.2 s | 2.29e-06 | — | 6.64e-08 | 6.67e-08 |
| rk4 | dt = 0.1 s | 1.34e-07 | 4.10 | 3.88e-09 | 3.89e-09 |
| rk4 | dt = 0.05 s | 8.11e-09 | 4.05 | 2.35e-10 | 2.35e-10 |
| rk4 | dt = 0.025 s | 4.99e-10 | 4.02 | 1.44e-11 | 1.44e-11 |
| dopri5 | rtol = 0.0001 | 3.54e-10 | — | 1.09e-11 | 3.29e-08 |
| dopri5 | rtol = 1e-06 | 3.54e-10 | — | 1.09e-11 | 3.29e-08 |
| dopri5 | rtol = 1e-08 | 2.30e-10 | — | 1.02e-11 | 2.32e-08 |
| implicit_euler | rtol = 0.0001 | 1.58e-05 | — | 8.83e-07 | 7.88e-07 |
| implicit_euler | rtol = 1e-06 | 1.75e-07 | — | 9.70e-09 | 8.72e-09 |
| implicit_euler | rtol = 1e-08 | 1.76e-09 | — | 9.79e-11 | 8.81e-11 |

## Usage et limites de RK4

- RK4 à pas fixe est d'ordre 4 : diviser dt par 2 divise l'erreur par environ 16 (colonne « ordre observé » ≈ 4), tant que dt reste petit devant le plus petit temps caractéristique (1/k).
- Au-delà (k·dt ≳ 1), l'erreur devient importante. Pour k·dt ≳ 2,8, RK4 est instable et le moteur refuse le calcul (« Negative concentration »).
- RK4 ne convient pas aux systèmes **raides** (constantes de vitesse très différentes) : utiliser `implicit_euler` (voir le problème de Robertson dans `tests/test_v52_numerics.py`).
- L'erreur estimée par le moteur (doublement du pas pour RK4, re-résolution pour les méthodes adaptatives) est indicative : elle n'est pas une borne garantie.
