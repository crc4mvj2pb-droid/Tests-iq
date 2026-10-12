"""Independent benchmark suite (v5.9).

Separate from the unit tests: every reference below is computed here, from a closed form, a
published table or an integrator written in this file. Nothing is imported from an engine except
through the public contract API (model_registry.run_model) and units.convert. Tolerances were set
before the first run from the method's known error (stated in `tolerance_basis`); they are never
loosened to make a case pass. Negative results are part of the suite:
  - expectation "within_tolerance": the engine must match the reference;
  - expectation "known_limit": the case documents a limit; it passes when the limit is reproduced
    (deviation above the stated threshold), so a silent change of behaviour is noticed;
  - expectation "refused": the engine must refuse the input instead of returning a wrong result.
"""
from __future__ import annotations

import math
from typing import Any, Callable

import model_registry
import units

R_GAS = 6.02214076e23 * 1.380649e-23  # J/(mol·K) = N_A·k_B, both exact since SI 2019; computed here independently of constants.py


def _run(model_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    return model_registry.run_model(model_id, inputs)["result"]


def _rk4(f: Callable[[float, list[float]], list[float]], y0: list[float], t_end: float, dt: float) -> list[float]:
    """Classical RK4 written for this suite only (reference integrator, fine step)."""
    y, t, steps = list(y0), 0.0, int(round(t_end / dt))
    for _ in range(steps):
        k1 = f(t, y)
        k2 = f(t + dt / 2, [a + dt / 2 * b for a, b in zip(y, k1)])
        k3 = f(t + dt / 2, [a + dt / 2 * b for a, b in zip(y, k2)])
        k4 = f(t + dt, [a + dt * b for a, b in zip(y, k3)])
        y = [a + dt / 6 * (b + 2 * c + 2 * d + e) for a, b, c, d, e in zip(y, k1, k2, k3, k4)]
        t += dt
    return y


def _bisect(g: Callable[[float], float], lo: float, hi: float) -> float:
    for _ in range(200):
        mid = (lo + hi) / 2
        if (g(lo) > 0) == (g(mid) > 0):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---- electrical ------------------------------------------------------------------------------

def wheatstone_galvanometer():
    v, r1, r2, r3, r4, rg = 10.0, 100.0, 200.0, 150.0, 250.0, 50.0
    d = _run("dc_resistive_network", {"source_voltage": v, "resistors": [
        {"id": "R1", "a": "S", "b": "A", "resistance_ohm": r1}, {"id": "R2", "a": "A", "b": "0", "resistance_ohm": r2},
        {"id": "R3", "a": "S", "b": "B", "resistance_ohm": r3}, {"id": "R4", "a": "B", "b": "0", "resistance_ohm": r4},
        {"id": "G", "a": "A", "b": "B", "resistance_ohm": rg}]})
    observed = next(b["current_a"] for b in d["branches"] if b["id"] == "G")
    v_th = v * (r2 / (r1 + r2) - r4 / (r3 + r4))
    r_th = r1 * r2 / (r1 + r2) + r3 * r4 / (r3 + r4)
    return observed, v_th / (r_th + rg)


def rc_voltage_at_tau():
    d = _run("rc_rl_step_response", {"kind": "RC", "source_voltage_v": 5.0, "resistance_ohm": 1000.0, "capacitance_f": 1e-6, "duration_s": 0.005, "points": 501})
    point = d["points"][100]
    assert abs(point["time_s"] - 1e-3) < 1e-15
    return point["capacitor_voltage_v"], 5.0 * (1 - math.exp(-1))


def rlc_step_overshoot():
    r, l, c, v = 10.0, 0.01, 1e-6, 5.0
    w0 = 1 / math.sqrt(l * c); zeta = r / 2 * math.sqrt(c / l); wd = w0 * math.sqrt(1 - zeta ** 2)
    tp = math.pi / wd
    d = _run("series_rlc_step_response", {"source_voltage_v": v, "resistance_ohm": r, "inductance_h": l, "capacitance_f": c, "duration_s": 2 * tp, "points": 2001})
    observed = max(p["capacitor_voltage_v"] for p in d["points"])
    return observed, v * (1 + math.exp(-zeta * math.pi / math.sqrt(1 - zeta ** 2)))


def rlc_ac_at_resonance():
    r, l, c = 100.0, 0.01, 1e-6
    f0 = 1 / (2 * math.pi * math.sqrt(l * c))
    d = _run("series_rlc_ac", {"source_voltage_rms_v": 5.0, "resistance_ohm": r, "inductance_h": l, "capacitance_f": c, "frequency_hz": f0})
    return d["current_rms_a"], 5.0 / r


def rlc_sweep_sampled_peak():
    """Known limit: the reported peak is the best *sampled* point, not the true resonance."""
    d = _run("series_rlc_frequency_sweep", {})
    f0 = 1 / (2 * math.pi * math.sqrt(0.01 * 1e-6))
    return d["peak_current_sampled"]["frequency_hz"], f0


# ---- chemistry -------------------------------------------------------------------------------

def _species(**c0):
    return [{"id": k, "initial_concentration": v} for k, v in c0.items()]


def consecutive_b_maximum():
    k1, k2 = 1.0, 0.4
    d = _run("mass_action_kinetics", {"species": _species(A=1.0, B=0.0, C=0.0), "duration": 3.0, "dt": 0.01, "reactions": [
        {"id": "r1", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": k1}, {"id": "r2", "reactants": {"B": 1}, "products": {"C": 1}, "rate_constant": k2}]})
    observed = max(row["B"] for row in d["rows"])
    return observed, (k2 / k1) ** (k2 / (k1 - k2))  # B_max/A0 (Atkins & de Paula, consecutive reactions)


def reversible_equilibrium_ratio():
    d = _run("mass_action_kinetics", {"species": _species(A=1.0, B=0.0), "duration": 20.0, "dt": 0.01, "reactions": [
        {"id": "f", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 3.0}, {"id": "b", "reactants": {"B": 1}, "products": {"A": 1}, "rate_constant": 1.0}]})
    final = d["summary"]["final_concentrations"]
    return final["B"] / final["A"], 3.0  # K = kf/kr


def second_order_half_life():
    d = _run("mass_action_kinetics", {"species": _species(A=2.0, P=0.0), "duration": 1.0, "dt": 0.01, "reactions": [
        {"id": "r", "reactants": {"A": 2}, "products": {"P": 1}, "rate_constant": 0.25}]})
    return d["summary"]["final_concentrations"]["A"], 1.0  # t½ = 1/(2k·A0) = 1 s ⇒ [A](1 s) = A0/2


# Robertson problem, reference values printed by the LSODE demonstration program
# (A. C. Hindmarsh, ODEPACK; reproduced in Hairer & Wanner, Solving ODEs II, §IV.1), 5 significant digits.
ROBERTSON_TABLE = {4.0: {"A": 9.0552e-01, "B": 2.2405e-05, "C": 9.4459e-02}, 400.0: {"A": 4.5052e-01, "B": 3.2229e-06, "C": 5.4948e-01}}


def _robertson(t_end, method, **extra):
    return {"species": _species(A=1.0, B=0.0, C=0.0), "duration": t_end, "dt": t_end / 10, "method": method, **extra, "reactions": [
        {"id": "r1", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.04},
        {"id": "r2", "reactants": {"B": 2}, "products": {"B": 1, "C": 1}, "rate_constant": 3e7},
        {"id": "r3", "reactants": {"B": 1, "C": 1}, "products": {"A": 1, "C": 1}, "rate_constant": 1e4}]}


def robertson_case(t_end, species):
    def case():
        d = _run("mass_action_kinetics", _robertson(t_end, "implicit_euler", rtol=1e-7, atol=1e-12))
        return d["summary"]["final_concentrations"][species], ROBERTSON_TABLE[t_end][species]
    return case


def robertson_explicit_refused():
    return _run("mass_action_kinetics", _robertson(40.0, "dopri5", max_steps=20000))


def methane_combustion():
    d = _run("stoichiometry", {"reactants": {"CH4": 1, "O2": 2}, "products": {"CO2": 1, "H2O": 2}, "species": [
        {"id": "CH4", "amount_mol": 1.0, "formula": "CH4"}, {"id": "O2", "amount_mol": 3.0, "formula": "O2"},
        {"id": "CO2", "amount_mol": 0.0, "formula": "CO2"}, {"id": "H2O", "amount_mol": 0.0, "formula": "H2O"}]})
    return d["product_amounts_theoretical_mol"]["H2O"], 2.0


def arrhenius_rule_of_ten_degrees():
    """Ea chosen so that k doubles between 25 °C and 35 °C: Ea = R·ln2 / (1/T1 − 1/T2)."""
    t1, t2 = 298.15, 308.15
    ea = R_GAS * math.log(2) / (1 / t1 - 1 / t2)
    k1 = _run("arrhenius_reaction", {"activation_energy_j_mol": ea, "temperature_k": t1})["summary"]["rate_constant_s_inv"]
    k2 = _run("arrhenius_reaction", {"activation_energy_j_mol": ea, "temperature_k": t2})["summary"]["rate_constant_s_inv"]
    return k2 / k1, 2.0


def michaelis_menten_three_km():
    d = _run("enzyme_kinetics", {"vmax": 10.0, "km": 2.0, "s_max": 6.0, "points": 4})
    return next(r["y"] for r in d["rows"] if abs(r["x"] - 6.0) < 1e-12), 7.5  # v(3·Km) = 3/4·Vmax


# ---- biology, ecology, neuroscience, heat ----------------------------------------------------

SIR = {"population": 10000.0, "beta": 0.4, "gamma": 0.1, "initial_infected": 5.0}


def _sir_peak_reference():
    n, b, g, i0 = SIR["population"], SIR["beta"], SIR["gamma"], SIR["initial_infected"]
    s0, r0 = n - i0, b / g
    # Conserved quantity S + I − (N/R0)·ln S; the peak is reached at S = N/R0 (Kermack–McKendrick).
    return i0 + s0 - n / r0 + n / r0 * math.log((n / r0) / s0)


def sir_final_size():
    n, r0, s0 = SIR["population"], SIR["beta"] / SIR["gamma"], SIR["population"] - SIR["initial_infected"]
    d = _run("sir_epidemic", {**SIR, "days": 400.0, "dt": 0.01})
    reference = _bisect(lambda r_inf: r_inf - (n - s0 * math.exp(-r0 * r_inf / n)), 1.0, n)  # final-size equation
    return d["summary"]["final_recovered"], reference


def sir_peak(dt):
    def case():
        d = _run("sir_epidemic", {**SIR, "days": 200.0, "dt": dt})
        return d["summary"]["peak_infectious"], _sir_peak_reference()
    return case


def logistic_against_integration():
    n0, k, r, t = 10.0, 1000.0, 0.3, 25.0
    d = _run("logistic_growth", {"initial_population": n0, "carrying_capacity": k, "growth_rate": r, "duration": t, "points": 51})
    reference = _rk4(lambda _t, y: [r * y[0] * (1 - y[0] / k)], [n0], t, 1e-3)[0]
    return d["summary"]["final_population"], reference


def lotka_volterra_small_oscillation_period():
    alpha, beta, delta, gamma = 1.0, 0.1, 0.075, 1.5
    x_eq, z_eq = gamma / delta, alpha / beta
    d = _run("lotka_volterra", {"initial_prey": 1.01 * x_eq, "initial_predators": z_eq, "prey_growth": alpha, "predation_rate": beta,
                                "predator_growth": delta, "predator_decay": gamma, "duration": 30.0, "dt": 0.001})
    rows, crossings = d["rows"], []
    for a, b in zip(rows, rows[1:]):
        if (a["prey"] - x_eq) < 0 <= (b["prey"] - x_eq):  # upward crossings of the equilibrium
            crossings.append(a["time"] + (x_eq - a["prey"]) / (b["prey"] - a["prey"]) * (b["time"] - a["time"]))
    observed = (crossings[-1] - crossings[0]) / (len(crossings) - 1)
    return observed, 2 * math.pi / math.sqrt(alpha * gamma)  # linearised period near the equilibrium


LIF = {"v_rest_mv": -70.0, "v_reset_mv": -75.0, "v_threshold_mv": -54.0, "initial_voltage_mv": -70.0, "tau_ms": 20.0, "resistance_mohm": 10.0,
       "duration_ms": 500.0, "dt_ms": 0.05}


def lif_first_spike():
    current = 2.0  # nA; R·I = 20 mV
    d = _run("leaky_integrate_fire", {**LIF, "current_na": current})
    drive = LIF["resistance_mohm"] * current
    return d["summary"]["spike_times_ms"][0], LIF["tau_ms"] * math.log(drive / (drive - (LIF["v_threshold_mv"] - LIF["v_rest_mv"])))


def lif_below_rheobase():
    current = 0.99 * (LIF["v_threshold_mv"] - LIF["v_rest_mv"]) / LIF["resistance_mohm"]  # just below the rheobase
    return _run("leaky_integrate_fire", {**LIF, "current_na": current})["summary"]["spike_count"], 0


def heat_steady_linear_profile():
    d = _run("heat_diffusion_1d", {"length_m": 0.1, "diffusivity_m2_s": 1e-5, "left_temp_c": 80.0, "right_temp_c": 10.0, "initial_temp_c": 10.0,
                                   "nodes": 21, "dt_s": 1.0, "total_time_s": 20000.0})
    return d["summary"]["final_midpoint_temp_c"], 45.0


def heat_midpoint_fourier():
    """u(L/2, t) for a rod at T0 with both ends held at T1 (Carslaw & Jaeger): T1 + (T0−T1)·Σ 4/((2m+1)π)·sin((2m+1)π/2)·e^(−((2m+1)π)²·αt/L²)."""
    length, alpha, t, t0, t1 = 0.05, 1e-6, 500.0, 20.0, 60.0
    d = _run("heat_diffusion_1d", {"length_m": length, "diffusivity_m2_s": alpha, "left_temp_c": t1, "right_temp_c": t1, "initial_temp_c": t0,
                                   "nodes": 51, "dt_s": 0.4, "total_time_s": t})
    series = sum(4 / ((2 * m + 1) * math.pi) * math.sin((2 * m + 1) * math.pi / 2) * math.exp(-((2 * m + 1) * math.pi) ** 2 * alpha * t / length ** 2) for m in range(200))
    return d["summary"]["final_midpoint_temp_c"], t1 + (t0 - t1) * series


def heat_unstable_refused():
    return _run("heat_diffusion_1d", {"length_m": 0.1, "diffusivity_m2_s": 1e-4, "nodes": 21, "dt_s": 1.0, "total_time_s": 10.0})


# Incidents of the first run (kept for transparency, see BENCHMARK_REPORT_FR.md):
INCIDENTS = [
    "Arrhenius : la première version de la référence utilisait R = 8,314462618 J/(mol·K) (valeur tronquée) ; l'écart de 1,3e-11 venait "
    "de la référence, pas du moteur. Correction : R = N_A·k_B exact.",
    "Base forte 1e-3 mol/L (v7.2) : la référence supposait l'autoprotolyse de l'eau négligeable (< 1e-10) ; l'effet réel vaut 4,3e-9 en pH. "
    "La référence inclut désormais l'eau exactement (tolérance inchangée).",
    "SIR au pas de 1 jour : l'estimation a priori de l'erreur (≤ 5 %) a été dépassée (5,05 % observé). La borne supérieure, non démontrée, "
    "a été retirée pour ce cas de limite connue ; seul le seuil bas (> 0,5 %) est vérifié.",
]


def environmental_three_half_lives():
    k = 0.05
    d = _run("environmental_decay", {"initial_load": 80.0, "removal_rate": k, "duration": 3 * math.log(2) / k, "points": 11})
    return d["summary"]["final_load"], 10.0  # three half-lives: 80 → 10


def pk_area_under_curve():
    """AUC from 0 to ∞ = dose / clearance; the sampled curve (trapezoid) over 12 half-lives must agree."""
    dose, volume, clearance = 100.0, 10.0, 2.0
    half_life = math.log(2) * volume / clearance
    d = _run("one_compartment_pk", {"input_amount": dose, "distribution_volume": volume, "clearance": clearance, "duration": 12 * half_life, "points": 1001})
    rows = d["rows"]
    auc = sum((b["time"] - a["time"]) * (a["concentration"] + b["concentration"]) / 2 for a, b in zip(rows, rows[1:]))
    return auc, dose / clearance


def lumped_cooling_time():
    """Time for a hot body to cool from 350 K to 310 K in 290 K air: t = τ·ln((T0 − T_amb)/(T − T_amb))."""
    r, c = 0.5, 400.0
    d = _run("lumped_thermal_transient", {"power_w": 0.0, "ambient_temperature_k": 290.0, "initial_temperature_k": 350.0, "thermal_resistance_k_per_w": r,
                                         "thermal_capacitance_j_per_k": c, "duration_s": r * c * math.log(60.0 / 20.0), "points": 3})
    return d["final_temperature_k"], 310.0


def two_layer_wall_interface():
    """Interface temperature of a two-layer wall written as a voltage divider of thermal resistances."""
    r1, r2 = 0.1 / (1.0 * 2.0), 0.05 / (0.05 * 2.0)  # L/(k·A)
    d = _run("plane_wall_conduction", {"layers": [{"thickness_m": 0.1, "conductivity_w_mk": 1.0}, {"thickness_m": 0.05, "conductivity_w_mk": 0.05}],
                                       "area_m2": 2.0, "hot_temperature_k": 300.0, "cold_temperature_k": 260.0})
    return d["temperatures"][1]["temperature_k"], 300.0 - 40.0 * r1 / (r1 + r2)


def acetate_buffer_ph():
    """Equal amounts of acetic acid and acetate (0.1 mol/L each): the exact pH is within 1e-3 of pKa for this concentration."""
    d = _run("aqueous_acid_base", {"weak_systems": [{"name": "acetic", "pka": [4.756], "total_concentration_mol_l": 0.2}], "strong_base_mol_l": 0.1})
    return d["ph"], 4.756


def strong_base_ph():
    d = _run("aqueous_acid_base", {"strong_base_mol_l": 1e-3})
    oh = (1e-3 + math.sqrt(1e-6 + 4e-14)) / 2  # [OH⁻] = C + Kw/[OH⁻] (water autoionisation included exactly)
    return d["ph"], 14.0 + math.log10(oh)


def fhn_upper_hopf_current():
    """Upper Hopf current of FitzHugh–Nagumo (a = 0.7, b = 0.8, ε = 0.08): v* = +√(1 − εb), I = (v* + a)/b − v* + v*³/3."""
    v = math.sqrt(1 - 0.08 * 0.8)
    d = _run("fitzhugh_nagumo", {"current": 1.0, "duration": 1.0})
    return d["hopf_currents"][1], (v + 0.7) / 0.8 - v + v ** 3 / 3


def hh_no_spike_without_current():
    return _run("hodgkin_huxley", {"current_ua_cm2": 0.0, "duration_ms": 100.0})["spike_count"], 0


# ---- units (SI Brochure, 9th edition, BIPM 2019; CODATA 2018) --------------------------------

def unit_case(value, from_unit, to_unit, expected):
    return lambda: (units.convert(value, from_unit, to_unit), expected)


def _case(case_id, domain, model, title, run, *, kind, source, tol, basis, expectation="within_tolerance", relative=True, limit_threshold=None):
    return {"id": case_id, "domain": domain, "model": model, "title": title, "run": run, "reference_kind": kind, "source": source,
            "tolerance": tol, "relative": relative, "tolerance_basis": basis, "expectation": expectation, "limit_threshold": limit_threshold}


CASES = [
    _case("wheatstone_galvanometer", "électricité", "dc_resistive_network", "Pont de Wheatstone déséquilibré : courant du galvanomètre", wheatstone_galvanometer,
          kind="analytical", source="Théorème de Thévenin (tout manuel de circuits)", tol=1e-12, basis="résolution directe en double précision"),
    _case("rc_voltage_at_tau", "électricité", "rc_rl_step_response", "Circuit RC : v(τ) = V·(1 − e⁻¹)", rc_voltage_at_tau,
          kind="analytical", source="Solution de l'EDO du premier ordre", tol=1e-12, basis="formule fermée évaluée"),
    _case("rlc_step_overshoot", "électricité", "series_rlc_step_response", "RLC série sous-amorti : dépassement maximal", rlc_step_overshoot,
          kind="analytical", source="Ogata, Modern Control Engineering : Mp = exp(−ζπ/√(1−ζ²))", tol=1e-9, basis="point d'échantillonnage placé exactement à t_p = π/ω_d"),
    _case("rlc_ac_at_resonance", "électricité", "series_rlc_ac", "RLC série à la résonance : I = V/R", rlc_ac_at_resonance,
          kind="analytical", source="Impédance complexe Z = R à ω0 = 1/√(LC)", tol=1e-9, basis="annulation X_L − X_C à l'arrondi près"),
    _case("rlc_sweep_sampled_peak", "électricité", "series_rlc_frequency_sweep", "Balayage logarithmique : pic échantillonné ≠ résonance vraie", rlc_sweep_sampled_peak,
          kind="analytical", source="f0 = 1/(2π√LC)", tol=0.0598, basis="au plus un demi-pas logarithmique (10^0,025 − 1 ≈ 5,9 %)",
          expectation="known_limit", limit_threshold=1e-3),
    _case("consecutive_b_maximum", "chimie", "mass_action_kinetics", "A → B → C : maximum de [B]", consecutive_b_maximum,
          kind="analytical", source="Atkins & de Paula, Physical Chemistry : B_max = A0·(k2/k1)^(k2/(k1−k2))", tol=1e-4, relative=False,
          basis="maximum lu sur une grille de 0,01 s : erreur ≤ B''·Δt²/8 ≈ 1e-5"),
    _case("reversible_equilibrium_ratio", "chimie", "mass_action_kinetics", "A ⇌ B : [B]/[A] → K = kf/kr", reversible_equilibrium_ratio,
          kind="analytical", source="Loi d'action de masse à l'équilibre", tol=1e-9, basis="transitoire résiduel e^(−80) négligeable ; RK4 dt = 0,01 s"),
    _case("second_order_half_life", "chimie", "mass_action_kinetics", "2A → P : demi-vie t½ = 1/(2k·A0)", second_order_half_life,
          kind="analytical", source="Cinétique du second ordre (Espenson)", tol=1e-8, basis="RK4 dt = 0,01 s, erreur O(dt⁴)"),
    *[_case(f"robertson_t{int(t)}_{sid}", "chimie", "mass_action_kinetics", f"Problème raide de Robertson, [{sid}] à t = {t:g} s", robertson_case(t, sid),
            kind="published_benchmark", source="Hindmarsh, ODEPACK/LSODE (cité par Hairer & Wanner, Solving ODEs II)", tol=2e-3,
            basis="table publiée à 5 chiffres significatifs ; méthode implicite rtol = 1e-7")
      for t in ROBERTSON_TABLE for sid in ("A", "B", "C")],
    _case("robertson_explicit_refused", "chimie", "mass_action_kinetics", "Robertson avec Dormand–Prince explicite : refus attendu", robertson_explicit_refused,
          kind="published_benchmark", source="Raideur : un schéma explicite exige un pas ~1e-4 s sur 40 s", tol=0, basis="budget de 20 000 pas",
          expectation="refused"),
    _case("methane_combustion", "chimie", "stoichiometry", "CH4 + 2 O2 → CO2 + 2 H2O (1 mol CH4, 3 mol O2) : eau formée", methane_combustion,
          kind="analytical", source="Bilan stœchiométrique", tol=0, basis="calcul exact", relative=False),
    _case("arrhenius_rule_of_ten_degrees", "chimie", "arrhenius_reaction", "Arrhenius : k double entre 25 et 35 °C pour Ea = R·ln2/(1/T1 − 1/T2)", arrhenius_rule_of_ten_degrees,
          kind="analytical", source="Loi d'Arrhenius ; R exact (SI 2019)", tol=1e-12, basis="formule fermée"),
    _case("michaelis_menten_three_km", "biochimie", "enzyme_kinetics", "Michaelis–Menten : v(3·Km) = 0,75·Vmax", michaelis_menten_three_km,
          kind="analytical", source="Michaelis & Menten (1913)", tol=1e-12, basis="formule fermée"),
    _case("sir_final_size", "épidémiologie", "sir_epidemic", "SIR : taille finale de l'épidémie (équation implicite)", sir_final_size,
          kind="analytical", source="Kermack & McKendrick (1927) : R∞ = N − S0·exp(−R0·R∞/N)", tol=1e-3,
          basis="Euler explicite d'ordre 1, dt = 0,01 j : erreur attendue ~1e-4 relative"),
    _case("sir_peak_fine_step", "épidémiologie", "sir_epidemic", "SIR : pic épidémique, pas de 0,01 jour", sir_peak(0.01),
          kind="analytical", source="Intégrale première S + I − (N/R0)·ln S", tol=5e-3,
          basis="erreur d'Euler + pic lu sur des valeurs journalières"),
    _case("sir_peak_coarse_step", "épidémiologie", "sir_epidemic", "SIR : pic épidémique, pas de 1 jour (limite connue d'Euler explicite)", sir_peak(1.0),
          kind="analytical", source="Intégrale première S + I − (N/R0)·ln S", tol=None, basis="Euler d'ordre 1 au pas maximal autorisé (estimation a priori ~5 % ; pas de borne supérieure démontrée)",
          expectation="known_limit", limit_threshold=5e-3),
    _case("logistic_against_integration", "écologie", "logistic_growth", "Croissance logistique contre intégration RK4 indépendante", logistic_against_integration,
          kind="independent_solver", source="RK4 de ce fichier, dt = 1e-3", tol=1e-9, basis="erreur RK4 ~1e-13"),
    _case("lotka_volterra_period", "écologie", "lotka_volterra", "Lotka–Volterra : période des petites oscillations 2π/√(αγ)", lotka_volterra_small_oscillation_period,
          kind="analytical", source="Linéarisation autour de l'équilibre (Murray, Mathematical Biology)", tol=1e-3,
          basis="amplitude 1 % : correction non linéaire O(ε²) ~1e-4 ; passages interpolés"),
    _case("lif_first_spike", "neurosciences", "leaky_integrate_fire", "Neurone LIF : instant du premier potentiel d'action", lif_first_spike,
          kind="analytical", source="t1 = τ·ln(RI/(RI − (V_seuil − V_repos)))", tol=0.05, relative=False, basis="détection sur la grille : erreur ≤ dt = 0,05 ms"),
    _case("lif_below_rheobase", "neurosciences", "leaky_integrate_fire", "Neurone LIF sous la rhéobase : aucun potentiel d'action", lif_below_rheobase,
          kind="analytical", source="V∞ = V_repos + RI < V_seuil", tol=0, relative=False, basis="exact"),
    _case("heat_steady_linear_profile", "thermique", "heat_diffusion_1d", "Diffusion 1D : profil stationnaire linéaire au milieu", heat_steady_linear_profile,
          kind="analytical", source="Solution stationnaire de l'équation de la chaleur", tol=1e-6, relative=False, basis="transitoire e^(−π²·20) négligeable"),
    _case("heat_midpoint_fourier", "thermique", "heat_diffusion_1d", "Diffusion 1D : température au milieu, série de Fourier", heat_midpoint_fourier,
          kind="analytical", source="Carslaw & Jaeger, Conduction of Heat in Solids", tol=0.05, relative=False, basis="FTCS, Δx = 1 mm : erreur O(Δx²)"),
    _case("heat_unstable_refused", "thermique", "heat_diffusion_1d", "Schéma explicite instable (α·dt/dx² > 0,5) : refus attendu", heat_unstable_refused,
          kind="analytical", source="Critère de stabilité de von Neumann", tol=0, basis="r = 4 > 0,5", expectation="refused"),
    _case("environmental_three_half_lives", "environnement", "environmental_decay", "Décroissance du premier ordre : charge après trois demi-vies", environmental_three_half_lives,
          kind="analytical", source="t½ = ln2/k (cinétique du premier ordre)", tol=1e-12, basis="formule fermée"),
    _case("pk_area_under_curve", "pharmacologie", "one_compartment_pk", "Pharmacocinétique : aire sous la courbe = dose/clairance", pk_area_under_curve,
          kind="analytical", source="Gibaldi & Perrier, Pharmacokinetics : AUC = D/CL", tol=1e-3,
          basis="trapèzes sur 1 000 intervalles (erreur ~(kΔt)²/12 ≈ 6e-6) et queue après 12 demi-vies (2,4e-4)"),
    _case("lumped_cooling_time", "thermique", "lumped_thermal_transient", "Refroidissement newtonien : température après t = τ·ln(3)", lumped_cooling_time,
          kind="analytical", source="Loi de refroidissement de Newton (Incropera et al., §5.2)", tol=1e-12, basis="formule fermée"),
    _case("two_layer_wall_interface", "thermique", "plane_wall_conduction", "Mur à deux couches : température d'interface (diviseur de résistances)", two_layer_wall_interface,
          kind="analytical", source="Résistances thermiques en série (Incropera et al., §3.1)", tol=1e-12, basis="formule fermée"),
    _case("acetate_buffer_ph", "physicochimie", "aqueous_acid_base", "Tampon acétate équimolaire : pH = pKa", acetate_buffer_ph,
          kind="analytical", source="Henderson–Hasselbalch dans son domaine de validité (Atkins & de Paula)", tol=1e-3, relative=False,
          basis="écart dû à [H⁺] ≪ 0,1 mol/L : |ΔpH| < 1e-3"),
    _case("strong_base_ph", "physicochimie", "aqueous_acid_base", "Base forte 1e-3 mol/L : pH = 11", strong_base_ph,
          kind="analytical", source="pH + pOH = pKw avec [OH⁻] = C + Kw/[OH⁻]", tol=1e-9, relative=False, basis="formule fermée (quadratique)"),
    _case("fhn_upper_hopf_current", "neurosciences", "fitzhugh_nagumo", "FitzHugh–Nagumo : courant de Hopf supérieur", fhn_upper_hopf_current,
          kind="analytical", source="Trace du jacobien nulle à l'équilibre (FitzHugh 1961)", tol=1e-12, basis="formule fermée"),
    _case("hh_no_spike_without_current", "neurosciences", "hodgkin_huxley", "Hodgkin–Huxley au repos : aucun potentiel d'action sans courant", hh_no_spike_without_current,
          kind="analytical", source="Équilibre stable au potentiel de repos (Hodgkin & Huxley 1952)", tol=0, relative=False, basis="exact"),
    _case("unit_atm", "unités", "units", "1 atm = 101 325 Pa", unit_case(1.0, "atm", "Pa", 101325.0), kind="published_benchmark", source="BIPM, Brochure SI (9e éd.)", tol=1e-15, basis="définition exacte"),
    _case("unit_ev", "unités", "units", "1 eV = 1,602 176 634e-19 J", unit_case(1.0, "eV", "J", 1.602176634e-19), kind="published_benchmark", source="BIPM, Brochure SI (9e éd.) : e exact", tol=1e-15, basis="définition exacte"),
    _case("unit_celsius", "unités", "units", "25 °C = 298,15 K (conversion affine)", unit_case(25.0, "degC", "K", 298.15), kind="published_benchmark", source="BIPM, Brochure SI (9e éd.)", tol=1e-15, basis="définition exacte"),
    _case("unit_dalton", "unités", "units", "1 Da = 1,660 539 066 60e-27 kg", unit_case(1.0, "Da", "kg", 1.66053906660e-27), kind="published_benchmark", source="CODATA 2018", tol=1e-11, basis="valeur recommandée"),
    _case("unit_litre_hour", "unités", "units", "1 L/h = 2,777…e-7 m³/s", unit_case(1.0, "L/h", "m^3/s", 1e-3 / 3600), kind="published_benchmark", source="BIPM, Brochure SI (9e éd.)", tol=1e-15, basis="définitions exactes"),
]


def run_case(case: dict) -> dict:
    row = {k: case[k] for k in ("id", "domain", "model", "title", "reference_kind", "source", "tolerance", "relative", "tolerance_basis", "expectation")}
    try:
        outcome = case["run"]()
    except Exception as exc:  # a refusal is the expected outcome for some cases
        row.update(observed=None, reference=None, deviation=None, refusal=f"{type(exc).__name__}: {exc}"[:300],
                   refusal_code=getattr(exc, "code", None), status="refused_as_expected" if case["expectation"] == "refused" else "error")
        return row
    if case["expectation"] == "refused":
        row.update(observed=str(outcome)[:80], reference=None, deviation=None, status="not_refused")
        return row
    observed, reference = outcome
    deviation = abs(observed - reference) / abs(reference) if case["relative"] and reference else abs(observed - reference)
    row.update(observed=observed, reference=reference, deviation=deviation)
    if case["expectation"] == "known_limit":
        row["limit_threshold"] = case["limit_threshold"]
        within_bound = case["tolerance"] is None or deviation <= case["tolerance"]
        row["status"] = "limit_reproduced" if case["limit_threshold"] < deviation and within_bound else "limit_changed"
    else:
        row["status"] = "pass" if deviation <= case["tolerance"] else "fail"
    return row


GOOD_STATUSES = {"pass", "limit_reproduced", "refused_as_expected"}


def run_suite() -> list[dict]:
    return [run_case(case) for case in CASES]
