"""General-purpose, deterministic research helpers for the implemented demonstration solvers."""
from __future__ import annotations
import math, random
from typing import Any
from models import execute_model, MODEL_CATALOG_BY_ID
from validation import compare_to_reference, interpolate_linear

DEFAULT_SWEEP_OUTPUT = {"enzyme_kinetics":"max_rate_calculated", "sir_epidemic":"peak_infectious", "heat_diffusion_1d":"final_midpoint_temp_c", "logistic_growth":"final_population", "first_order_reaction":"final_A", "environmental_decay":"final_load", "one_compartment_pk":"final_concentration", "lotka_volterra":"final_prey", "leaky_integrate_fire":"spike_count", "arrhenius_reaction":"final_A"}


def _finite(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")
    if positive and value <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return float(value)


def parameter_sweep(model_id: str, parameters: dict[str, Any], parameter: str, values: list[Any], summary_key: str | None = None) -> dict[str, Any]:
    if model_id not in MODEL_CATALOG_BY_ID or MODEL_CATALOG_BY_ID[model_id]["status"] != "implemented_demo":
        raise ValueError("Choose an implemented model; workflow-only templates cannot be swept.")
    if not isinstance(parameters, dict) or not isinstance(parameter, str) or not parameter:
        raise ValueError("parameters and parameter name are required.")
    if not isinstance(values, list) or not 2 <= len(values) <= 25:
        raise ValueError("Provide between 2 and 25 parameter values.")
    numeric = [_finite(v, "sweep value") for v in values]
    if len(set(numeric)) != len(numeric):
        raise ValueError("Sweep values must be unique.")
    if parameter not in parameters:
        raise ValueError("The swept parameter must exist in the submitted parameter object.")
    rows=[]; checks=[]
    for value in numeric:
        p=dict(parameters); p[parameter]=value
        if isinstance(parameters[parameter], int) and not isinstance(parameters[parameter], bool) and value.is_integer(): p[parameter]=int(value)
        result=execute_model(model_id,p)
        key=summary_key
        if not key:
            key = DEFAULT_SWEEP_OUTPUT.get(model_id)
        if not key:
            candidates=[k for k,v in result.get("summary",{}).items() if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)]
            key=candidates[-1] if candidates else None
        if not key or key not in result.get("summary",{}) or not isinstance(result["summary"][key],(int,float)) or not math.isfinite(result["summary"][key]):
            raise ValueError("Requested summary_key is not a finite numeric output of this model.")
        rows.append({"parameter_value":value,"summary_key":key,"summary_value":result["summary"][key],"model_status":result["status"]})
        checks.append(all(result.get("checks",{}).values()))
    return {"status":"sweep_completed","model_id":model_id,"parameter":parameter,"summary_key":rows[0]["summary_key"],"rows":rows,"all_basic_checks_passed":all(checks),"limitations":["A parameter sweep explores the submitted model only; it does not establish real-world validity.","Parameter values are not automatically checked against literature-derived physical ranges."]}


