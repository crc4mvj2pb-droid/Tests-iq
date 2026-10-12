"""Local, dependency-free smoke checks for Virtual Lab Platform."""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis_tools import enzyme_uncertainty, enzyme_local_sensitivity
from models import MODEL_CATALOG, get_solver_contract, run_enzyme, run_sir, run_heat, execute_model
from research_tools import parameter_sweep, monte_carlo_uncertainty, fit_model_parameters, run_software_validation_suite
from planner import plan_enzyme_sweep
from provenance import parse_xy_csv, create_provenance_record
from design import rank_enzyme_experiments
from validation import compare_to_reference

def main():
    assert len(MODEL_CATALOG) >= 13
    assert get_solver_contract()["contract_version"] == "0.5"
    p = {"vmax": 1.2, "km": 0.8, "s_max": 2.0, "points": 5}
    enzyme = run_enzyme(p)
    assert len(enzyme["rows"]) == 5
    sweep = plan_enzyme_sweep(p, "km", [0.5, 0.8, 1.2])
    assert sweep["status"] == "sweep_completed"
    uncertainty = enzyme_uncertainty(p, {"vmax": 0.05, "km": 0.04}, samples=100)
    assert uncertainty["accepted_samples"] >= 50
    sensitivity = enzyme_local_sensitivity(p)
    assert len(sensitivity["rows"]) > 0
    parsed = parse_xy_csv("x,y\n0,0\n1,1\n2,1.5")
    comparison = compare_to_reference(enzyme["rows"], parsed["rows"])
    assert comparison["number_of_comparison_points"] >= 2
    assert create_provenance_record("enzyme_kinetics", "demo-1", p)["record_sha256"]
    assert rank_enzyme_experiments(p, [0.1, 0.2, 0.5, 0.8], 2)["ranked_designs"]
    # Newly added solvers and generic research tools.
    for model_id in ("logistic_growth", "first_order_reaction", "environmental_decay", "one_compartment_pk", "lotka_volterra", "leaky_integrate_fire", "arrhenius_reaction"):
        assert execute_model(model_id, {}).get("rows")
    generic_sweep = parameter_sweep("first_order_reaction", {"initial_A":1,"rate_constant":0.2,"duration":10,"points":11}, "rate_constant", [0.1,0.2,0.3], "final_A")
    assert generic_sweep["status"] == "sweep_completed"
    generic_uncertainty = monte_carlo_uncertainty("logistic_growth", {"initial_population":10,"carrying_capacity":100,"growth_rate":0.2,"duration":10,"points":11}, {"growth_rate":0.01}, "final_population", samples=40, seed=7)
    assert generic_uncertainty["samples_accepted"] >= 20
    known = execute_model("first_order_reaction", {"initial_A":1,"rate_constant":0.3,"duration":10,"points":21})
    reference = [{"x":row["time"],"y":row["A"]} for row in known["rows"][::2]]
    fitted = fit_model_parameters("first_order_reaction", {"initial_A":1,"rate_constant":0.1,"duration":10,"points":21}, reference, "time", "A", {"rate_constant":[0.01,1.0]})
    assert abs(fitted["fitted_parameters"]["rate_constant"]-0.3) < 1e-5
    validation = run_software_validation_suite()
    assert validation["passed"] == validation["total"] == 10
    # The other numerical models should remain executable.
    assert run_sir({"population": 1000, "infected": 5, "recovered": 0, "beta": 0.2, "gamma": 0.05, "days": 5, "dt": 0.1})["rows"]
    assert run_heat({"length": 1, "nx": 11, "alpha": 0.01, "dt": 0.1, "steps": 2, "initial_temperature": 100, "boundary_temperature": 0})["rows"]
    print(json.dumps({
        "status": "passed",
        "checks": [
            "model registry and solver contract",
            "candidate experiment design ranking",
            "enzyme simulation and parameter sweep",
            "Monte Carlo uncertainty and local sensitivity",
            "CSV import and reference comparison",
            "provenance record",
            "SIR and heat solver execution",
            "seven added model families",
            "generic multi-model parameter sweep and Monte Carlo uncertainty",
            "bounded parameter fitting against synthetic reference data",
            "ten-model software sanity validation suite"
        ]
    }, indent=2))

if __name__ == "__main__":
    main()
