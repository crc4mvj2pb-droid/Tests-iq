"""Generate KINETICS_VALIDATION_FR.md: error of each integrator against analytical solutions (v5.3).

Usage: python scripts/kinetics_validation.py
Every number in the report is computed by this script; nothing is typed by hand.
"""
from __future__ import annotations

import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.kinetics_analytic import CASES, max_abs_error  # noqa: E402
from chemical_kinetics import ENGINE_VERSION, simulate_reaction_network  # noqa: E402
from version import APP_VERSION  # noqa: E402

RK4_STEPS = (0.2, 0.1, 0.05, 0.025)


def final_error(d, case):
    ref = case["exact"](d["rows"][-1]["time"])
    return max(abs(d["summary"]["final_concentrations"][sid] - v) for sid, v in ref.items())
TOLERANCES = (1e-4, 1e-6, 1e-8)


def main() -> int:
    lines = [f"# Validation de la cinétique chimique — v{APP_VERSION} (moteur {ENGINE_VERSION})", "",
             f"Généré par `python scripts/kinetics_validation.py` le {datetime.now(timezone.utc).isoformat(timespec='seconds')} (Python {platform.python_version()}).",
             "Erreur = plus grand écart absolu |calcul − solution exacte| sur tous les instants échantillonnés et toutes les espèces (concentrations initiales de l'ordre de 1).", ""]
    for name, case in CASES.items():
        lines += [f"## {name}", "", case["description"], "", "| Méthode | Pas dt ou tolérance rtol | Erreur max (trajectoire) | Ordre observé | Erreur finale réelle | Erreur finale estimée par le moteur |", "|---|---|---|---|---|---|"]
        previous = None
        for dt in RK4_STEPS:
            d = simulate_reaction_network({**case["request"], "dt": dt, "method": "rk4"})
            err = max_abs_error(d, case["exact"])
            order = f"{math.log2(previous / err):.2f}" if previous and err > 0 else "—"
            est = max((d["summary"]["estimated_final_error"] or {}).values(), default=float("nan"))
            lines.append(f"| rk4 | dt = {dt:g} s | {err:.2e} | {order} | {final_error(d, case):.2e} | {est:.2e} |")
            previous = err
        for method in ("dopri5", "implicit_euler"):
            for rtol in TOLERANCES:
                d = simulate_reaction_network({**case["request"], "dt": 0.1, "method": method, "rtol": rtol, "atol": rtol * 1e-3})
                err = max_abs_error(d, case["exact"])
                est = max((d["summary"]["estimated_final_error"] or {}).values(), default=float("nan"))
                lines.append(f"| {method} | rtol = {rtol:g} | {err:.2e} | — | {final_error(d, case):.2e} | {est:.2e} |")
        lines.append("")
    lines += ["## Usage et limites de RK4", "",
              "- RK4 à pas fixe est d'ordre 4 : diviser dt par 2 divise l'erreur par environ 16 (colonne « ordre observé » ≈ 4), tant que dt reste petit devant le plus petit temps caractéristique (1/k).",
              "- Au-delà (k·dt ≳ 1), l'erreur devient importante. Pour k·dt ≳ 2,8, RK4 est instable et le moteur refuse le calcul (« Negative concentration »).",
              "- RK4 ne convient pas aux systèmes **raides** (constantes de vitesse très différentes) : utiliser `implicit_euler` (voir le problème de Robertson dans `tests/test_v52_numerics.py`).",
              "- L'erreur estimée par le moteur (doublement du pas pour RK4, re-résolution pour les méthodes adaptatives) est indicative : elle n'est pas une borne garantie.", ""]
    (ROOT / "KINETICS_VALIDATION_FR.md").write_text("\n".join(lines), encoding="utf-8")
    print("KINETICS_VALIDATION_FR.md written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