def monte_carlo_uncertainty(model_id: str, parameters: dict[str, Any], uncertainty: dict[str, Any], output_key: str, samples: int = 300, seed: int = 7) -> dict[str, Any]:
    if model_id not in MODEL_CATALOG_BY_ID or MODEL_CATALOG_BY_ID[model_id]["status"] != "implemented_demo":
        raise ValueError("Choose an implemented model; workflow-only templates cannot be sampled.")
    if not isinstance(parameters,dict) or not isinstance(uncertainty,dict) or not uncertainty:
        raise ValueError("parameters and a non-empty uncertainty object are required.")
    if not isinstance(samples,int) or isinstance(samples,bool) or not 30<=samples<=2000:
        raise ValueError("samples must be an integer between 30 and 2000.")
    if not isinstance(seed,int) or isinstance(seed,bool): raise ValueError("seed must be an integer.")
    if not isinstance(output_key,str) or not output_key: raise ValueError("output_key is required (a numeric summary field).")
    sds={k:_finite(v,f"uncertainty[{k}]") for k,v in uncertainty.items()}
    if any(v<0 for v in sds.values()): raise ValueError("Standard deviations must be non-negative.")
    for k in sds:
        if k not in parameters or not isinstance(parameters[k],(int,float)) or isinstance(parameters[k],bool): raise ValueError(f"Uncertainty parameter {k!r} must be numeric and exist in parameters.")
    rng=random.Random(seed); accepted=[]; rejected=0
    for _ in range(samples):
        p=dict(parameters)
        for key,sd in sds.items():
            value=rng.gauss(float(parameters[key]),sd)
            if isinstance(parameters[key],int) and not isinstance(parameters[key],bool): value=max(1,round(value))
            p[key]=value
        try:
            result=execute_model(model_id,p); val=result.get("summary",{}).get(output_key)
            if isinstance(val,(int,float)) and not isinstance(val,bool) and math.isfinite(val) and all(result.get("checks",{}).values()): accepted.append(float(val))
            else: rejected+=1
        except (ValueError, OverflowError, ZeroDivisionError): rejected+=1
    if len(accepted)<max(20,int(samples*0.5)): raise ValueError("Too few valid samples; reduce parameter uncertainty or review parameter ranges.")
    ordered=sorted(accepted)
    def quantile(q):
        idx=(len(ordered)-1)*q; lo=math.floor(idx); hi=math.ceil(idx)
        return ordered[lo] if lo==hi else ordered[lo]*(hi-idx)+ordered[hi]*(idx-lo)
    mean=sum(accepted)/len(accepted); sd=(sum((v-mean)**2 for v in accepted)/(len(accepted)-1))**0.5 if len(accepted)>1 else 0
    return {"status":"monte_carlo_completed","model_id":model_id,"output_key":output_key,"samples_requested":samples,"samples_accepted":len(accepted),"samples_rejected":rejected,"seed":seed,"summary":{"mean":mean,"standard_deviation":sd,"median":quantile(.5),"q025":quantile(.025),"q975":quantile(.975),"min":ordered[0],"max":ordered[-1]},"assumptions":["Each parameter is sampled independently from a normal distribution with the supplied mean and SD.","Invalid samples and samples whose basic model checks fail are rejected.","This interval reflects only the submitted parameter uncertainty; not structural, measurement or model uncertainty."],"limitations":["Monte Carlo output is exploratory and depends on user-specified distributions.","It does not validate the scientific model or provide clinical/safety evidence."]}


def compare_model_output(model_id: str, parameters: dict[str, Any], reference: list[dict[str, Any]], x_key: str, y_key: str) -> dict[str, Any]:
    result=execute_model(model_id,parameters)
    rows=result.get("rows",[])
    if not rows: raise ValueError("The selected model did not produce rows to compare.")
    if x_key not in rows[0] or y_key not in rows[0]: raise ValueError("x_key or y_key does not match a numeric output column from this model.")
    prediction=[]
    for row in rows:
        x=row.get(x_key); y=row.get(y_key)
        if isinstance(x,(int,float)) and isinstance(y,(int,float)) and math.isfinite(x) and math.isfinite(y): prediction.append({"x":x,"y":y})
    out=compare_to_reference(prediction,reference)
    out["model_id"]=model_id; out["source_output_columns"]={"x":x_key,"y":y_key}; out["limitations"]=["Metrics describe agreement with the supplied dataset only.","A low error does not prove causal correctness, parameter identifiability or external validity."]
    return out


