"""Maturity levels of the platform's models (v5.7), with machine-checked evidence.

concept            — conceptual mock-up: description or workflow, no scientific calculation;
computable         — computes a result; only internal checks (no independent reference);
verified           — compared with at least one independent reference (closed form evaluated
                     separately, independent solver, published benchmark, statistical property)
                     in a test that exists in tests/ and passes in the generated validation matrix;
validated_on_data  — compared with sourced (experimental or public) data with an acceptance criterion.

`check_claims()` refuses any "verified" claim without existing test evidence and any
"validated_on_data" claim without a sourced dataset, so the catalogue cannot overstate a model.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
LEVELS = [
    {"id": "concept", "rank": 0, "label_fr": "Maquette conceptuelle", "definition": "Description ou flux de travail ; aucun calcul scientifique."},
    {"id": "computable", "rank": 1, "label_fr": "Modèle calculable", "definition": "Calcule un résultat ; contrôles internes seulement, sans référence indépendante."},
    {"id": "verified", "rank": 2, "label_fr": "Modèle vérifié",
     "definition": "Comparé à au moins une référence indépendante (solution analytique, solveur indépendant, benchmark publié, propriété statistique) dans un test existant."},
    {"id": "validated_on_data", "rank": 3, "label_fr": "Validé sur données", "definition": "Comparé à des données sourcées avec un critère d'acceptation explicite."},
]
LEVEL_IDS = {level["id"] for level in LEVELS}
INDEPENDENT_KINDS = {"analytical", "independent_solver", "published_benchmark", "statistical_property", "conserved_quantity"}


def _ev(kind: str, test: str, description: str, tolerance: str) -> dict[str, str]:
    return {"kind": kind, "test": test, "description": description, "tolerance": tolerance}


V44, V52, V53, V54, V56, V57 = ("tests/test_v44_dc_reference.py", "tests/test_v52_numerics.py", "tests/test_v53_kinetics_validation.py",
                                "tests/test_v54_transients.py", "tests/test_v56_sbml.py", "tests/test_v57_model_verification.py")

MATURITY: dict[str, dict[str, Any]] = {
    "dc_resistive_network": {"level": "verified", "evidence": [
        _ev("analytical", f"{V44}::test_wheatstone_bridge_matches_thevenin_formula", "Pont de Wheatstone, formule de Thévenin", "1e-9 relatif"),
        _ev("analytical", f"{V44}::test_r2r_ladder_halves_voltage_at_each_stage", "Échelle R-2R", "1e-9 relatif"),
        _ev("independent_solver", f"{V44}::test_reported_uncertainty_bounds_the_true_error", "300 réseaux, solveur exact en rationnels", "erreur ≤ incertitude publiée")]},
    "workbench_dc_circuit": {"level": "verified", "evidence": [
        _ev("analytical", f"{V44}::test_series_parallel_divider_closed_forms", "Série, parallèle, diviseur", "1e-10 relatif"),
        _ev("analytical", f"{V54}::test_rc_divider_matches_hand_thevenin", "Circuit câblé réduit à la main", "1e-12 relatif")]},
    "rc_rl_step_response": {"level": "verified", "evidence": [
        _ev("independent_solver", f"{V57}::test_rc_rl_step_against_integration", "Intégration Dormand–Prince de l'EDO", "1e-8 relatif")]},
    "series_rlc_ac": {"level": "verified", "evidence": [
        _ev("independent_solver", f"{V57}::test_series_rlc_ac_against_complex_arithmetic", "Arithmétique complexe indépendante", "1e-12 relatif")]},
    "series_rlc_frequency_sweep": {"level": "verified", "evidence": [
        _ev("analytical", f"{V57}::test_rlc_sweep_points_equal_individual_solves", "Points identiques aux résolutions unitaires ; f0 = 1/(2π√LC)", "exact / 1e-12")]},
    "series_rlc_step_response": {"level": "verified", "evidence": [
        _ev("independent_solver", f"{V54}::test_rlc_step_matches_independent_numerical_integration", "3 régimes contre intégration de l'EDO", "1e-7 V"),
        _ev("conserved_quantity", f"{V54}::test_rlc_energy_balance", "Bilan d'énergie", "2e-3 relatif")]},
    "workbench_rc_rl_transient": {"level": "verified", "evidence": [
        _ev("analytical", f"{V54}::test_capacitor_across_a_wheatstone_bridge", "Thévenin d'un pont, calcul à la main", "1e-12 relatif"),
        _ev("analytical", f"{V54}::test_rl_circuit_matches_hand_thevenin", "Circuit RL", "1e-10 relatif")]},
    "mass_action_kinetics": {"level": "verified", "evidence": [
        _ev("analytical", f"{V53}::test_trajectory_matches_analytical_solution", "7 solutions analytiques × 3 intégrateurs", "2e-7 (rk4, dt = 0,05 s)"),
        _ev("published_benchmark", f"{V52}::test_stiff_robertson_problem_matches_published_reference_with_implicit_method", "Problème de Robertson (Hairer & Wanner)", "2e-3 relatif")]},
    "stoichiometry": {"level": "verified", "evidence": [
        _ev("analytical", "tests/test_v36_stoichiometry.py::test_neutralization_checks_atom_balance_and_calculates_extent", "Bilan atomique et avancement calculés à la main", "exact"),
        _ev("analytical", "tests/test_v46_chemistry.py::test_stoichiometry_result_values_in_dossier", "2 H₂ + O₂ → 2 H₂O", "exact")]},
    "enzyme_kinetics": {"level": "validated_on_data", "evidence": [
        _ev("analytical", f"{V57}::test_enzyme_kinetics_against_michaelis_menten_properties", "v(Km) = Vmax/2", "1e-15"),
        {**_ev("data", "tests/test_v73_data_validation.py::test_puromycin_protocol_is_validated_and_rejects_its_negative_control",
               "Protocole fixé en v7.3 : ajustement sur un réplicat, validation sur l'autre (Puromycine, cellules traitées) ; témoin négatif rejeté",
               "RMSE de validation ≤ 2 × écart-type des réplicats"), "dataset_source": "puromycin_treloar_1974 (Treloar 1974 ; Bates & Watts 1988)"}],
        "note": "Validé uniquement pour ce jeu de données et ses conditions."},
    "sir_epidemic": {"level": "verified", "evidence": [
        _ev("independent_solver", f"{V57}::test_sir_epidemic_against_adaptive_integration", "Pic épidémique contre intégration adaptative (dt = 0,01 j)", "0,5 % ; 0,31 % au pas par défaut 0,1 j")]},
    "heat_diffusion_1d": {"level": "verified", "evidence": [_ev("analytical", f"{V57}::test_heat_diffusion_against_fourier_series", "Série de Fourier exacte", "0,02 °C (observé 0,0095 °C)")]},
    "logistic_growth": {"level": "verified", "evidence": [_ev("independent_solver", f"{V57}::test_logistic_growth_against_integration", "Intégration de l'EDO", "1e-8 relatif")]},
    "first_order_reaction": {"level": "verified", "evidence": [_ev("independent_solver", f"{V57}::test_first_order_closed_forms_against_integration", "Intégration de l'EDO", "1e-8 relatif")]},
    "environmental_decay": {"level": "verified", "evidence": [_ev("independent_solver", f"{V57}::test_first_order_closed_forms_against_integration", "Intégration de l'EDO", "1e-8 relatif")]},
    "one_compartment_pk": {"level": "verified", "evidence": [_ev("independent_solver", f"{V57}::test_first_order_closed_forms_against_integration", "Intégration de l'EDO", "1e-8 relatif")]},
    "lotka_volterra": {"level": "verified", "evidence": [_ev("conserved_quantity", f"{V57}::test_lotka_volterra_conserves_its_first_integral_and_matches_integration",
                                                          "Intégrale première et intégration indépendante", "1e-7 / 1e-6 relatif")]},
    "leaky_integrate_fire": {"level": "verified", "evidence": [_ev("analytical", f"{V57}::test_leaky_integrate_and_fire_against_analytical_interspike_interval",
                                                                  "Intervalle entre potentiels d'action analytique", "2e-3 ms")]},
    "arrhenius_reaction": {"level": "verified", "evidence": [_ev("analytical", f"{V57}::test_arrhenius_rate_constant_against_independent_evaluation", "k = A·exp(−Ea/RT)", "1e-14 relatif")]},
    "sbml_subset_simulator": {"level": "verified", "evidence": [_ev("analytical", f"{V56}::test_first_order_model_matches_analytical_solution", "Modèle SBML du premier ordre", "1e-6 relatif"),
                                                               _ev("analytical", f"{V56}::test_second_order_model_matches_analytical_solution", "Modèle SBML du second ordre", "1e-6 relatif")]},
    "linked_virtual_instrument": {"level": "verified", "evidence": [_ev("statistical_property", "tests/test_v47_linked_instruments.py::test_expanded_uncertainty_has_about_95_percent_coverage",
                                                                       "Couverture de l'intervalle k = 2 sur 2 000 lectures simulées", "94–97 %")],
                                  "note": "Vérifie le modèle de mesure simulée, pas un instrument réel."},
    "lumped_thermal_transient": {"level": "verified", "evidence": [
        _ev("independent_solver", "tests/test_v71_thermal.py::test_lumped_transient_against_independent_integration", "Intégration RK4 indépendante de C·dT/dt = P − (T − T_amb)/R", "1e-9 relatif"),
        _ev("conserved_quantity", "tests/test_v71_thermal.py::test_lumped_energy_balance", "Bilan d'énergie fourni = perdu + stocké", "1e-5 relatif")]},
    "plane_wall_conduction": {"level": "verified", "evidence": [
        _ev("independent_solver", "tests/test_v71_thermal.py::test_composite_wall_against_finite_differences", "Différences finies de l'équation de conduction stationnaire, 3 couches", "1e-9 relatif"),
        _ev("analytical", "tests/test_v71_thermal.py::test_single_layer_hand_calculation", "q = kAΔT/L calculé à la main", "1e-12 relatif")]},
    "aqueous_acid_base": {"level": "verified", "evidence": [
        _ev("independent_solver", "tests/test_v72_acid_base.py::test_weak_acid_against_independent_cubic_solution", "Racine de l'équation cubique exacte par Newton, écrite à part", "1e-9 pH"),
        _ev("analytical", "tests/test_v72_acid_base.py::test_strong_acid_and_base_closed_forms", "Acide fort avec autoprotolyse de l'eau (quadratique)", "1e-9 pH"),
        _ev("conserved_quantity", "tests/test_v72_acid_base.py::test_charge_and_mass_balances_hold", "Bilans de charges et de matière", "1e-12")]},
    "aqueous_titration": {"level": "verified", "evidence": [
        _ev("analytical", "tests/test_v72_acid_base.py::test_titration_landmarks", "Volume d'équivalence C·V/Cb ; pH à la demi-équivalence ≈ pKa", "1e-12 mL / 0,01 pH")]},
    "model_fit": {"level": "verified", "evidence": [
        _ev("published_benchmark", "tests/test_v63_fitting.py::test_puromycin_fit_reproduces_bates_and_watts", "Estimations et erreurs types de Bates & Watts (1988), Puromycine", "5e-4 relatif"),
        _ev("published_benchmark", "tests/test_v63_fitting.py::test_bod_fit_reproduces_the_published_estimates", "Estimations publiées, DBO", "2e-4 relatif"),
        _ev("statistical_property", "tests/test_v63_fitting.py::test_confidence_intervals_have_their_nominal_coverage", "Couverture des IC 95 % sur 400 simulations", "92–98 %")],
                  "note": "Vérifie le moteur d'ajustement (v6.3), pas la validité d'un modèle particulier pour des données."},
    "lab_workflow_designer": {"level": "computable", "evidence": [], "note": "Certains flux calculent un bilan (par exemple une dilution, C1·V1 = C2·V2) ; contrôles internes seulement."},
}
CATALOGUE_TEMPLATE_LEVEL = "concept"  # models.py entries with status "workflow_template"


def _test_exists(node_id: str) -> bool:
    path, _, name = node_id.partition("::")
    file = ROOT / path
    if not file.is_file():
        return False
    tree = ast.parse(file.read_text(encoding="utf-8"))
    return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name for n in ast.walk(tree))


def check_claims() -> list[str]:
    """Problems in the maturity claims (empty = every claim is backed as its level requires)."""
    problems = []
    for model_id, entry in MATURITY.items():
        level = entry["level"]
        if level not in LEVEL_IDS:
            problems.append(f"{model_id}: unknown level {level}")
        evidence = entry.get("evidence", [])
        for ev in evidence:
            if not _test_exists(ev["test"]):
                problems.append(f"{model_id}: evidence test not found: {ev['test']}")
        if level == "verified" and not any(ev["kind"] in INDEPENDENT_KINDS for ev in evidence):
            problems.append(f"{model_id}: 'verified' needs at least one independent reference")
        if level == "validated_on_data" and not any(ev["kind"] == "data" and ev.get("dataset_source") for ev in evidence):
            problems.append(f"{model_id}: 'validated_on_data' needs a sourced dataset")
    return problems


def maturity_of(model_id: str, catalogue_status: str | None = None) -> dict[str, Any]:
    if model_id in MATURITY:
        entry = MATURITY[model_id]
    elif catalogue_status == "workflow_template":
        entry = {"level": CATALOGUE_TEMPLATE_LEVEL, "evidence": [], "note": "Entrée de catalogue sans solveur : aucun résultat scientifique n'est calculé."}
    else:
        entry = {"level": "computable", "evidence": [], "note": "Aucune vérification indépendante enregistrée."}
    level = next(l for l in LEVELS if l["id"] == entry["level"])
    return {**entry, "label_fr": level["label_fr"], "rank": level["rank"]}


def summary() -> dict[str, Any]:
    from models import MODEL_CATALOG
    rows = [{"model_id": mid, **maturity_of(mid)} for mid in MATURITY]
    rows += [{"model_id": m["id"], **maturity_of(m["id"], m["status"])} for m in MODEL_CATALOG if m["id"] not in MATURITY]
    counts = {level["id"]: sum(r["level"] == level["id"] for r in rows) for level in LEVELS}
    return {"levels": LEVELS, "counts": counts, "models": rows, "claims_checked": not check_claims()}
