from __future__ import annotations
import itertools, math
from typing import Any

def rank_enzyme_experiments(parameters: dict[str, Any], candidate_concentrations: list[float], experiments_per_design: int = 3, measurement_sd: float = 0.05, top_n: int = 5) -> dict[str, Any]:
    """Rank candidate substrate-concentration designs by a local D-optimal information heuristic."""
    vmax=float(parameters.get("vmax", 0))
    km=float(parameters.get("km", 0))
    if not math.isfinite(vmax) or vmax <= 0 or not math.isfinite(km) or km <= 0:
        raise ValueError("vmax and km must be finite and greater than zero.")
    if not isinstance(candidate_concentrations, list) or len(candidate_concentrations) < 2 or len(candidate_concentrations) > 10:
        raise ValueError("Provide between 2 and 10 candidate substrate concentrations.")
    candidates=[]
    for i,value in enumerate(candidate_concentrations):
        if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Candidate concentration {i+1} must be finite and greater than zero.")
        candidates.append(float(value))
    if len(set(candidates)) != len(candidates):
        raise ValueError("Candidate concentrations must be unique.")
    if not isinstance(experiments_per_design,int) or isinstance(experiments_per_design,bool) or not 2 <= experiments_per_design <= min(5,len(candidates)):
        raise ValueError("experiments_per_design must be between 2 and min(5, number of candidates).")
    if not isinstance(measurement_sd,(int,float)) or isinstance(measurement_sd,bool) or not math.isfinite(measurement_sd) or measurement_sd <= 0:
        raise ValueError("measurement_sd must be finite and greater than zero.")
    if not isinstance(top_n,int) or isinstance(top_n,bool) or not 1 <= top_n <= 20:
        raise ValueError("top_n must be between 1 and 20.")

    candidates=sorted(candidates)
    scored=[]
    variance=float(measurement_sd)**2
    for design in itertools.combinations(candidates, experiments_per_design):
        f11=f12=f22=0.0
        for substrate in design:
            denom=km+substrate
            rate=vmax*substrate/denom
            # Derivatives with respect to log(Vmax) and log(Km).
            g1=rate
            g2=-vmax*substrate*km/(denom*denom)
            f11 += g1*g1/variance
            f12 += g1*g2/variance
            f22 += g2*g2/variance
        det=max(0.0, f11*f22-f12*f12)
        scored.append({"concentrations":list(design),"information_determinant":det})
    scored.sort(key=lambda x:x["information_determinant"],reverse=True)
    return {
        "status":"exploratory_design_ranking",
        "criterion":"local D-optimality using a two-parameter Fisher information approximation",
        "assumed_measurement_standard_deviation":float(measurement_sd),
        "nominal_parameters":{"vmax":vmax,"km":km},
        "candidate_count":len(candidates),
        "designs_evaluated":len(scored),
        "ranked_designs":scored[:top_n],
        "interpretation":"The ranking estimates which candidate substrate concentrations may distinguish Vmax and Km most efficiently under the assumed model and constant independent Gaussian measurement noise.",
        "limitations":[
            "This is a local model-based design heuristic, not proof that a physical experiment will succeed.",
            "The ranking depends on nominal Vmax/Km values and the assumed measurement noise.",
            "It omits reagent cost, practical constraints, biological variability, model discrepancy and safety requirements.",
            "The enzyme model is illustrative and is not empirically validated by this tool."
        ]
    }