def fit_model_parameters(model_id: str, parameters: dict[str, Any], reference: list[dict[str, Any]],
                        x_key: str, y_key: str, bounds: dict[str, list[float]],
                        max_iterations: int = 120) -> dict[str, Any]:
    """Bounded deterministic coordinate search for parameter fitting to user-supplied x/y data.

    This is a transparent, dependency-free optimizer, not a statistical inference engine.
    It minimizes unweighted SSE after linear interpolation of the model output at observed x.
    """
    if model_id not in MODEL_CATALOG_BY_ID or MODEL_CATALOG_BY_ID[model_id].get("status") != "implemented_demo":
        raise ValueError("Parameter fitting requires an implemented model.")
    if not isinstance(parameters, dict) or not parameters:
        raise ValueError("A non-empty parameter object is required.")
    if not isinstance(reference, list) or len(reference) < 3:
        raise ValueError("At least three reference observations are required for fitting.")
    if not isinstance(x_key, str) or not x_key or not isinstance(y_key, str) or not y_key:
        raise ValueError("Numeric model output column names x_key and y_key are required.")
    if not isinstance(bounds, dict) or not bounds:
        raise ValueError("Provide bounds for at least one numeric parameter to fit.")
    if not isinstance(max_iterations, int) or isinstance(max_iterations, bool) or not 1 <= max_iterations <= 500:
        raise ValueError("max_iterations must be an integer from 1 to 500.")

    cleaned=[]
    for i,row in enumerate(reference):
        try: x=float(row["x"]); y=float(row["y"])
        except (KeyError, TypeError, ValueError): raise ValueError(f"Reference row {i+1} must contain numeric x and y.")
        if not math.isfinite(x) or not math.isfinite(y): raise ValueError(f"Reference row {i+1} contains a non-finite value.")
        cleaned.append({"x":x,"y":y})
    cleaned.sort(key=lambda r:r["x"])
    if len({r["x"] for r in cleaned}) != len(cleaned): raise ValueError("Reference x values must be unique.")

    fit_bounds={}
    for key,pair in bounds.items():
        if key not in parameters or isinstance(parameters[key], bool) or not isinstance(parameters[key],(int,float)):
            raise ValueError(f"Fitted parameter {key!r} must exist and be numeric in parameters.")
        if not isinstance(pair,list) or len(pair)!=2: raise ValueError(f"Bounds for {key!r} must be [minimum, maximum].")
        lo=_finite(pair[0],f"{key} minimum"); hi=_finite(pair[1],f"{key} maximum")
        if not lo < hi: raise ValueError(f"Bounds for {key!r} must have minimum < maximum.")
        start=float(parameters[key])
        if not lo <= start <= hi: raise ValueError(f"Initial value for {key!r} must be inside its bounds.")
        fit_bounds[key]=(lo,hi)

    def objective(candidate):
        result=execute_model(model_id,candidate)
        rows=result.get("rows",[])
        if not rows or x_key not in rows[0] or y_key not in rows[0]:
            raise ValueError("x_key/y_key must match numeric output columns of the selected model.")
        points=[]
        for row in rows:
            x=row.get(x_key); y=row.get(y_key)
            if isinstance(x,(int,float)) and not isinstance(x,bool) and isinstance(y,(int,float)) and not isinstance(y,bool) and math.isfinite(x) and math.isfinite(y): points.append({"x":float(x),"y":float(y)})
        if len(points)<2: raise ValueError("Selected model columns must contain at least two numeric points.")
        predictions=[]
        for obs in cleaned:
            pred=interpolate_linear(points,obs["x"])
            predictions.append({"x":obs["x"],"observed":obs["y"],"predicted":pred,"residual":pred-obs["y"]})
        sse=sum(r["residual"]**2 for r in predictions)
        if not math.isfinite(sse): raise ValueError("The objective produced a non-finite score.")
        return sse,predictions

    current=dict(parameters)
    # Clamp only fitted coordinates; preserve all other submitted model settings.
    for key,(lo,hi) in fit_bounds.items(): current[key]=min(hi,max(lo,float(current[key])))
    score,paired=objective(current)
    steps={key:(hi-lo)/4 for key,(lo,hi) in fit_bounds.items()}
    converged=False; iteration=0
    for iteration in range(1,max_iterations+1):
        improved=False
        for key,(lo,hi) in fit_bounds.items():
            best_value=current[key]; best_score=score
            for direction in (-1,1):
                candidate_value=min(hi,max(lo,current[key]+direction*steps[key]))
                if math.isclose(candidate_value,current[key],rel_tol=0,abs_tol=1e-15): continue
                candidate=dict(current); candidate[key]=candidate_value
                try: candidate_score,_=objective(candidate)
                except (ValueError,OverflowError,ZeroDivisionError): continue
                if candidate_score < best_score - max(1e-15,abs(best_score)*1e-12): best_score=candidate_score; best_value=candidate_value
            if best_score < score - max(1e-15,abs(score)*1e-12):
                current[key]=best_value; score=best_score; improved=True
        if not improved:
            for key in steps: steps[key]*=0.5
            if max(steps.values(),default=0.0) < 1e-8:
                converged=True; break
    score,paired=objective(current)
    residuals=[r["residual"] for r in paired]
    observed=[r["observed"] for r in paired]
    mean=sum(observed)/len(observed)
    sst=sum((v-mean)**2 for v in observed)
    rmse=math.sqrt(score/len(paired)); mae=sum(abs(v) for v in residuals)/len(residuals); bias=sum(residuals)/len(residuals)
    r2=1-score/sst if sst>0 else None
    return {
        "status":"parameter_fit_completed_exploratory", "model_id":model_id,
        "fitted_parameters":{k:current[k] for k in fit_bounds},
        "fixed_parameters":{k:v for k,v in current.items() if k not in fit_bounds},
        "bounds":{k:{"minimum":v[0],"maximum":v[1]} for k,v in fit_bounds.items()},
        "objective":"unweighted_sum_of_squared_residuals", "sse":score,
        "metrics":{"rmse":rmse,"mae":mae,"mean_bias_predicted_minus_observed":bias,"r_squared_descriptive":r2},
        "observations_used":len(paired), "iterations":iteration, "converged_by_step_tolerance":converged,
        "paired_values":paired,
        "assumptions":["Unweighted least squares; all observations receive equal weight.","Model output is linearly interpolated at observation x values.","Only explicitly selected parameters are optimized; all other parameters remain fixed."],
        "limitations":["Coordinate search is a simple bounded optimizer and may find a local rather than global minimum.","No parameter confidence intervals, covariance, formal identifiability analysis, or measurement-error model is calculated.","Fit quality on supplied data is not proof of scientific validity or predictive performance.","The supplied dataset's provenance and measurement uncertainty are not independently verified."]
    }


