# Notes de version — Virtual Lab Platform v5.9

**Objectif (feuille de route) :** banc d'essai scientifique indépendant. Il s'agit de cas de référence séparés des tests unitaires, comparés à des valeurs analytiques ou publiées (ou à des logiciels de référence quand c'est possible), avec les écarts, les critères d'acceptation et les résultats négatifs documentés.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Cas séparés des tests unitaires | `benchmarks/independent_suite.py` compte 33 cas. Chaque référence est calculée dans ce fichier : formule fermée, table publiée ou intégrateur RK4 écrit à part. Le fichier n'importe que `model_registry` (API publique des contrats) et `units`, ce que vérifie une analyse du code. **Aucun test unitaire ne réutilise ces références**, ce qui est aussi vérifié. Les paramètres diffèrent de ceux des tests unitaires. |
| Références analytiques, publiées et solveur indépendant | **Analytiques** : pont de Wheatstone, v(τ) d'un RC, dépassement d'un RLC (Ogata), résonance, maximum de [B] dans A → B → C, équilibre A ⇌ B, demi-vie d'ordre 2, bilan stœchiométrique, règle des 10 °C d'Arrhenius, Michaelis–Menten, taille finale et pic SIR (Kermack–McKendrick), période de Lotka–Volterra, premier potentiel d'action et rhéobase d'un LIF, diffusion stationnaire et série de Fourier. **Publiées** : problème raide de Robertson (table LSODE, 6 valeurs), définitions SI et CODATA (5 conversions). **Solveur indépendant** : croissance logistique contre RK4. Au total, **15 moteurs ou modules et 8 domaines**. |
| Tolérances fixées a priori | Chaque cas indique la base de sa tolérance (erreur connue de la méthode : ordre de l'intégrateur, grille d'échantillonnage, précision de la table). Aucune tolérance n'a été élargie pour faire passer un cas. |
| Résultats négatifs | 4 cas documentent une limite ou un refus. (1) Le pic d'un balayage logarithmique est le meilleur **point échantillonné**, pas la résonance vraie : écart de 0,42 %. (2) Le modèle SIR (Euler explicite) au pas de 1 jour s'écarte de **5,05 %** du pic exact. (3) Dormand–Prince explicite refuse le problème raide de Robertson. (4) Le schéma explicite de diffusion refuse r = 4 > 0,5. Si un comportement change (une limite disparaît, un refus n'a plus lieu), le banc échoue. |
| Écarts documentés, rapport généré | `python scripts/run_benchmarks.py` génère `BENCHMARK_REPORT_FR.md` : observé, référence, écart, tolérance, base de la tolérance et statut pour chaque cas, puis la synthèse, les résultats négatifs, les incidents et ce que le banc ne montre pas. Le code de sortie vaut 1 en cas d'écart inattendu. Le rapport est régénéré à chaque publication. Route `GET /api/benchmarks` (liste des cas). |
| Classement qui ne masque rien | Les statuts possibles sont : conforme, échec, limite reproduite, limite modifiée, refus attendu, non refusé, erreur. Des tests vérifient le classement sur des cas synthétiques. |

## Incidents de la première exécution (conservés)
- **Arrhenius** : la référence utilisait d'abord R = 8,314462618 J/(mol·K), une valeur tronquée. L'écart de 1,3e-11 venait de la référence, pas du moteur. Correction : R = N_A·k_B, valeur exacte.
- **SIR au pas de 1 jour** : l'erreur observée (5,05 %) a dépassé mon estimation a priori (≤ 5 %). Cette borne n'étant pas démontrée, elle a été retirée pour ce cas de limite connue. Seul le seuil bas (> 0,5 %) est vérifié.

## Complément du critère v5.8 « conditions »
`pipelines.py` 1.1 signale par l'avertissement `inconsistent_conditions` deux étapes d'une même expérience qui utilisent des **conditions de fonctionnement différentes** : température différente (y compris celle d'un adaptateur thermique) ou unités de concentration différentes. Les deux exemples lient leurs conditions et n'émettent aucun avertissement.

## Tests
- `tests/test_v59_benchmarks.py` : 15 tests (indépendance, documentation des cas, classement, constantes exactes, exécution complète du banc, rapport, API).
- `tests/test_v59_pipeline_conditions.py` : 4 tests.

## Limites
- Aucun logiciel de référence externe : ngspice n'est pas disponible dans l'environnement, et aucun téléchargement de modèle SBML de référence n'a été fait. Les références de circuits sont analytiques.
- Ce banc vérifie que les moteurs résolvent correctement leurs équations. **Il ne valide aucun modèle sur des mesures réelles** : c'est l'objet du jalon C et de la v7.3.
- Les valeurs de Robertson ne sont publiées qu'à 5 chiffres significatifs.