def run_software_validation_suite() -> dict[str, Any]:
    """Run reproducible numerical sanity checks across every currently executable catalog model."""
    cases=[
        ("enzyme_kinetics",{"vmax":2,"km":0.5,"s_max":5,"points":21}),
        ("sir_epidemic",{"population":1000,"beta":0.3,"gamma":0.1,"initial_infected":2,"days":20,"dt":0.1}),
        ("heat_diffusion_1d",{}),
        ("logistic_growth",{"initial_population":10,"carrying_capacity":100,"growth_rate":0.2,"duration":10,"points":21}),
        ("first_order_reaction",{"initial_A":1,"rate_constant":0.2,"duration":10,"points":21}),
        ("environmental_decay",{"initial_load":100,"removal_rate":0.1,"duration":10,"points":21}),
        ("one_compartment_pk",{"input_amount":100,"distribution_volume":10,"clearance":1,"duration":24,"points":25}),
        ("lotka_volterra",{"duration":5,"dt":0.01}),
        ("leaky_integrate_fire",{"duration_ms":50,"dt_ms":0.1}),
        ("arrhenius_reaction",{"duration_s":10,"points":21})
    ]
    results=[]
    for model_id,params in cases:
        try:
            result=execute_model(model_id,params)
            checks=result.get("checks",{})
            passed=bool(checks) and all(value is True for value in checks.values()) and result.get("status")=="computed_basic_checks_passed"
            results.append({"model_id":model_id,"status":"pass" if passed else "fail","checks":checks,"rows":len(result.get("rows",[]))})
        except Exception as exc:
            results.append({"model_id":model_id,"status":"fail","error":str(exc)})
    passed=sum(1 for item in results if item["status"]=="pass")
    return {"status":"software_sanity_suite_completed","passed":passed,"failed":len(results)-passed,"total":len(results),"models":results,"scope":"Automated mathematical/software sanity checks only; not empirical, clinical, engineering, cosmetic-safety, or independent scientific validation.","timestamp_utc":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
